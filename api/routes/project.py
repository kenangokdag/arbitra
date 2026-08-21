"""F9 P093 /api/project — proje oluşturma + listeleme + tek satır.

Plan: docs/plans/F9_kesif_workbench.md §7 (endpoint sözleşmesi)
- POST /api/project: create + onboarding miras kopyalama
  (user_profile_fields/_subfields bridge + user_profiles.metadata.research_focus_en)
- GET  /api/project: kullanıcının projeleri (RLS-filtered + manuel user_id zırh,
  service role bypass'a karşı), updated_at DESC
- GET  /api/project/{id}: tek proje detayı (anchor=None placeholder, P094+ wire)
- HK-1: extra=forbid (model layer); HK-6: no Any (cast'li sınırda).
- Auth: AuthMiddleware request.state.user_id.
- Dev/test fallback: SUPABASE yoksa placeholder UUID döner, DB yazımı atlanır
  (onboarding.py:36-44 pattern paralel).

F11 Phase A:
- POST /api/project/from-q: Q (vitrin/OpenAlex) sayfasından "Projeye Dönüştür"
  CTA → projects insert (seed_query/lang/source='q') + project_seed_papers
  bulk insert. Onboarding miras kopyalama burada DA çalışır (onboarding profili
  + Q seçimi birlikte oturur).

⚠ Service role client RLS BYPASS — tüm SELECT/UPDATE'lerde manuel
   .eq("user_id", uid) zırhı zorunlu. Ekstra defansif kat (RLS güvenmek yetmez).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query, Request, status
from supabase import Client

from api.models.project import (
    ProjectCreate,
    ProjectFromQRequest,
    ProjectFromQResponse,
    ProjectListItem,
    ProjectPaperItem,
    ProjectPapersResponse,
    ProjectRead,
)

router = APIRouter(prefix="/api", tags=["project"])


def _supabase() -> Client | None:
    from api.config import get_settings

    s = get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_SECRET_KEY:
        return None
    from api.db.supabase_client import get_supabase_admin

    return get_supabase_admin()


def _user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="missing_user_id")
    return cast(str, uid)


def _row_to_read(
    row: dict[str, Any],
    seed_paper_count: int = 0,
    parsed_understanding: dict[str, Any] | None = None,
) -> ProjectRead:
    # F11 Phase A: seed_* alanları 0019 migration sonrası kolonda var.
    # Eski projelerde NULL → Pydantic default (None / 'manual' / 0).
    return ProjectRead(
        id=str(row["id"]),
        name=row["name"],
        status=row["status"],
        current_stage=row["current_stage"],
        inherited_field_ids=list(row.get("inherited_field_ids") or []),
        inherited_subfield_ids=list(row.get("inherited_subfield_ids") or []),
        inherited_research_focus=row.get("inherited_research_focus"),
        seed_query=row.get("seed_query"),
        seed_lang=row.get("seed_lang"),
        seed_source=row.get("seed_source") or "manual",
        seed_paper_count=seed_paper_count,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        anchor=None,
        parsed_understanding=parsed_understanding,
    )


def _placeholder_project(
    name: str,
    *,
    seed_query: str | None = None,
    seed_lang: str | None = None,
    seed_source: str = "manual",
    seed_paper_count: int = 0,
) -> ProjectRead:
    """Dev/test fallback (SUPABASE yok): şablon ProjectRead."""
    now = datetime.now(UTC)
    return ProjectRead(
        id=str(uuid.uuid4()),
        name=name,
        status="active",
        current_stage="1.1",
        inherited_field_ids=[],
        inherited_subfield_ids=[],
        inherited_research_focus=None,
        seed_query=seed_query,
        seed_lang=cast(Any, seed_lang),  # SeedLang Literal — None geçirilebilir
        seed_source=cast(Any, seed_source),
        seed_paper_count=seed_paper_count,
        created_at=now,
        updated_at=now,
        anchor=None,
    )


def _extract_research_focus_en(metadata_raw: object) -> str | None:
    """metadata jsonb / json string'inden research_focus_en oku.

    Onboarding (onboarding.py:132) `json.dumps(metadata)` ile str yazıyor;
    Supabase jsonb otomatik parse de edebilir. Her iki path da güvenli.
    """
    meta: dict[str, Any]
    if isinstance(metadata_raw, dict):
        meta = cast(dict[str, Any], metadata_raw)
    elif isinstance(metadata_raw, str) and metadata_raw:
        try:
            parsed = json.loads(metadata_raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        meta = cast(dict[str, Any], parsed)
    else:
        return None
    focus = meta.get("research_focus_en")
    return focus if isinstance(focus, str) and focus else None


async def _fetch_onboarding_inheritance(
    db: Client, user_id: str
) -> dict[str, Any]:
    """Onboarding miras snapshot: 3 SELECT (fields + subfields + metadata).

    POST /api/project ve POST /api/project/from-q ikisi de aynı miras kopyalar
    (kullanıcı onboarding'den geçtiyse profil bilgisi proje açılışında dondurulur).
    """
    from api.db.supabase_client import supabase_call_async

    field_resp = await supabase_call_async(
        lambda: db.table("user_profile_fields")
        .select("field_id")
        .eq("user_id", user_id)
        .execute()
    )
    inherited_field_ids = [
        r["field_id"]
        for r in cast(list[dict[str, Any]], field_resp.data or [])
    ]

    sub_resp = await supabase_call_async(
        lambda: db.table("user_profile_subfields")
        .select("subfield_id")
        .eq("user_id", user_id)
        .execute()
    )
    inherited_subfield_ids = [
        r["subfield_id"]
        for r in cast(list[dict[str, Any]], sub_resp.data or [])
    ]

    profile_resp = await supabase_call_async(
        lambda: db.table("user_profiles")
        .select("metadata")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    profile_rows = cast(list[dict[str, Any]], profile_resp.data or [])
    inherited_research_focus = (
        _extract_research_focus_en(profile_rows[0].get("metadata"))
        if profile_rows
        else None
    )
    return {
        "inherited_field_ids": inherited_field_ids,
        "inherited_subfield_ids": inherited_subfield_ids,
        "inherited_research_focus": inherited_research_focus,
    }


@router.post(
    "/project",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(req: ProjectCreate, request: Request) -> ProjectRead:
    user_id = _user_id(request)
    db = _supabase()
    if db is None:
        return _placeholder_project(req.name)

    from api.db.supabase_client import supabase_call_async

    inheritance = await _fetch_onboarding_inheritance(db, user_id)

    insert_payload: dict[str, Any] = {
        "user_id": user_id,
        "name": req.name,
        # status='active', current_stage='1.1' DDL DEFAULT'tan
        **inheritance,
    }
    inserted = await supabase_call_async(
        lambda: db.table("projects").insert(insert_payload).execute()
    )
    rows = cast(list[dict[str, Any]], inserted.data or [])
    if not rows:
        raise HTTPException(status_code=503, detail="project_insert_failed")
    return _row_to_read(rows[0])


def _name_from_q_query(q_query: str) -> str:
    # projects.name CHECK 1-200; "Q: <ilk 180 char>" güvenli içerik.
    snippet = q_query.strip()[:180]
    return f"Q: {snippet}" if snippet else "Q sorgusu"


@router.post(
    "/project/from-q",
    response_model=ProjectFromQResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_from_q(
    req: ProjectFromQRequest, request: Request
) -> ProjectFromQResponse:
    """F11 Phase A: Q (vitrin) sayfasından proje yarat + Q'dan miras snapshot.

    1) projects insert (seed_query/lang/source='q' + onboarding miras)
    2) project_seed_papers bulk insert (1-25 OpenAlex paper_id)
    Hata durumu: 503 (insert fail). Tek paper_id 2 kez gelirse 422 (Pydantic).
    """
    user_id = _user_id(request)
    db = _supabase()
    if db is None:
        return ProjectFromQResponse(
            project_id=str(uuid.uuid4()),
            seed_query=req.q_query,
            seed_paper_count=len(req.selected_paper_ids),
        )

    from api.db.supabase_client import supabase_call_async

    inheritance = await _fetch_onboarding_inheritance(db, user_id)

    insert_payload: dict[str, Any] = {
        "user_id": user_id,
        "name": _name_from_q_query(req.q_query),
        "seed_query": req.q_query,
        "seed_lang": req.q_lang,
        "seed_source": "q",
        **inheritance,
    }
    inserted = await supabase_call_async(
        lambda: db.table("projects").insert(insert_payload).execute()
    )
    rows = cast(list[dict[str, Any]], inserted.data or [])
    if not rows:
        raise HTTPException(status_code=503, detail="project_insert_failed")
    project_id = str(rows[0]["id"])

    seed_rows = [
        {
            "project_id": project_id,
            "paper_id": pid,
            "source_query": req.q_query,
            "source_lang": req.q_lang,
        }
        for pid in req.selected_paper_ids
    ]
    seed_inserted = await supabase_call_async(
        lambda: db.table("project_seed_papers").insert(seed_rows).execute()
    )
    seed_data = cast(list[dict[str, Any]], seed_inserted.data or [])
    if len(seed_data) != len(seed_rows):
        # Atomic değil — projects yazıldı, seed eksik. RLS ihlali / DB hatası.
        raise HTTPException(status_code=503, detail="seed_papers_insert_failed")

    return ProjectFromQResponse(
        project_id=project_id,
        seed_query=req.q_query,
        seed_paper_count=len(seed_data),
    )


@router.get("/project", response_model=list[ProjectListItem])
async def list_projects(request: Request) -> list[ProjectListItem]:
    user_id = _user_id(request)
    db = _supabase()
    if db is None:
        return []

    from api.db.supabase_client import supabase_call_async

    resp = await supabase_call_async(
        lambda: db.table("projects")
        .select("id,name,status,current_stage,updated_at")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return [
        ProjectListItem(
            id=str(r["id"]),
            name=r["name"],
            status=r["status"],
            current_stage=r["current_stage"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]


@router.get("/project/{project_id}", response_model=ProjectRead)
async def get_project(project_id: str, request: Request) -> ProjectRead:
    user_id = _user_id(request)
    db = _supabase()
    if db is None:
        # Dev fallback: gerçek satır yok, var-gibi 404
        raise HTTPException(status_code=404, detail="project_not_found")

    from api.db.supabase_client import supabase_call_async

    resp = await supabase_call_async(
        lambda: db.table("projects")
        .select("*")
        .eq("id", project_id)
        .eq("user_id", user_id)  # service role bypass'a defansif zırh
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    if not rows:
        # RLS / yok → UX güvenli 404 (403 sızdırmaz)
        raise HTTPException(status_code=404, detail="project_not_found")

    # F11 Phase A: seed_paper_count = len(project_seed_papers rows).
    # max 25 satır (request limiti) — basit SELECT yeterli, COUNT(*) gereksiz.
    seed_resp = await supabase_call_async(
        lambda: db.table("project_seed_papers")
        .select("paper_id")
        .eq("project_id", project_id)
        .execute()
    )
    seed_rows = cast(list[dict[str, Any]], seed_resp.data or [])

    # V1-S16-P001: son adviser turn'unun parsed_understanding'i (2.1 confirm sayfası).
    # En yüksek (attempt_no, turn_no) sıralı; role='adviser' filtreli; tek satır.
    pu_resp = await supabase_call_async(
        lambda: db.table("project_chat_messages")
        .select("parsed_understanding")
        .eq("project_id", project_id)
        .eq("role", "adviser")
        .order("attempt_no", desc=True)
        .order("turn_no", desc=True)
        .limit(1)
        .execute()
    )
    pu_rows = cast(list[dict[str, Any]], pu_resp.data or [])
    parsed_understanding: dict[str, Any] | None = None
    if pu_rows:
        pu = pu_rows[0].get("parsed_understanding")
        if isinstance(pu, dict):
            parsed_understanding = pu

    return _row_to_read(
        rows[0],
        seed_paper_count=len(seed_rows),
        parsed_understanding=parsed_understanding,
    )


@router.get("/project/{project_id}/papers", response_model=ProjectPapersResponse)
async def list_project_papers(
    project_id: str,
    request: Request,
    rank_max: int | None = Query(default=None, ge=1, le=50),
) -> ProjectPapersResponse:
    """F13 S11.0 — proje çapasındaki makaleler (hydrated papers metadata).

    1) Ownership check (projects.user_id == request.user_id; RLS bypass'a defansif).
    2) Kaynak:
       - rank_max set ise (V1-S17 P010) project_cluster.rank_final ASC top-N
       - aksi halde project_seed_papers (V1-S14 legacy)
    3) papers_hydration_service.hydrate_paper_ids: eksikleri OpenAlex'ten doldur.
    4) papers SELECT (title/abstract/authors/year/venue/doi/citations_count).

    404: project_not_found (ownership veya satır yok).
    503: hydration_failed (OpenAlex erişilemez).
    """
    user_id = _user_id(request)
    db = _supabase()
    if db is None:
        # Dev fallback — boş liste döner (SUPABASE yok)
        return ProjectPapersResponse(
            project_id=project_id, papers=[], hydrated_count=0
        )

    from api.db.supabase_client import supabase_call_async

    owner_resp = await supabase_call_async(
        lambda: db.table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not cast(list[dict[str, Any]], owner_resp.data or []):
        raise HTTPException(status_code=404, detail="project_not_found")

    if rank_max is not None:
        # V1-S17 P010 (KD-V1-S17-05) — cluster top-N (rank_final ASC).
        cluster_resp = await supabase_call_async(
            lambda: db.table("project_cluster")
            .select("paper_id,rank_final")
            .eq("project_id", project_id)
            .order("rank_final", desc=False)
            .limit(rank_max)
            .execute()
        )
        cluster_rows = cast(list[dict[str, Any]], cluster_resp.data or [])
        paper_ids = [str(r["paper_id"]) for r in cluster_rows]
    else:
        seed_resp = await supabase_call_async(
            lambda: db.table("project_seed_papers")
            .select("paper_id")
            .eq("project_id", project_id)
            .execute()
        )
        seed_rows = cast(list[dict[str, Any]], seed_resp.data or [])
        paper_ids = [str(r["paper_id"]) for r in seed_rows]
    if not paper_ids:
        return ProjectPapersResponse(
            project_id=project_id, papers=[], hydrated_count=0
        )

    from api.services.openalex_polite import OpenAlexError
    from api.services.papers_hydration_service import hydrate_paper_ids

    try:
        hydrated = await hydrate_paper_ids(paper_ids)
    except OpenAlexError as exc:
        raise HTTPException(status_code=503, detail=f"hydration_failed: {exc}") from exc

    papers_resp = await supabase_call_async(
        lambda: db.table("papers")
        .select("paper_id,doi,title,abstract,authors,year,venue,citations_count")
        .in_("paper_id", paper_ids)
        .execute()
    )
    paper_rows = cast(list[dict[str, Any]], papers_resp.data or [])

    items: list[ProjectPaperItem] = []
    for row in paper_rows:
        raw_authors = row.get("authors") or []
        if isinstance(raw_authors, str):
            try:
                raw_authors = json.loads(raw_authors)
            except json.JSONDecodeError:
                raw_authors = []
        author_names = [
            str(a.get("name", "")) for a in raw_authors if isinstance(a, dict)
        ]
        items.append(
            ProjectPaperItem(
                paper_id=str(row["paper_id"]),
                title=row.get("title") or "(başlıksız)",
                abstract=row.get("abstract"),
                authors=[n for n in author_names if n],
                year=row.get("year"),
                venue=row.get("venue"),
                doi=row.get("doi"),
                citations_count=int(row.get("citations_count") or 0),
            )
        )

    # paper_ids sırasına göre döndür (seed sırası UX'te önemli)
    by_id = {item.paper_id: item for item in items}
    ordered = [by_id[pid] for pid in paper_ids if pid in by_id]

    return ProjectPapersResponse(
        project_id=project_id, papers=ordered, hydrated_count=hydrated
    )
