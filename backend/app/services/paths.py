"""Centralized path helpers for backend services.

Keeps filesystem paths consistent across services and avoids hard-coded
relative paths like "data/processed".
"""

from __future__ import annotations

import os


def backend_root() -> str:
    # services/ -> app/ -> backend/
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def data_dir() -> str:
    return os.path.join(backend_root(), "data")


def processed_data_dir() -> str:
    return os.path.join(data_dir(), "processed")


def raw_data_dir() -> str:
    return os.path.join(data_dir(), "raw")


def models_dir() -> str:
    return os.path.join(backend_root(), "models")
