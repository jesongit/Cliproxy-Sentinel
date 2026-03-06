from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import cliproxyapi.registration.registrar as registrar_module
from cliproxyapi.registration.registrar import register_one
from cliproxyapi.settings import (
    RegistrationConfig,
    RegistrationEmailConfig,
    RegistrationImapConfig,
    RegistrationOauthConfig,
    RegistrationProxyConfig,
)


def test_get_registration_module_uses_internal_module() -> None:
    module = registrar_module._get_registration_module()
    assert hasattr(module, "ProtocolRegistrar")
    assert hasattr(module, "generate_random_password")
    assert module.__name__.startswith("cliproxyapi.registration.")


def _registration_cfg() -> RegistrationConfig:
    return RegistrationConfig(
        email=RegistrationEmailConfig(prefix="auto", domain="pid.im"),
        imap=RegistrationImapConfig(
            host="imap.example.com",
            port=993,
            username="u",
            password="p",
            mailbox="INBOX",
            fetch_limit=30,
            poll_interval_seconds=2,
            otp_timeout_seconds=180,
        ),
        proxy=RegistrationProxyConfig(
            enabled=False,
            scheme="http",
            host="",
            username="",
            password="",
            direct_fallback_on_challenge=False,
        ),
        oauth=RegistrationOauthConfig(
            issuer="https://auth.openai.com",
            client_id="app_id",
            redirect_uri="http://localhost:1455/auth/callback",
        ),
    )


def test_register_one_returns_token_payload(monkeypatch) -> None:
    captured = {}
    fake_module = SimpleNamespace()

    class DummyRegistrar:
        def __init__(self, proxy_url=None):
            self.proxy_url = proxy_url

        def register(self, account_data, password):
            captured["email"] = account_data["email"]
            captured["password"] = password
            fake_module.save_token_json(  # type: ignore[attr-defined]
                account_data["email"],
                "acc-token",
                "ref-token",
                "id-token",
            )
            return True, "Success"

    fake_module = SimpleNamespace(
        EMAIL_PREFIX="",
        EMAIL_DOMAIN="",
        IMAP_HOST="",
        IMAP_PORT=0,
        IMAP_USERNAME="",
        IMAP_PASSWORD="",
        IMAP_MAILBOX="",
        IMAP_FETCH_LIMIT=0,
        IMAP_POLL_INTERVAL_SECONDS=0,
        OTP_POLL_TIMEOUT_SECONDS=0,
        PROXY_ENABLED=False,
        PROXY_SCHEME="http",
        PROXY_HOST="",
        PROXY_USERNAME="",
        PROXY_PASSWORD="",
        PROXY_DIRECT_FALLBACK_ON_CHALLENGE=False,
        OAUTH_ISSUER="",
        OAUTH_CLIENT_ID="",
        OAUTH_REDIRECT_URI="",
        ProtocolRegistrar=DummyRegistrar,
        generate_random_password=lambda: "P@ssw0rd",
        get_runtime_proxy_url=lambda: None,
        save_token_json=lambda *_args, **_kwargs: "__unused__",
    )

    monkeypatch.setattr("cliproxyapi.registration.registrar._get_registration_module", lambda: fake_module)

    payload, reason = register_one(_registration_cfg())
    assert reason == "Success"
    assert payload is not None
    assert payload["email"] == captured["email"]
    assert payload["access_token"] == "acc-token"


def test_register_one_returns_none_when_register_failed(monkeypatch) -> None:
    class DummyRegistrar:
        def __init__(self, proxy_url=None):
            self.proxy_url = proxy_url

        def register(self, account_data, password):
            return False, "失败"

    fake_module = SimpleNamespace(
        EMAIL_PREFIX="",
        EMAIL_DOMAIN="",
        IMAP_HOST="",
        IMAP_PORT=0,
        IMAP_USERNAME="",
        IMAP_PASSWORD="",
        IMAP_MAILBOX="",
        IMAP_FETCH_LIMIT=0,
        IMAP_POLL_INTERVAL_SECONDS=0,
        OTP_POLL_TIMEOUT_SECONDS=0,
        PROXY_ENABLED=False,
        PROXY_SCHEME="http",
        PROXY_HOST="",
        PROXY_USERNAME="",
        PROXY_PASSWORD="",
        PROXY_DIRECT_FALLBACK_ON_CHALLENGE=False,
        OAUTH_ISSUER="",
        OAUTH_CLIENT_ID="",
        OAUTH_REDIRECT_URI="",
        ProtocolRegistrar=DummyRegistrar,
        generate_random_password=lambda: "P@ssw0rd",
        get_runtime_proxy_url=lambda: None,
    )

    monkeypatch.setattr("cliproxyapi.registration.registrar._get_registration_module", lambda: fake_module)

    payload, reason = register_one(_registration_cfg())
    assert payload is None
    assert reason == "失败"


def test_register_one_builds_codex_payload_in_memory(monkeypatch) -> None:
    class DummyRegistrar:
        def __init__(self, proxy_url=None):
            self.proxy_url = proxy_url

        def register(self, account_data, password):
            fake_module.save_token_json(  # type: ignore[attr-defined]
                account_data["email"],
                "acc-token",
                "ref-token",
                "id-token",
            )
            return True, "Success"

    legacy_save_called = {"count": 0}
    exp_dt = datetime(2026, 3, 13, 15, 0, 0, tzinfo=timezone(timedelta(hours=8)))
    exp_ts = int(exp_dt.timestamp())

    def _legacy_save_token_json(*_args, **_kwargs):
        legacy_save_called["count"] += 1
        return "__legacy_should_not_be_called__"

    fake_module = SimpleNamespace(
        EMAIL_PREFIX="",
        EMAIL_DOMAIN="",
        IMAP_HOST="",
        IMAP_PORT=0,
        IMAP_USERNAME="",
        IMAP_PASSWORD="",
        IMAP_MAILBOX="",
        IMAP_FETCH_LIMIT=0,
        IMAP_POLL_INTERVAL_SECONDS=0,
        OTP_POLL_TIMEOUT_SECONDS=0,
        PROXY_ENABLED=False,
        PROXY_SCHEME="http",
        PROXY_HOST="",
        PROXY_USERNAME="",
        PROXY_PASSWORD="",
        PROXY_DIRECT_FALLBACK_ON_CHALLENGE=False,
        OAUTH_ISSUER="",
        OAUTH_CLIENT_ID="",
        OAUTH_REDIRECT_URI="",
        ProtocolRegistrar=DummyRegistrar,
        generate_random_password=lambda: "P@ssw0rd",
        get_runtime_proxy_url=lambda: None,
        decode_jwt_payload=lambda _token: {
            "https://api.openai.com/auth": {"chatgpt_account_id": "acc-id-1"},
            "exp": exp_ts,
        },
        save_token_json=_legacy_save_token_json,
    )

    monkeypatch.setattr("cliproxyapi.registration.registrar._get_registration_module", lambda: fake_module)

    payload, reason = register_one(_registration_cfg())
    assert reason == "Success"
    assert payload is not None
    assert legacy_save_called["count"] == 0
    assert payload["type"] == "codex"
    assert payload["account_id"] == "acc-id-1"
    assert payload["expired"] == "2026-03-13T15:00:00+08:00"
