from pathlib import Path

import pytest

import cliproxyapi.settings as settings_module
from cliproxyapi.settings import load_settings


def test_load_yaml_config_success(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "app:\n"
        "  log_level: INFO\n"
        "  once: false\n"
        "monitor:\n"
        "  target_count: 10\n"
        "  interval_seconds: 1800\n"
        "  max_register_attempts: 30\n"
        "  weekly_remaining_threshold_percent: 30\n"
        "cliproxy:\n"
        "  api_base: https://api.example.com\n"
        "  management_key: secret\n"
        "  timeout_seconds: 30\n"
        "  verify_tls: true\n"
        "registration:\n"
        "  email:\n"
        "    prefix: auto\n"
        "    domain: pid.im\n"
        "  imap:\n"
        "    host: imap.example.com\n"
        "    port: 993\n"
        "    username: user\n"
        "    password: pass\n"
        "    mailbox: INBOX\n"
        "    fetch_limit: 30\n"
        "    poll_interval_seconds: 2\n"
        "    otp_timeout_seconds: 180\n"
        "  proxy:\n"
        "    enabled: false\n"
        "    scheme: http\n"
        "    host: ''\n"
        "    username: ''\n"
        "    password: ''\n"
        "    direct_fallback_on_challenge: false\n"
        "  oauth:\n"
        "    issuer: https://auth.openai.com\n"
        "    client_id: app_id\n"
        "    redirect_uri: http://localhost:1455/auth/callback\n"
        "upload:\n"
        "  mode: memory_json\n"
        "  field_name: file\n"
        "  filename_pattern: '{email}.json'\n"
        "debug:\n"
        "  save_failed_upload_payload: false\n"
        "  failed_payload_dir: ./debug_failed_payloads\n",
        encoding="utf-8",
    )

    data = load_settings(str(cfg_file))
    assert data.app.log_level == "INFO"
    assert data.monitor.target_count == 10
    assert data.cliproxy.verify_tls is True
    assert data.registration.imap.port == 993


def test_load_yaml_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_settings("not-exists.yaml")


def test_load_settings_uses_default_config_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "app:\n"
        "  log_level: INFO\n"
        "  once: false\n"
        "monitor:\n"
        "  target_count: 10\n"
        "  interval_seconds: 1800\n"
        "  max_register_attempts: 30\n"
        "  weekly_remaining_threshold_percent: 30\n"
        "cliproxy:\n"
        "  api_base: https://api.example.com\n"
        "  management_key: secret\n"
        "  timeout_seconds: 30\n"
        "  verify_tls: true\n"
        "registration:\n"
        "  email:\n"
        "    prefix: auto\n"
        "    domain: pid.im\n"
        "  imap:\n"
        "    host: imap.example.com\n"
        "    port: 993\n"
        "    username: user\n"
        "    password: pass\n"
        "    mailbox: INBOX\n"
        "    fetch_limit: 30\n"
        "    poll_interval_seconds: 2\n"
        "    otp_timeout_seconds: 180\n"
        "  proxy:\n"
        "    enabled: false\n"
        "    scheme: http\n"
        "    host: ''\n"
        "    username: ''\n"
        "    password: ''\n"
        "    direct_fallback_on_challenge: false\n"
        "  oauth:\n"
        "    issuer: https://auth.openai.com\n"
        "    client_id: app_id\n"
        "    redirect_uri: http://localhost:1455/auth/callback\n"
        "upload:\n"
        "  mode: memory_json\n"
        "  field_name: file\n"
        "  filename_pattern: '{email}.json'\n"
        "debug:\n"
        "  save_failed_upload_payload: false\n"
        "  failed_payload_dir: ./debug_failed_payloads\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", cfg_file)

    data = load_settings()
    assert data.cliproxy.api_base == "https://api.example.com"


def test_load_settings_parses_string_booleans(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "app:\n"
        "  log_level: INFO\n"
        "  once: 'false'\n"
        "monitor:\n"
        "  target_count: 10\n"
        "  interval_seconds: 1800\n"
        "  max_register_attempts: 30\n"
        "  weekly_remaining_threshold_percent: 30\n"
        "cliproxy:\n"
        "  api_base: https://api.example.com\n"
        "  management_key: secret\n"
        "  timeout_seconds: 30\n"
        "  verify_tls: '0'\n"
        "registration:\n"
        "  email:\n"
        "    prefix: auto\n"
        "    domain: pid.im\n"
        "  imap:\n"
        "    host: imap.example.com\n"
        "    port: 993\n"
        "    username: user\n"
        "    password: pass\n"
        "    mailbox: INBOX\n"
        "    fetch_limit: 30\n"
        "    poll_interval_seconds: 2\n"
        "    otp_timeout_seconds: 180\n"
        "  proxy:\n"
        "    enabled: 'yes'\n"
        "    scheme: http\n"
        "    host: ''\n"
        "    username: ''\n"
        "    password: ''\n"
        "    direct_fallback_on_challenge: 'no'\n"
        "  oauth:\n"
        "    issuer: https://auth.openai.com\n"
        "    client_id: app_id\n"
        "    redirect_uri: http://localhost:1455/auth/callback\n"
        "upload:\n"
        "  mode: memory_json\n"
        "  field_name: file\n"
        "  filename_pattern: '{email}.json'\n"
        "debug:\n"
        "  save_failed_upload_payload: 'off'\n"
        "  failed_payload_dir: ./debug_failed_payloads\n",
        encoding="utf-8",
    )

    data = load_settings(str(cfg_file))
    assert data.app.once is False
    assert data.cliproxy.verify_tls is False
    assert data.registration.proxy.enabled is True
    assert data.registration.proxy.direct_fallback_on_challenge is False
    assert data.debug.save_failed_upload_payload is False


def test_load_settings_rejects_invalid_string_boolean(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "app:\n"
        "  log_level: INFO\n"
        "  once: maybe\n"
        "monitor:\n"
        "  target_count: 10\n"
        "  interval_seconds: 1800\n"
        "  max_register_attempts: 30\n"
        "  weekly_remaining_threshold_percent: 30\n"
        "cliproxy:\n"
        "  api_base: https://api.example.com\n"
        "  management_key: secret\n"
        "  timeout_seconds: 30\n"
        "  verify_tls: true\n"
        "registration:\n"
        "  email:\n"
        "    prefix: auto\n"
        "    domain: pid.im\n"
        "  imap:\n"
        "    host: imap.example.com\n"
        "    port: 993\n"
        "    username: user\n"
        "    password: pass\n"
        "    mailbox: INBOX\n"
        "    fetch_limit: 30\n"
        "    poll_interval_seconds: 2\n"
        "    otp_timeout_seconds: 180\n"
        "  proxy:\n"
        "    enabled: false\n"
        "    scheme: http\n"
        "    host: ''\n"
        "    username: ''\n"
        "    password: ''\n"
        "    direct_fallback_on_challenge: false\n"
        "  oauth:\n"
        "    issuer: https://auth.openai.com\n"
        "    client_id: app_id\n"
        "    redirect_uri: http://localhost:1455/auth/callback\n"
        "upload:\n"
        "  mode: memory_json\n"
        "  field_name: file\n"
        "  filename_pattern: '{email}.json'\n"
        "debug:\n"
        "  save_failed_upload_payload: false\n"
        "  failed_payload_dir: ./debug_failed_payloads\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"app\.once"):
        load_settings(str(cfg_file))
