import pytest
import yaml

from infrastructure.config import DEFAULT_POLL_INTERVAL_SECONDS, load_config


def _valid_env():
    return {
        "TELEGRAM_TOKEN": "t",
        "TELEGRAM_CHAT_ID": "c",
        "CWB_TOKEN": "w",
        "LOG": "./log/x.log",
        "AREAS": [[23.0, 22.0, 120.0, 121.0]],
    }


def _write_config(dir_path, data):
    (dir_path / "config.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_load_config_returns_env_section(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path, {"PROD": _valid_env()})
    assert load_config("PROD")["TELEGRAM_TOKEN"] == "t"


def test_load_config_missing_env_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path, {"PROD": _valid_env()})
    with pytest.raises(ValueError, match="STAGE"):
        load_config("STAGE")


def test_load_config_missing_required_key_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    del env["CWB_TOKEN"]
    _write_config(tmp_path, {"PROD": env})
    with pytest.raises(ValueError, match="CWB_TOKEN"):
        load_config("PROD")


def test_load_config_empty_yaml_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_config("PROD")


def test_load_config_placeholder_required_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["CWB_TOKEN"] = "<your_cwa_opendata_token>"
    _write_config(tmp_path, {"PROD": env})
    with pytest.raises(ValueError, match="CWB_TOKEN"):
        load_config("PROD")


def test_load_config_empty_required_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["TELEGRAM_TOKEN"] = "   "
    _write_config(tmp_path, {"PROD": env})
    with pytest.raises(ValueError, match="TELEGRAM_TOKEN"):
        load_config("PROD")


def test_areas_bare_boxes_get_default_names(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["AREAS"] = [[23.0, 22.0, 120.0, 121.0], [25.0, 24.0, 121.0, 122.0]]
    _write_config(tmp_path, {"PROD": env})
    areas = load_config("PROD")["AREAS"]
    assert areas == [
        {"name": "區域 1", "box": [23.0, 22.0, 120.0, 121.0]},
        {"name": "區域 2", "box": [25.0, 24.0, 121.0, 122.0]},
    ]


def test_areas_named_form_is_kept(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["AREAS"] = [{"name": "高雄", "box": [23.0, 22.0, 120.0, 121.0]}]
    _write_config(tmp_path, {"PROD": env})
    areas = load_config("PROD")["AREAS"]
    assert areas == [{"name": "高雄", "box": [23.0, 22.0, 120.0, 121.0]}]


def test_areas_named_entry_without_name_gets_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["AREAS"] = [{"box": [23.0, 22.0, 120.0, 121.0]}]
    _write_config(tmp_path, {"PROD": env})
    assert load_config("PROD")["AREAS"][0]["name"] == "區域 1"


def test_areas_bad_box_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["AREAS"] = [{"name": "高雄", "box": [23.0, 22.0, 120.0]}]  # only 3 numbers
    _write_config(tmp_path, {"PROD": env})
    with pytest.raises(ValueError, match="AREAS"):
        load_config("PROD")


def test_areas_empty_list_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["AREAS"] = []
    _write_config(tmp_path, {"PROD": env})
    with pytest.raises(ValueError, match="AREAS"):
        load_config("PROD")


def test_poll_interval_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path, {"PROD": _valid_env()})
    assert load_config("PROD")["POLL_INTERVAL_SECONDS"] == DEFAULT_POLL_INTERVAL_SECONDS


def test_poll_interval_explicit_kept(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["POLL_INTERVAL_SECONDS"] = 120
    _write_config(tmp_path, {"PROD": env})
    assert load_config("PROD")["POLL_INTERVAL_SECONDS"] == 120


def test_poll_interval_invalid_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["POLL_INTERVAL_SECONDS"] = 0
    _write_config(tmp_path, {"PROD": env})
    with pytest.raises(ValueError, match="POLL_INTERVAL_SECONDS"):
        load_config("PROD")


def test_healthcheck_url_kept_when_set(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["HEALTHCHECK_URL"] = "https://hc-ping.com/abc"
    _write_config(tmp_path, {"PROD": env})
    assert load_config("PROD")["HEALTHCHECK_URL"] == "https://hc-ping.com/abc"


def test_healthcheck_url_absent_normalizes_to_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path, {"PROD": _valid_env()})
    assert load_config("PROD")["HEALTHCHECK_URL"] == ""


def test_healthcheck_url_placeholder_normalizes_to_empty(tmp_path, monkeypatch):
    # A copied-but-unedited placeholder must disable pinging, not ping garbage.
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["HEALTHCHECK_URL"] = "<optional_healthchecks_io_ping_url>"
    _write_config(tmp_path, {"PROD": env})
    assert load_config("PROD")["HEALTHCHECK_URL"] == ""


def test_command_user_ids_kept_when_set(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["COMMAND_USER_IDS"] = [6006055946]
    _write_config(tmp_path, {"PROD": env})
    assert load_config("PROD")["COMMAND_USER_IDS"] == [6006055946]


def test_command_user_ids_absent_normalizes_to_empty_list(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path, {"PROD": _valid_env()})
    assert load_config("PROD")["COMMAND_USER_IDS"] == []


def test_command_user_ids_non_integer_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["COMMAND_USER_IDS"] = ["@someone"]
    _write_config(tmp_path, {"PROD": env})
    with pytest.raises(ValueError, match="COMMAND_USER_IDS"):
        load_config("PROD")


def test_legacy_line_keys_are_ignored(tmp_path, monkeypatch):
    """A config.yaml left over from the LINE era must still load fine."""
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["LINE_CHANNEL_ACCESS_TOKEN"] = "stale"
    env["IMGUR_CLIENT_ID"] = "stale"
    _write_config(tmp_path, {"PROD": env})
    config = load_config("PROD")
    assert config["TELEGRAM_TOKEN"] == "t"  # loads without error
