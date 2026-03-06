from unittest.mock import Mock

from cliproxyapi.monitor.scheduler import run_once
from cliproxyapi.settings import (
    AppConfig,
    CliproxyConfig,
    DebugConfig,
    MonitorConfig,
    RegistrationConfig,
    RegistrationEmailConfig,
    RegistrationImapConfig,
    RegistrationOauthConfig,
    RegistrationProxyConfig,
    Settings,
    UploadConfig,
)


def _settings() -> Settings:
    return Settings(
        app=AppConfig(log_level="INFO", once=True),
        monitor=MonitorConfig(
            target_count=2,
            interval_seconds=1800,
            max_register_attempts=5,
            weekly_remaining_threshold_percent=30,
        ),
        cliproxy=CliproxyConfig(
            api_base="https://api.example.com",
            management_key="secret",
            timeout_seconds=30,
            verify_tls=True,
        ),
        registration=RegistrationConfig(
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
        ),
        upload=UploadConfig(mode="memory_json", field_name="file", filename_pattern="{email}.json"),
        debug=DebugConfig(
            save_failed_upload_payload=False,
            failed_payload_dir="./debug_failed_payloads",
        ),
    )


def test_run_once_registers_until_missing_filled() -> None:
    client = Mock()
    client.list_auth_files.side_effect = [
        [
            {"id": "1", "type": "codex", "status": "active", "expired": False},
            {"id": "2", "type": "codex", "expired": True},
        ],
        [{"id": "1", "type": "codex", "status": "active", "expired": False}],
        [
            {"id": "1", "type": "codex", "status": "active", "expired": False},
            {"id": "3", "type": "codex", "status": "active", "expired": False},
        ],
    ]
    client.delete_auth_file.return_value = True

    def fake_register(_cfg):
        return (
            {
                "email": "a@b.com",
                "access_token": "acc",
                "refresh_token": "ref",
                "id_token": "id",
            },
            "Success",
        )

    summary = run_once(client, _settings(), register_func=fake_register)
    assert summary["uploaded"] == 1
    assert summary["missing_count"] == 0
    client.upload_auth_payload.assert_called_once()


def test_run_once_stops_when_reach_max_attempts() -> None:
    client = Mock()
    client.list_auth_files.side_effect = [
        [{"id": "1", "type": "codex", "status": "active", "expired": False}],
        [{"id": "1", "type": "codex", "status": "active", "expired": False}],
    ]

    settings = _settings()
    settings = Settings(
        app=settings.app,
        monitor=MonitorConfig(
            target_count=2,
            interval_seconds=1800,
            max_register_attempts=2,
            weekly_remaining_threshold_percent=30,
        ),
        cliproxy=settings.cliproxy,
        registration=settings.registration,
        upload=settings.upload,
        debug=settings.debug,
    )

    def fake_register(_cfg):
        return None, "失败"

    summary = run_once(client, settings, register_func=fake_register)
    assert summary["attempts"] == 2
    assert summary["uploaded"] == 0


def test_run_once_does_not_count_upload_when_codex_not_increased() -> None:
    client = Mock()
    client.list_auth_files.side_effect = [
        [{"id": "1", "type": "codex", "status": "active", "expired": False}],
        [{"id": "1", "type": "codex", "status": "active", "expired": False}],
        [
            {"id": "1", "type": "codex", "status": "active", "expired": False},
            {"id": "u1", "type": "unknown", "status": "active", "expired": False},
        ],
    ]

    settings = _settings()
    settings = Settings(
        app=settings.app,
        monitor=MonitorConfig(
            target_count=2,
            interval_seconds=1800,
            max_register_attempts=1,
            weekly_remaining_threshold_percent=30,
        ),
        cliproxy=settings.cliproxy,
        registration=settings.registration,
        upload=settings.upload,
        debug=settings.debug,
    )

    def fake_register(_cfg):
        return (
            {
                "email": "a@b.com",
                "access_token": "acc",
                "refresh_token": "ref",
                "id_token": "id",
                "type": "codex",
            },
            "Success",
        )

    summary = run_once(client, settings, register_func=fake_register)
    assert summary["attempts"] == 1
    assert summary["uploaded"] == 0
    assert summary["missing_count"] == 1
    client.upload_auth_payload.assert_called_once()


def test_run_once_force_add_one_uploads_even_when_target_already_met() -> None:
    client = Mock()
    client.list_auth_files.side_effect = [
        [{"id": "1", "type": "codex", "status": "active", "expired": False}],
        [{"id": "1", "type": "codex", "status": "active", "expired": False}],
        [
            {"id": "1", "type": "codex", "status": "active", "expired": False},
            {"id": "2", "type": "codex", "status": "active", "expired": False},
        ],
    ]

    settings = _settings()
    settings = Settings(
        app=settings.app,
        monitor=MonitorConfig(
            target_count=1,
            interval_seconds=1800,
            max_register_attempts=2,
            weekly_remaining_threshold_percent=30,
        ),
        cliproxy=settings.cliproxy,
        registration=settings.registration,
        upload=settings.upload,
        debug=settings.debug,
    )

    def fake_register(_cfg):
        return (
            {
                "email": "a@b.com",
                "access_token": "acc",
                "refresh_token": "ref",
                "id_token": "id",
                "type": "codex",
            },
            "Success",
        )

    summary = run_once(client, settings, register_func=fake_register, force_add_one=True)
    assert summary["attempts"] == 1
    assert summary["uploaded"] == 1
    assert summary["missing_count"] == 0
    client.upload_auth_payload.assert_called_once()


def test_run_once_force_add_one_respects_max_attempts() -> None:
    client = Mock()
    client.list_auth_files.side_effect = [
        [{"id": "1", "type": "codex", "status": "active", "expired": False}],
        [{"id": "1", "type": "codex", "status": "active", "expired": False}],
    ]

    settings = _settings()
    settings = Settings(
        app=settings.app,
        monitor=MonitorConfig(
            target_count=1,
            interval_seconds=1800,
            max_register_attempts=2,
            weekly_remaining_threshold_percent=30,
        ),
        cliproxy=settings.cliproxy,
        registration=settings.registration,
        upload=settings.upload,
        debug=settings.debug,
    )

    def fake_register(_cfg):
        return None, "失败"

    summary = run_once(client, settings, register_func=fake_register, force_add_one=True)
    assert summary["attempts"] == 2
    assert summary["uploaded"] == 0
    assert summary["missing_count"] == 1
