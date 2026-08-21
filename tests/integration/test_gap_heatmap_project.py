"""V1-S17 P004 — GET /api/gap-heatmap project_id integration.

Plan: docs/plans/V1_S17_cascade_5rc.md §4 C004.

Kapsam:
1. project_id verildiğinde project_cluster + fact_paper_topic + fact_paper_metod
   bridges ile cells daralır (sadece proje theme/method üzerinden hücreler).
2. project_id verilmediğinde global cells set döner (V1-S14 davranış korunur).
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def authed_client(client: TestClient) -> TestClient:
    token = jwt.encode({"sub": "user-1"}, "x", algorithm="HS256")
    client.headers["Authorization"] = f"Bearer {token}"
    return client


class _FakeBuilder:
    def __init__(self, recorder: _FakeSupabase, table: str) -> None:
        self._rec = recorder
        self._table = table
        self._op: str | None = None
        self._filters: dict[str, Any] = {}
        self._in_filters: dict[str, list[Any]] = {}
        self._limit: int | None = None
        self._order: tuple[str, bool] | None = None  # (col, desc)

    def select(self, _cols: str = "*", **_kw: Any) -> _FakeBuilder:
        self._op = "select"
        return self

    def eq(self, col: str, val: Any) -> _FakeBuilder:
        self._filters[col] = val
        return self

    def in_(self, col: str, vals: list[Any]) -> _FakeBuilder:
        self._in_filters[col] = list(vals)
        return self

    def limit(self, n: int) -> _FakeBuilder:
        self._limit = n
        return self

    def order(self, col: str, desc: bool = False) -> _FakeBuilder:
        self._order = (col, desc)
        return self

    def execute(self) -> SimpleNamespace:
        return self._rec.respond(
            {
                "table": self._table,
                "op": self._op,
                "filters": dict(self._filters),
                "in_filters": dict(self._in_filters),
                "limit": self._limit,
                "order": self._order,
            }
        )


class _FakeSupabase:
    def __init__(self) -> None:
        self.gap_cells: list[dict[str, Any]] = []
        self.theme_labels: list[dict[str, Any]] = []
        self.project_clusters: list[dict[str, Any]] = []
        self.paper_topics: list[dict[str, Any]] = []
        self.paper_methods: list[dict[str, Any]] = []

    def table(self, name: str) -> _FakeBuilder:
        return _FakeBuilder(self, name)

    def respond(self, call: dict[str, Any]) -> SimpleNamespace:
        t, f, inf, order, lim = (
            call["table"],
            call["filters"],
            call["in_filters"],
            call["order"],
            call["limit"],
        )
        if t == "fact_gap_matrix":
            rows = [r for r in self.gap_cells if r.get("matrix_id") == f.get("matrix_id")]
            if order:
                col, desc = order
                rows = sorted(rows, key=lambda r: r.get(col) or 0, reverse=desc)
            if lim:
                rows = rows[:lim]
            return SimpleNamespace(data=rows)
        if t == "dim_theme":
            ids = set(inf.get("theme_id") or [])
            return SimpleNamespace(data=[r for r in self.theme_labels if r.get("theme_id") in ids])
        if t == "project_cluster":
            rows = [r for r in self.project_clusters if r.get("project_id") == f.get("project_id")]
            return SimpleNamespace(data=rows)
        if t == "fact_paper_topic":
            ids = set(inf.get("paper_id") or [])
            return SimpleNamespace(data=[r for r in self.paper_topics if r.get("paper_id") in ids])
        if t == "fact_paper_metod":
            ids = set(inf.get("paper_id") or [])
            return SimpleNamespace(data=[r for r in self.paper_methods if r.get("paper_id") in ids])
        return SimpleNamespace(data=[])


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeSupabase]:
    fake = _FakeSupabase()
    # Global cells: 4 themes × 3 methods = 12 cells, gap_value variyetli
    fake.gap_cells = [
        {"matrix_id": "M1", "axis_x": "T_ai", "axis_y": "topsis", "depth": 50, "depth_norm": 0.5, "gap_value": 0.92},
        {"matrix_id": "M1", "axis_x": "T_ai", "axis_y": "vikor", "depth": 30, "depth_norm": 0.3, "gap_value": 0.85},
        {"matrix_id": "M1", "axis_x": "T_ai", "axis_y": "ahp", "depth": 20, "depth_norm": 0.2, "gap_value": 0.80},
        {"matrix_id": "M1", "axis_x": "T_med", "axis_y": "topsis", "depth": 40, "depth_norm": 0.4, "gap_value": 0.78},
        {"matrix_id": "M1", "axis_x": "T_med", "axis_y": "vikor", "depth": 25, "depth_norm": 0.25, "gap_value": 0.70},
        {"matrix_id": "M1", "axis_x": "T_med", "axis_y": "ahp", "depth": 15, "depth_norm": 0.15, "gap_value": 0.65},
        {"matrix_id": "M1", "axis_x": "T_env", "axis_y": "topsis", "depth": 22, "depth_norm": 0.2, "gap_value": 0.60},
        {"matrix_id": "M1", "axis_x": "T_env", "axis_y": "vikor", "depth": 18, "depth_norm": 0.18, "gap_value": 0.55},
        {"matrix_id": "M1", "axis_x": "T_env", "axis_y": "ahp", "depth": 12, "depth_norm": 0.12, "gap_value": 0.50},
        {"matrix_id": "M1", "axis_x": "T_econ", "axis_y": "topsis", "depth": 10, "depth_norm": 0.1, "gap_value": 0.45},
        {"matrix_id": "M1", "axis_x": "T_econ", "axis_y": "vikor", "depth": 8, "depth_norm": 0.08, "gap_value": 0.40},
        {"matrix_id": "M1", "axis_x": "T_econ", "axis_y": "ahp", "depth": 6, "depth_norm": 0.06, "gap_value": 0.35},
    ]
    fake.theme_labels = [
        {"theme_id": "T_ai", "name_tr": "Yapay Zekâ", "metadata": {"group": "Tech"}},
        {"theme_id": "T_med", "name_tr": "Tıp", "metadata": {"group": "Health"}},
        {"theme_id": "T_env", "name_tr": "Çevre", "metadata": {"group": "Eco"}},
        {"theme_id": "T_econ", "name_tr": "Ekonomi", "metadata": {"group": "Soc"}},
    ]
    # Proje "prj-1" sadece T_med + topsis/vikor (3 hücreyi kapsar)
    fake.project_clusters = [
        {"project_id": "prj-1", "paper_id": "P1"},
        {"project_id": "prj-1", "paper_id": "P2"},
    ]
    fake.paper_topics = [
        {"paper_id": "P1", "theme_id": "T_med"},
        {"paper_id": "P2", "theme_id": "T_med"},
    ]
    fake.paper_methods = [
        {"paper_id": "P1", "metod_id": "topsis"},
        {"paper_id": "P2", "metod_id": "vikor"},
    ]

    monkeypatch.setattr("api.routes.gap_heatmap.get_supabase_admin", lambda: fake)

    async def _direct_call(
        fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> Any:
        del timeout
        return fn()

    monkeypatch.setattr(
        "api.db.supabase_client.supabase_call_async", _direct_call
    )
    # gap_heatmap.py içindeki çağrı `from api.db.supabase_client import supabase_call_async`
    # ile alındığı için modül-içi referansı da patchle:
    monkeypatch.setattr(
        "api.routes.gap_heatmap.supabase_call_async", _direct_call
    )
    yield fake


# ── 1. project_id verildiğinde cells daralır ─────────────────────────────────


def test_gap_heatmap_project_filter_narrows_cells(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    del fake_db
    r = authed_client.get(
        "/api/gap-heatmap",
        params={"top_methods": 14, "top_topics": 30, "project_id": "prj-1"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Proje sadece T_med + (topsis|vikor) — 2 hücre kalmalı (ahp DIŞARIDA, T_ai/T_env/T_econ DIŞARIDA)
    method_ids = {m["id"] for m in body["methods"]}
    topic_ids = {t["id"] for t in body["topics"]}
    assert method_ids <= {"topsis", "vikor"}, method_ids
    assert topic_ids == {"T_med"}, topic_ids
    # Cells'ler de filtre içinde
    for cell in body["cells"]:
        assert cell["method_id"] in {"topsis", "vikor"}
        assert cell["topic_id"] == "T_med"


# ── 2. project_id YOK → global cells set (12 hücre setinin daraltılmamış hali) ─


def test_gap_heatmap_no_project_id_returns_global(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    del fake_db
    r = authed_client.get(
        "/api/gap-heatmap",
        params={"top_methods": 14, "top_topics": 30},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    topic_ids = {t["id"] for t in body["topics"]}
    method_ids = {m["id"] for m in body["methods"]}
    # 4 tema + 3 metod global'de yer almalı
    assert topic_ids == {"T_ai", "T_med", "T_env", "T_econ"}, topic_ids
    assert method_ids == {"topsis", "vikor", "ahp"}, method_ids
