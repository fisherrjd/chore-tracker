"""Shared fixtures.

The app reads ``CHORE_BASE`` (for templates/static) and ``CHORE_CONFIG`` (the
config file) at *import time*, so both env vars are set before importing
``chore_tracker.main``. Tests run against an isolated temp config file, never
the real ``config.yaml``.
"""
import os
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Templates and static assets live at the project root.
os.environ["CHORE_BASE"] = str(PROJECT_ROOT)

# Point the app at a throwaway config file for the whole session. Guarded so a
# stray re-import of this module can never repoint the app at a second temp dir.
if "CHORE_CONFIG" not in os.environ:
    _TMP_DIR = Path(tempfile.mkdtemp(prefix="chore-tests-"))
    os.environ["CHORE_CONFIG"] = str(_TMP_DIR / "config.yaml")

from starlette.testclient import TestClient  # noqa: E402

from chore_tracker import checks  # noqa: E402
from chore_tracker.main import CONFIG_PATH as APP_CONFIG_PATH  # noqa: E402
from chore_tracker.main import app  # noqa: E402
from tests.helpers import default_config, write_config  # noqa: E402

# Sanity: the app must be using our temp config, not the real one.
assert str(APP_CONFIG_PATH) == os.environ["CHORE_CONFIG"], APP_CONFIG_PATH


@pytest.fixture(autouse=True)
def fresh_state():
    """Reset the in-memory checklist store and seed the default config."""
    checks._state.clear()
    write_config(default_config())
    yield
    checks._state.clear()


@pytest.fixture
def client():
    # No `with` block: we deliberately skip the lifespan so the APScheduler
    # background scheduler never starts during tests.
    return TestClient(app)
