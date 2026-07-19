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

    return env_config
