"""POST /api/onboarding — F5-S1A + S1B + S2 (K-008/K-013/K-015/K-017/K-019 + K-010/K-014).

Plan: docs/plans/F5_S1_user_profile_bridge_tier_enum.md §7.5
      docs/plans/F5_S1B_dim_subfield_bridge.md §7.4/§7.5/§8 (DM-9)
      F5-S2 PROMPT #4 §1.B (translator hook)
- user_profiles upsert (3-tier enum; language_pref + field_primary kolonları DB'de yok)
- dim_field pre-flight: req.field_ids her elemanı dim_field'da olmalı (422)
- payload-level orphan check: subfields[i].field_id ∈ req.field_ids (DB'siz, en hızlı, 422)
- dim_subfield composite pre-flight: (subfield_id, field_id) çiftleri DB'de mevcut (422)
- F5-S2 hook: research_focus → translate_to_academic_en (Gemini Flash, 5sn timeout,
  K-015 graceful — fallback=True olsa bile 200 dön; metadata.research_focus_en +
  metadata.translation_meta jsonb'ye yazılır)
- user_profile_fields bridge: idempotent DELETE + INSERT (re-submit'te yeniden create)
- user_profile_subfields bridge: idempotent DELETE + INSERT (composite payload)
- ⚠ OQ-B sıra: field bridge ÖNCE, subfield bridge SONRA (cascade trigger field'ı görsün)
- ORCID: KVKK — raw SHA-256'lanır, orcid_hash kolonuna yazılır; raw asla saklanmaz/loglanmaz
- Dev/test fallback: SUPABASE yoksa placeholder UUID döner, DB yazımı + translator yapılmaz.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request
from supabase import Client

from api.models.onboarding import OnboardingRequest, OnboardingResponse, SubfieldRef
from api.services.translator import translate_to_academic_en

router = APIRouter(prefix="/api", tags=["onboarding"])


def _supabase() -> Client | None:
    from api.config import get_settings

    s = get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_SECRET_KEY:
        return None
    from api.db.supabase_client import get_supabase_admin

    return get_supabase_admin()


def _orcid_hash(orcid_raw: str | None) -> str | None:
    if not orcid_raw:
        return None
    return hashlib.sha256(orcid_raw.encode("utf-8")).hexdigest()


@router.post("/onboarding", response_model=OnboardingResponse)
async def onboarding(req: OnboardingRequest, request: Request) -> OnboardingResponse:
    user_id = getattr(request.state, "user_id", None) or uuid.uuid4().hex[:24]
    db = _supabase()

    # Payload-level orphan check (DB'siz, en hızlı) — req.subfields[i].field_id ∈ req.field_ids
    field_set = set(req.field_ids)
    orphan_pairs = [
        [s.subfield_id, s.field_id] for s in req.subfields if s.field_id not in field_set
    ]
    if orphan_pairs:
        raise HTTPException(
            status_code=422,
            detail={"error": "orphan_subfield_ids", "orphan": orphan_pairs},
        )

    if db is not None:
        from api.db.supabase_client import supabase_call_async

        field_check = await supabase_call_async(
            lambda: db.table("dim_field")
            .select("field_id")
            .in_("field_id", req.field_ids)
            .execute()
        )
        rows = cast(list[dict[str, Any]], field_check.data or [])
        existing = {row["field_id"] for row in rows}
        missing = [fid for fid in req.field_ids if fid not in existing]
        if missing:
            raise HTTPException(
                status_code=422,
                detail={"error": "invalid_field_ids", "missing": missing},
            )

        # dim_subfield composite pre-flight — (subfield_id, field_id) çiftleri DB'de mevcut
        if req.subfields:
            requested_ids = list({s.subfield_id for s in req.subfields})
            sub_check = await supabase_call_async(
                lambda: db.table("dim_subfield")
                .select("subfield_id, field_id")
                .in_("subfield_id", requested_ids)
                .execute()
            )
            sub_rows = cast(list[dict[str, Any]], sub_check.data or [])
            valid_pairs = {(r["subfield_id"], r["field_id"]) for r in sub_rows}
            invalid = [
                [s.subfield_id, s.field_id]
                for s in req.subfields
                if (s.subfield_id, s.field_id) not in valid_pairs
            ]
            if invalid:
                raise HTTPException(
                    status_code=422,
                    detail={"error": "invalid_subfield_pairs", "invalid": invalid},
                )

        # F5-S2 translator hook — K-010 sistem iç dili EN; K-015 graceful (fail → 200)
        translation = await translate_to_academic_en(req.research_focus)
        from api.config import get_settings

        settings = get_settings()
        metadata: dict[str, Any] = {
            "research_focus": req.research_focus,
            "research_focus_en": translation.text_en,
            "translation_meta": {
                "source_lang": translation.source_lang,
                "duration_ms": translation.duration_ms,
                "fallback": translation.fallback,
                "model": settings.GEMINI_FLASH_MODEL,
            },
        }
        if req.affiliation:
            metadata["affiliation"] = req.affiliation

        profile_payload = {
            "user_id": user_id,
            "display_name": req.full_name,
            "tier": req.tier,
            "onboarding_completed": True,
            "metadata": json.dumps(metadata),
        }
        orcid_hash = _orcid_hash(req.orcid_raw)
        if orcid_hash is not None:
            profile_payload["orcid_hash"] = orcid_hash

        await supabase_call_async(
            lambda: db.table("user_profiles")
            .upsert(profile_payload, on_conflict="user_id")
            .execute()
        )

        # OQ-B sıra: field bridge ÖNCE (cascade trigger NEW.field_id'i bu satırlardan okur)
        await supabase_call_async(
            lambda: db.table("user_profile_fields")
            .delete()
            .eq("user_id", user_id)
            .execute()
        )
        bridge_rows = [
            {"user_id": user_id, "field_id": fid, "position": idx + 1}
            for idx, fid in enumerate(req.field_ids)
        ]
        await supabase_call_async(
            lambda: db.table("user_profile_fields").insert(bridge_rows).execute()
        )

        # OQ-B sıra: subfield bridge SONRA (composite payload, idempotent DELETE+INSERT)
        # subfields=[] → skip path (delete+insert ikisi de atlanır, brief §C.2)
        if req.subfields:
            await supabase_call_async(
                lambda: db.table("user_profile_subfields")
                .delete()
                .eq("user_id", user_id)
                .execute()
            )
            subfield_rows = [
                {
                    "user_id": user_id,
                    "subfield_id": s.subfield_id,
                    "field_id": s.field_id,
                }
                for s in req.subfields
            ]
            await supabase_call_async(
                lambda: db.table("user_profile_subfields")
                .insert(subfield_rows)
                .execute()
            )

    return OnboardingResponse(
        user_id=user_id,
        tier=req.tier,
        field_ids=list(req.field_ids),
        subfields=[SubfieldRef(subfield_id=s.subfield_id, field_id=s.field_id) for s in req.subfields],
        profile_complete=True,
    )
