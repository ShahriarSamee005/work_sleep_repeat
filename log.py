import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup(console=True):
    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = str(Path.home() / "AppData" / "Roaming")
    log_dir = Path(appdata) / "WorkSleepRepeat"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "wsr.log"

    logger = logging.getLogger("wsr")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s %(levelname)-5s %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    fh = RotatingFileHandler(str(log_path), maxBytes=1_000_000, backupCount=3,
                             encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    if console:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    return logger


_logger = None


def get():
    global _logger
    if _logger is None:
        _logger = setup(console=not getattr(sys, "frozen", False))
    return _logger
