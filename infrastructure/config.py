import yaml

REQUIRED_KEYS = [
    "TELEGRAM_TOKEN",
    "TELEGRAM_CHAT_ID",
    "CWB_TOKEN",
    "LOG",
    "AREAS",
]

DEFAULT_POLL_INTERVAL_SECONDS = 60


def _is_unset(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip()
        return stripped == "" or (stripped.startswith("<") and stripped.endswith(">"))
    return False


def _normalize_areas(areas) -> list[dict]:
    """Normalize AREAS entries to ``{"name": str, "box": [top, down, left, right]}``.

    Accepts either the named form (``{name: 高雄, box: [...]}```) or the legacy
    bare-box form (``[top, down, left, right]``); bare boxes get "區域 N" names.
    """
    if not isinstance(areas, list) or not areas:
        raise ValueError("AREAS must be a non-empty list")
    normalized = []
    for i, entry in enumerate(areas, 1):
        if isinstance(entry, dict):
            name = entry.get("name")
            name = f"區域 {i}" if _is_unset(name) else str(name).strip()
            box = entry.get("box")
        else:
            name, box = f"區域 {i}", entry
        if (
            not isinstance(box, list)
            or len(box) != 4
            or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in box)
        ):
            raise ValueError(
                f"AREAS entry {i} must provide a box of 4 numbers [top, down, left, right]"
            )
        normalized.append({"name": name, "box": [float(v) for v in box]})
    return normalized


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

    env_config["AREAS"] = _normalize_areas(env_config["AREAS"])

    interval = env_config.get("POLL_INTERVAL_SECONDS")
    if _is_unset(interval):
        env_config["POLL_INTERVAL_SECONDS"] = DEFAULT_POLL_INTERVAL_SECONDS
    elif not isinstance(interval, int) or isinstance(interval, bool) or interval <= 0:
        raise ValueError("POLL_INTERVAL_SECONDS must be a positive integer")

    # Optional dead-man's-switch ping URL. Normalize absent/blank/placeholder to
    # "" (disabled) so the monitor never pings a leftover placeholder string.
    if _is_unset(env_config.get("HEALTHCHECK_URL")):
        env_config["HEALTHCHECK_URL"] = ""

    # Optional user ids allowed to run commands from any chat (the push chat is
    # always allowed). Numeric Telegram user ids only — usernames are spoofable
    # and Telegram may not include them on every update.
    user_ids = env_config.get("COMMAND_USER_IDS")
    if _is_unset(user_ids):
        env_config["COMMAND_USER_IDS"] = []
    elif not isinstance(user_ids, list) or not all(
        isinstance(v, int) and not isinstance(v, bool) for v in user_ids
    ):
        raise ValueError("COMMAND_USER_IDS must be a list of numeric Telegram user ids")

    return env_config
