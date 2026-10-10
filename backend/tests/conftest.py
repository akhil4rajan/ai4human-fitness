import pytest


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("AI4HUMAN_DB", str(tmp_path / "test.db"))
    import app.main
    monkeypatch.setattr(app.main, "_store", None)
