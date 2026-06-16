from pathlib import Path

import yaml

from infrastructure.config import REQUIRED_KEYS

CONFIG_EXAMPLE = Path(__file__).resolve().parent.parent.parent / "config.example.yaml"


def test_config_example_has_required_keys_for_both_envs():
    with open(CONFIG_EXAMPLE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for env in ("PROD", "STAGE"):
        assert env in data, f"missing env {env}"
        for key in REQUIRED_KEYS:
            assert key in data[env], f"{env} missing {key}"
