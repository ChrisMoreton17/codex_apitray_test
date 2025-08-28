import json
from pathlib import Path
from typing import Dict

import requests


CONFIG_PATH = Path.home() / '.api_tray_config.json'


def load_config() -> Dict[str, object]:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open('r', encoding='utf-8') as f:
            return json.load(f)
    return {'api_url': '', 'api_key': '', 'interval_seconds': 60, 'notify_mode': 'all'}


def save_config(config: Dict[str, object]) -> None:
    with CONFIG_PATH.open('w', encoding='utf-8') as f:
        json.dump(config, f)


def check_api_details(api_url: str, api_key: str):
    """Return (ok: bool, status: int|None, error: str|None).

    Makes a GET request to api_url with optional Bearer api_key.
    """
    if not api_url:
        return False, None, None
    try:
        headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}
        response = requests.get(api_url, headers=headers, timeout=5)
        return bool(response.ok), int(getattr(response, 'status_code', 0) or 0), None
    except requests.RequestException as e:
        return False, None, str(e)


def check_api(api_url: str, api_key: str) -> bool:
    ok, _status, _err = check_api_details(api_url, api_key)
    return ok
