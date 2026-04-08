"""Path helpers for backend services.

Kept tiny so other modules can import it without pulling heavy ML deps.
"""

from __future__ import annotations

import os


def backend_root() -> str:
    # services/ -> app/ -> backend/
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def models_dir() -> str:
    return os.path.join(backend_root(), "models")
