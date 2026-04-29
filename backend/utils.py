"""
Utility helpers — logging, clamping.
"""
import logging, sys


def clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, value))


def setup_logging(level=logging.INFO) -> logging.Logger:
    logger = logging.getLogger("smartchair")
    logger.setLevel(level)
    if not logger.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S"))
        logger.addHandler(h)
    return logger


logger = setup_logging()
