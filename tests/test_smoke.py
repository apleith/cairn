from src.config import load


def test_config_loads(tmp_project):
    cfg = load()
    assert cfg["app"]["port"] == 5151
    assert "wearable" in cfg
