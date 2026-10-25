"""Script kiểm tra cấu hình Supabase không bao giờ in khoá hay URL."""

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_supabase_config.py"
SPEC = importlib.util.spec_from_file_location("check_supabase_config", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

SECRET_URL = "https://abcdefgh.supabase.co"
SECRET_KEY = "sb_publishable_SECRET_VALUE_123"


class _Res:
    count = 5


class _Table:
    def select(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return _Res()


class _Client:
    def table(self, name):
        return _Table()


def _factory(url, key):
    return _Client()


def test_report_never_contains_secret_values():
    env = {"SUPABASE_URL": SECRET_URL, "SUPABASE_ANON_KEY": SECRET_KEY}
    report, code = mod.run(env, client_factory=_factory)
    text = json.dumps(report)
    assert code == 0 and report["ok"] is True
    assert SECRET_KEY not in text and SECRET_URL not in text and "abcdefgh" not in text
    assert report["key_var"] == "SUPABASE_ANON_KEY" and report["key_role"] == "anon"


def test_offline_mode_does_not_call_network_and_hides_values():
    env = {"SUPABASE_URL": SECRET_URL, "SUPABASE_ANON_KEY": SECRET_KEY}

    def boom(*a):
        raise AssertionError("không được gọi mạng ở chế độ --offline")

    report, code = mod.run(env, offline=True, client_factory=boom)
    assert code == 0 and SECRET_KEY not in json.dumps(report)


def test_missing_or_placeholder_config_exits_1():
    assert mod.run({}, offline=True)[1] == 1
    placeholder = {
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_ANON_KEY": "your-key",
    }
    assert mod.run(placeholder, offline=True)[1] == 1


def test_service_role_key_is_rejected_with_code_2():
    env = {"SUPABASE_URL": SECRET_URL, "SUPABASE_SERVICE_ROLE_KEY": "sb_secret_SHOULD_NOT_APPEAR"}
    report, code = mod.run(env, offline=True)
    assert code == 2 and "SHOULD_NOT_APPEAR" not in json.dumps(report)
