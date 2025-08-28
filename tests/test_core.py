import json
from unittest import mock

import builtins
import types

import core


def test_load_config_defaults_when_missing(tmp_path, monkeypatch):
    # Point CONFIG_PATH to a temp file that does not exist
    cfg_path = tmp_path / 'cfg.json'
    monkeypatch.setattr(core, 'CONFIG_PATH', cfg_path)
    cfg = core.load_config()
    assert cfg['api_url'] == ''
    assert cfg['api_key'] == ''
    assert cfg['interval_seconds'] == 60
    assert cfg['notify_mode'] == 'all'


def test_save_and_load_config_roundtrip(tmp_path, monkeypatch):
    cfg_path = tmp_path / 'cfg.json'
    monkeypatch.setattr(core, 'CONFIG_PATH', cfg_path)
    data = {'api_url': 'https://example.com/health', 'api_key': 'k', 'interval_seconds': 30, 'notify_mode': 'fail'}
    core.save_config(data)
    loaded = core.load_config()
    assert loaded == data


def test_check_api_success(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        class Resp:
            ok = True
        return Resp()

    monkeypatch.setattr(core.requests, 'get', fake_get)
    assert core.check_api('https://example.com/health', 'abc') is True


def test_check_api_failure_status(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        class Resp:
            ok = False
        return Resp()

    monkeypatch.setattr(core.requests, 'get', fake_get)
    assert core.check_api('https://example.com/health', '') is False


def test_check_api_exception(monkeypatch):
    def raise_exc(*args, **kwargs):
        raise core.requests.RequestException('boom')

    monkeypatch.setattr(core.requests, 'get', raise_exc)
    assert core.check_api('https://example.com/health', '') is False

