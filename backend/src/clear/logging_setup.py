"""Single stdout logger config. No network handlers at import time (quality bar)."""
from __future__ import annotations

import logging
import sys

def configure_logging(level: int = logging.INFO) -> logging.Logger:
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s :: %(message)s")
        )
        root.addHandler(handler)
    root.setLevel(level)
    return logging.getLogger("clear")
