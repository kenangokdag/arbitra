"""F13-S14 Cron — paylaşılan helper'lar.

Tüm cron job'lar bu modülden `bootstrap_repo_path()` + `cron_logger()` + ortak
arg parser desenini kullanır.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def bootstrap_repo_path() -> None:
    """sys.path'a repo root'u ekle (cron Render servisi içinde `python -m` ile çalışır)."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))


def cron_logger(job_name: str) -> logging.Logger:
    """Yapısal log: INFO baz, stderr; Render log drainer kolay parse eder."""
    logger = logging.getLogger(f"cron.{job_name}")
    if not logger.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def build_cron_arg_parser(job_name: str) -> argparse.ArgumentParser:
    """`--dry-run` standart flag'i her job'a otomatik koy."""
    parser = argparse.ArgumentParser(
        prog=f"cron.{job_name}",
        description=f"PaperMind cron job: {job_name}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="DB mutasyonu yapma; sadece etkilenecek satır sayısını yaz.",
    )
    return parser
