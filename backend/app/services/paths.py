"""Centralized path helpers for backend services.

Canonical layout (required):

        backend/data/
            training/
                raw/
                processed/
            testing/
                raw/
                processed/

Runtime services default to the testing dataset ("testing/*").
"""

from __future__ import annotations

import os


def backend_root() -> str:
    # services/ -> app/ -> backend/
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def data_dir() -> str:
    return os.path.join(backend_root(), "data")


def training_dir() -> str:
    return os.path.join(data_dir(), "training")


def training_raw_dir() -> str:
    return os.path.join(training_dir(), "raw")


def training_processed_dir() -> str:
    return os.path.join(training_dir(), "processed")


def testing_dir() -> str:
    return os.path.join(data_dir(), "testing")


def testing_raw_dir() -> str:
    return os.path.join(testing_dir(), "raw")


def testing_processed_dir() -> str:
    return os.path.join(testing_dir(), "processed")


def processed_data_dir() -> str:
    """Backwards-compatible alias for the runtime (testing) processed directory."""
    return testing_processed_dir()


def raw_data_dir() -> str:
    """Backwards-compatible alias for the runtime (testing) raw directory."""
    return testing_raw_dir()


def models_dir() -> str:
    return os.path.join(backend_root(), "models")
