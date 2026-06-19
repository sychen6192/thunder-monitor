import yaml

REQUIRED_KEYS = [
    "TELEGRAM_TOKEN",
    "TELEGRAM_CHAT_ID",
    "CWB_TOKEN",
    "LOG",
    "AREAS",
]

# LINE is optional: leave its keys blank/placeholder for a Telegram-only setup.
OPTIONAL_KEYS = ["IMGUR_CLIENT_ID", "LINE_CHANNEL_ACCESS_TOKEN", "LINE_TO"]


def _is_unset(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip()
        return stripped == "" or (stripped.startswith("<") and stripped.endswith(">"))
    return False


def load_config(env: str = "PROD") -> dict:
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError("config.yaml is empty or not a valid YAML mapping")

    if env not in config:
        raise ValueError(f"Environment '{env}' not found in config.yaml")

    env_config = config[env]

    missing = [key for key in REQUIRED_KEYS if key not in env_config or _is_unset(env_config[key])]
    if missing:
        raise ValueError(
            f"Missing or unset required config in {env}: {', '.join(missing)} "
            "(values must not be empty or <placeholders>)"
        )

    for key in OPTIONAL_KEYS:
        if key in env_config and _is_unset(env_config[key]):
            del env_config[key]

    return env_config
