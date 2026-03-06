from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"


@dataclass(frozen=True)
class AppConfig:
    log_level: str
    once: bool


@dataclass(frozen=True)
class MonitorConfig:
    target_count: int
    interval_seconds: int
    max_register_attempts: int
    weekly_remaining_threshold_percent: float


@dataclass(frozen=True)
class CliproxyConfig:
    api_base: str
    management_key: str
    timeout_seconds: int
    verify_tls: bool


@dataclass(frozen=True)
class RegistrationEmailConfig:
    prefix: str
    domain: str


@dataclass(frozen=True)
class RegistrationImapConfig:
    host: str
    port: int
    username: str
    password: str
    mailbox: str
    fetch_limit: int
    poll_interval_seconds: int
    otp_timeout_seconds: int


@dataclass(frozen=True)
class RegistrationProxyConfig:
    enabled: bool
    scheme: str
    host: str
    username: str
    password: str
    direct_fallback_on_challenge: bool


@dataclass(frozen=True)
class RegistrationOauthConfig:
    issuer: str
    client_id: str
    redirect_uri: str


@dataclass(frozen=True)
class RegistrationConfig:
    email: RegistrationEmailConfig
    imap: RegistrationImapConfig
    proxy: RegistrationProxyConfig
    oauth: RegistrationOauthConfig


@dataclass(frozen=True)
class UploadConfig:
    mode: str
    field_name: str
    filename_pattern: str


@dataclass(frozen=True)
class DebugConfig:
    save_failed_upload_payload: bool
    failed_payload_dir: str


@dataclass(frozen=True)
class Settings:
    app: AppConfig
    monitor: MonitorConfig
    cliproxy: CliproxyConfig
    registration: RegistrationConfig
    upload: UploadConfig
    debug: DebugConfig


def _as_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"配置项 `{key}` 缺失或格式错误")
    return value


def _as_bool(value: Any, field_path: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    raise ValueError(f"配置项 `{field_path}` 必须是布尔值")


def load_settings(path: str | Path | None = None) -> Settings:
    file_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not file_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {file_path}")

    with file_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    if not isinstance(raw, dict):
        raise ValueError("配置文件根节点必须是对象")

    app_raw = _as_dict(raw, "app")
    monitor_raw = _as_dict(raw, "monitor")
    cliproxy_raw = _as_dict(raw, "cliproxy")
    registration_raw = _as_dict(raw, "registration")
    registration_email_raw = _as_dict(registration_raw, "email")
    registration_imap_raw = _as_dict(registration_raw, "imap")
    registration_proxy_raw = _as_dict(registration_raw, "proxy")
    registration_oauth_raw = _as_dict(registration_raw, "oauth")
    upload_raw = _as_dict(raw, "upload")
    debug_raw = _as_dict(raw, "debug")

    return Settings(
        app=AppConfig(
            log_level=str(app_raw.get("log_level", "INFO")),
            once=_as_bool(app_raw.get("once", False), "app.once"),
        ),
        monitor=MonitorConfig(
            target_count=int(monitor_raw.get("target_count", 10)),
            interval_seconds=int(monitor_raw.get("interval_seconds", 1800)),
            max_register_attempts=int(monitor_raw.get("max_register_attempts", 30)),
            weekly_remaining_threshold_percent=float(
                monitor_raw.get("weekly_remaining_threshold_percent", 30)
            ),
        ),
        cliproxy=CliproxyConfig(
            api_base=str(cliproxy_raw.get("api_base", "")).rstrip("/"),
            management_key=str(cliproxy_raw.get("management_key", "")),
            timeout_seconds=int(cliproxy_raw.get("timeout_seconds", 30)),
            verify_tls=_as_bool(cliproxy_raw.get("verify_tls", True), "cliproxy.verify_tls"),
        ),
        registration=RegistrationConfig(
            email=RegistrationEmailConfig(
                prefix=str(registration_email_raw.get("prefix", "auto")),
                domain=str(registration_email_raw.get("domain", "")),
            ),
            imap=RegistrationImapConfig(
                host=str(registration_imap_raw.get("host", "")),
                port=int(registration_imap_raw.get("port", 993)),
                username=str(registration_imap_raw.get("username", "")),
                password=str(registration_imap_raw.get("password", "")),
                mailbox=str(registration_imap_raw.get("mailbox", "INBOX")),
                fetch_limit=int(registration_imap_raw.get("fetch_limit", 30)),
                poll_interval_seconds=int(registration_imap_raw.get("poll_interval_seconds", 2)),
                otp_timeout_seconds=int(registration_imap_raw.get("otp_timeout_seconds", 180)),
            ),
            proxy=RegistrationProxyConfig(
                enabled=_as_bool(registration_proxy_raw.get("enabled", False), "registration.proxy.enabled"),
                scheme=str(registration_proxy_raw.get("scheme", "http")),
                host=str(registration_proxy_raw.get("host", "")),
                username=str(registration_proxy_raw.get("username", "")),
                password=str(registration_proxy_raw.get("password", "")),
                direct_fallback_on_challenge=_as_bool(
                    registration_proxy_raw.get("direct_fallback_on_challenge", False),
                    "registration.proxy.direct_fallback_on_challenge",
                ),
            ),
            oauth=RegistrationOauthConfig(
                issuer=str(registration_oauth_raw.get("issuer", "https://auth.openai.com")),
                client_id=str(registration_oauth_raw.get("client_id", "")),
                redirect_uri=str(
                    registration_oauth_raw.get(
                        "redirect_uri", "http://localhost:1455/auth/callback"
                    )
                ),
            ),
        ),
        upload=UploadConfig(
            mode=str(upload_raw.get("mode", "memory_json")),
            field_name=str(upload_raw.get("field_name", "file")),
            filename_pattern=str(upload_raw.get("filename_pattern", "{email}.json")),
        ),
        debug=DebugConfig(
            save_failed_upload_payload=_as_bool(
                debug_raw.get("save_failed_upload_payload", False),
                "debug.save_failed_upload_payload",
            ),
            failed_payload_dir=str(debug_raw.get("failed_payload_dir", "./debug_failed_payloads")),
        ),
    )
