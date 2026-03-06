import pytest

from cliproxyapi.app import (
    _resolve_startup_mode,
    _startup_mode_message,
    _validate_settings,
    parse_args,
)
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

def test_resolve_startup_mode_prefers_cli_once() -> None:
    mode, source = _resolve_startup_mode(args_once=True, config_once=False)
    assert mode == "once"
    assert source == "cli"


def test_resolve_startup_mode_uses_config_once() -> None:
    mode, source = _resolve_startup_mode(args_once=False, config_once=True)
    assert mode == "once"
    assert source == "config"


def test_resolve_startup_mode_defaults_to_forever() -> None:
    mode, source = _resolve_startup_mode(args_once=False, config_once=False)
    assert mode == "forever"
    assert source == "default"


def test_startup_mode_message_for_once_by_cli() -> None:
    assert _startup_mode_message(mode="once", source="cli", interval_seconds=1800) == (
        "启动模式：单轮执行（来源：命令行参数 --once）。"
        "执行策略：仅执行一轮监控，强制新增 1 个账号，完成后退出。"
    )


def test_startup_mode_message_for_forever() -> None:
    assert _startup_mode_message(mode="forever", source="default", interval_seconds=1800) == (
        "启动模式：持续监控（来源：默认配置）。"
        "执行策略：每 1800 秒执行一轮监控，按目标数量自动补齐账号。"
    )


def test_startup_mode_message_for_once_by_config() -> None:
    assert _startup_mode_message(mode="once", source="config", interval_seconds=1800) == (
        "启动模式：单轮执行（来源：配置项 app.once）。"
        "执行策略：仅执行一轮监控，按缺口补齐账号，完成后退出。"
    )


def test_parse_args_supports_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["cliproxyapi", "--once"])
    args = parse_args()
    assert args.once is True


def test_parse_args_rejects_config_option(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["cliproxyapi", "--config", "foo.yaml"])
    with pytest.raises(SystemExit):
        parse_args()


def _build_valid_settings(
    *,
    max_register_attempts: int = 1,
    target_count: int = 10,
    interval_seconds: int = 600,
    weekly_threshold_percent: float = 30,
    imap_fetch_limit: int = 5,
    imap_poll_interval_seconds: int = 2,
    imap_otp_timeout_seconds: int = 180,
) -> Settings:
    return Settings(
        app=AppConfig(log_level="INFO", once=False),
        monitor=MonitorConfig(
            target_count=target_count,
            interval_seconds=interval_seconds,
            max_register_attempts=max_register_attempts,
            weekly_remaining_threshold_percent=weekly_threshold_percent,
        ),
        cliproxy=CliproxyConfig(
            api_base="https://api.example.com",
            management_key="secret",
            timeout_seconds=30,
            verify_tls=True,
        ),
        registration=RegistrationConfig(
            email=RegistrationEmailConfig(prefix="test", domain="pid.im"),
            imap=RegistrationImapConfig(
                host="imap.example.com",
                port=993,
                username="user",
                password="pass",
                mailbox="INBOX",
                fetch_limit=imap_fetch_limit,
                poll_interval_seconds=imap_poll_interval_seconds,
                otp_timeout_seconds=imap_otp_timeout_seconds,
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
        debug=DebugConfig(save_failed_upload_payload=False, failed_payload_dir="./debug_failed_payloads"),
    )


def test_validate_settings_rejects_non_positive_max_register_attempts() -> None:
    settings = _build_valid_settings(max_register_attempts=0)
    with pytest.raises(SystemExit):
        _validate_settings(settings)


def test_validate_settings_rejects_non_positive_target_count() -> None:
    settings = _build_valid_settings(target_count=0)
    with pytest.raises(SystemExit):
        _validate_settings(settings)


def test_validate_settings_rejects_non_positive_interval_seconds() -> None:
    settings = _build_valid_settings(interval_seconds=0)
    with pytest.raises(SystemExit):
        _validate_settings(settings)


def test_validate_settings_rejects_invalid_weekly_threshold_percent() -> None:
    settings_low = _build_valid_settings(weekly_threshold_percent=-1)
    settings_high = _build_valid_settings(weekly_threshold_percent=101)

    with pytest.raises(SystemExit):
        _validate_settings(settings_low)
    with pytest.raises(SystemExit):
        _validate_settings(settings_high)


def test_validate_settings_rejects_non_positive_imap_fetch_limit() -> None:
    settings = _build_valid_settings(imap_fetch_limit=0)
    with pytest.raises(SystemExit):
        _validate_settings(settings)


def test_validate_settings_rejects_non_positive_imap_poll_interval() -> None:
    settings = _build_valid_settings(imap_poll_interval_seconds=0)
    with pytest.raises(SystemExit):
        _validate_settings(settings)


def test_validate_settings_rejects_non_positive_imap_otp_timeout() -> None:
    settings = _build_valid_settings(imap_otp_timeout_seconds=0)
    with pytest.raises(SystemExit):
        _validate_settings(settings)


def test_validate_settings_returns_all_errors_in_one_message() -> None:
    settings = _build_valid_settings(
        target_count=0,
        interval_seconds=0,
        imap_fetch_limit=0,
    )

    with pytest.raises(SystemExit) as exc_info:
        _validate_settings(settings)

    message = str(exc_info.value)
    assert "`monitor.target_count`" in message
    assert "`monitor.interval_seconds`" in message
    assert "`registration.imap.fetch_limit`" in message
