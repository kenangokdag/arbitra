"""2026-08-09 - EvidencePack wiring fix davranis kaniti (guardian talebi).
Tek makale (openreview:PwxYoMvmvy, eski calistirmada 66 not_found_in_index
referans vardi) gercek pipeline'dan gecirilip citation_integrity/
literature_positioning finding'leri ESKI (fix-oncesi, scratchpad'de sakli)
rapor ile karsilastirilir."""

import asyncio
import json
import sys
import time
import traceback
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, r"C:\Users\USER\Desktop\arbitra-main")

import api.services.review_service as review_service  # noqa: E402
from api.services import consent_gate  # noqa: E402

PDF_PATH = Path(r"C:\Users\USER\Desktop\goldset_pdfs\openreview_PwxYoMvmvy.pdf")
OUT_PATH = Path(
    r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main"
    r"\492975e2-533f-4eaf-b2e8-4d52c4badcb1\scratchpad\spot_check_PwxYoMvmvy_after_fix.json"
)


async def run_one() -> dict:
    captured: dict = {}

    async def fake_update(job_id, **fields):
        captured.update(fields)

    async def fake_save_stages(job_id, tracker):
        pass

    async def fake_set_step(job_id, status, **extra):
        pass

    review_service._update = fake_update
    review_service._save_stages = fake_save_stages
    review_service._set_step = fake_set_step

    privacy = consent_gate.resolve_privacy(mode="author", is_author=True)
    data = PDF_PATH.read_bytes()
    job_id = uuid4()
    t0 = time.time()
    error = None
    try:
        await review_service.run_pipeline(
            job_id,
            data=data,
            kind="pdf",
            filename=PDF_PATH.name,
            mode="author",
            language="en",
            privacy=privacy,
        )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    elapsed = time.time() - t0

    return {"elapsed_s": round(elapsed, 1), "error": error, "report": captured.get("report")}


async def main() -> None:
    result = await run_one()
    OUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(f"bitti: {result['elapsed_s']}s, hata={result['error']}")
    print(f"yazildi: {OUT_PATH}")


asyncio.run(main())
