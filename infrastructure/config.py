import yaml

REQUIRED_KEYS = [
    "TELEGRAM_TOKEN",
    "TELEGRAM_CHAT_ID",
    "CWB_TOKEN",
    "LOG",
    "AREAS",
    "LINE_CHANNEL_ACCESS_TOKEN",
    "LINE_TO",
]


def load_config(env: str = "PROD") -> dict:
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError("config.yaml is empty or not a valid YAML mapping")

    if env not in config:
        raise ValueError(f"Environment '{env}' not found in config.yaml")

    env_config = config[env]
    missing = [key for key in REQUIRED_KEYS if key not in env_config]
    if missing:
        raise ValueError(f"Missing required config in {env}: {', '.join(missing)}")

    return env_config
