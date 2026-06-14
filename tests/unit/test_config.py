import pytest
import yaml

from infrastructure.config import load_config


def _valid_env():
    return {
        "TELEGRAM_TOKEN": "t",
        "TELEGRAM_CHAT_ID": "c",
        "CWB_TOKEN": "w",
        "LOG": "./log/x.log",
        "AREAS": [[23.0, 22.0, 120.0, 121.0]],
        "LINE_CHANNEL_ACCESS_TOKEN": "la",
        "LINE_TO": "U1",
    }


def _write_config(dir_path, data):
    (dir_path / "config.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


def test_load_config_returns_env_section(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path, {"PROD": _valid_env()})
    assert load_config("PROD")["LINE_TO"] == "U1"


def test_load_config_missing_env_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path, {"PROD": _valid_env()})
    with pytest.raises(ValueError, match="STAGE"):
        load_config("STAGE")


def test_load_config_missing_required_key_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    del env["LINE_TO"]
    _write_config(tmp_path, {"PROD": env})
    with pytest.raises(ValueError, match="LINE_TO"):
        load_config("PROD")


def test_load_config_empty_yaml_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_config("PROD")
