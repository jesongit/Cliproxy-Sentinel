from __future__ import annotations

from datetime import datetime, timedelta, timezone
import time
from typing import Any

from cliproxyapi.registration import internal_registration
from cliproxyapi.settings import RegistrationConfig


def _get_registration_module() -> Any:
    return internal_registration


def _apply_registration_config(module: Any, cfg: RegistrationConfig) -> None:
    module.EMAIL_PREFIX = cfg.email.prefix
    module.EMAIL_DOMAIN = cfg.email.domain
    module.CF_EMAIL_DOMAIN = cfg.email.domain

    module.IMAP_HOST = cfg.imap.host
    module.IMAP_PORT = cfg.imap.port
    module.IMAP_USERNAME = cfg.imap.username
    module.IMAP_PASSWORD = cfg.imap.password
    module.IMAP_MAILBOX = cfg.imap.mailbox
    module.IMAP_FETCH_LIMIT = cfg.imap.fetch_limit
    module.IMAP_POLL_INTERVAL_SECONDS = cfg.imap.poll_interval_seconds
    module.OTP_POLL_TIMEOUT_SECONDS = cfg.imap.otp_timeout_seconds

    module.PROXY_ENABLED = cfg.proxy.enabled
    module.PROXY_SCHEME = cfg.proxy.scheme
    module.PROXY_HOST = cfg.proxy.host
    module.PROXY_USERNAME = cfg.proxy.username
    module.PROXY_PASSWORD = cfg.proxy.password
    module.PROXY_DIRECT_FALLBACK_ON_CHALLENGE = cfg.proxy.direct_fallback_on_challenge

    module.OAUTH_ISSUER = cfg.oauth.issuer
    module.OPENAI_AUTH_BASE = cfg.oauth.issuer
    module.OAUTH_CLIENT_ID = cfg.oauth.client_id
    module.OAUTH_REDIRECT_URI = cfg.oauth.redirect_uri


def _generate_email(cfg: RegistrationConfig) -> str:
    return f"{cfg.email.prefix}{int(time.time())}@{cfg.email.domain}"


def _build_memory_token_payload(
    module: Any,
    token_email: str,
    access_token: str,
    refresh_token: str | None = None,
    id_token: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id_token": id_token or "",
        "access_token": access_token,
        "refresh_token": refresh_token or "",
        "account_id": "",
        "last_refresh": datetime.now(tz=timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "email": token_email,
        "type": "codex",
        "expired": "",
    }

    decode_jwt_payload = getattr(module, "decode_jwt_payload", None)
    if not callable(decode_jwt_payload):
        return payload

    try:
        decoded = decode_jwt_payload(access_token)
    except Exception:
        return payload
    if not isinstance(decoded, dict):
        return payload

    auth_info = decoded.get("https://api.openai.com/auth", {})
    if isinstance(auth_info, dict):
        payload["account_id"] = str(auth_info.get("chatgpt_account_id", "") or "")

    exp_timestamp = decoded.get("exp")
    try:
        exp_int = int(exp_timestamp)
    except (TypeError, ValueError):
        exp_int = 0
    if exp_int > 0:
        exp_dt = datetime.fromtimestamp(exp_int, tz=timezone(timedelta(hours=8)))
        payload["expired"] = exp_dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    return payload


def register_one(cfg: RegistrationConfig) -> tuple[dict[str, Any] | None, str]:
    module = _get_registration_module()
    _apply_registration_config(module, cfg)

    email = _generate_email(cfg)
    password = module.generate_random_password()
    proxy_url = module.get_runtime_proxy_url()

    token_payload: dict[str, Any] = {}
    old_save_token_json = getattr(module, "save_token_json", None)

    def _capture_save_token_json(
        token_email: str,
        access_token: str,
        refresh_token: str | None = None,
        id_token: str | None = None,
    ) -> str:
        token_payload.update(
            _build_memory_token_payload(
                module,
                token_email,
                access_token,
                refresh_token,
                id_token,
            )
        )
        return "__memory__"

    module.save_token_json = _capture_save_token_json
    try:
        registrar = module.ProtocolRegistrar(proxy_url=proxy_url)
        success, reason = registrar.register(account_data={"email": email}, password=password)
    finally:
        if old_save_token_json is not None:
            module.save_token_json = old_save_token_json

    if not success:
        return None, reason

    if token_payload.get("access_token"):
        return token_payload, reason

    return None, reason
