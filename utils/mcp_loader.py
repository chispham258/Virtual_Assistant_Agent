import json
import os


def _expand_env_vars(value):
    """Recursively expand $VAR placeholders in strings inside a config dict/list."""
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    return value


def load_mcp_config(
    config_path: str = "config/mcp_config.json",
    server_names: list[str] | None = None,
) -> dict:
    full_path = os.path.join(os.getcwd(), config_path)

    with open(full_path, "r") as f:
        config = json.load(f)

    if server_names:
        config = {k: v for k, v in config.items() if k in server_names}

    return _expand_env_vars(config)
