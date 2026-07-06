"""
Prometheus Logging System
-------------------------
Every module gets a logger via get_logger(__name__). Logs go to both
console and a file so you have a persistent research/debug trail —
this matters later when Prometheus is reasoning about hardware and
you need to reconstruct what it did and why.
"""
import logging
import os
from .config import config


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured (avoids duplicate handlers on re-import)
        return logger

    logger.setLevel(config.log_level)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    os.makedirs(os.path.dirname(config.log_path), exist_ok=True)
    file_handler = logging.FileHandler(config.log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
