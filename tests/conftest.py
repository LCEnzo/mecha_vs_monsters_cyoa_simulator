import pytest

import utils.settings as settings_mod


@pytest.fixture(autouse=True)
def set_debug_mode(monkeypatch):
    monkeypatch.setenv("MODE", "DEBUG")

    settings_mod.settings = settings_mod.Settings()
