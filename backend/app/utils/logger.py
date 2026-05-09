import logging
import sys
import io

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Force UTF-8 so non-ASCII chars don't crash on Windows CP1252 consoles
        if hasattr(sys.stdout, "buffer"):
            stream = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        else:
            stream = sys.stdout
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
