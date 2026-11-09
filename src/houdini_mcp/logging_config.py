from __future__ import annotations

import logging
import sys


def configure_logging(level: int) -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt='[{asctime}][{levelname: <8}][{name}] {message}',
            datefmt='%I:%M:%S%p',
            style='{',
        )
    )
    logging.basicConfig(level=level, handlers=[handler])
