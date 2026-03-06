from __future__ import annotations

import argparse
from pathlib import Path

from cliproxyapi.cliproxy.client import CliproxyApiClient
from cliproxyapi.logging_setup import setup_logging
from cliproxyapi.monitor.scheduler import run_forever, run_once
from cliproxyapi.settings import Settings, load_settings


def _default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config.yaml"


def _validate_settings(settings: Settings) -> None:
    if not settings.cliproxy.api_base:
        raise SystemExit("配置错误：`cliproxy.api_base` 不能为空。")
    if not settings.cliproxy.management_key:
        raise SystemExit("配置错误：`cliproxy.management_key` 不能为空。")
    if not settings.registration.imap.host:
        raise SystemExit("配置错误：`registration.imap.host` 不能为空。")
    if not settings.registration.imap.username:
        raise SystemExit("配置错误：`registration.imap.username` 不能为空。")
    if not settings.registration.imap.password:
        raise SystemExit("配置错误：`registration.imap.password` 不能为空。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="监控 CLIProxyAPI 的 codex 账号并自动补齐。")
    parser.add_argument("--config", default=str(_default_config_path()), help="YAML 配置文件路径")
    parser.add_argument("--once", action="store_true", help="仅执行一轮后退出")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings(args.config)
    _validate_settings(settings)
    setup_logging(settings.app.log_level)

    client = CliproxyApiClient(
        api_base=settings.cliproxy.api_base,
        management_key=settings.cliproxy.management_key,
        timeout=settings.cliproxy.timeout_seconds,
        verify_tls=settings.cliproxy.verify_tls,
        upload_field_name=settings.upload.field_name,
    )

    if args.once:
        run_once(client, settings, force_add_one=True)
        return

    if settings.app.once:
        run_once(client, settings)
        return

    run_forever(client, settings)


if __name__ == "__main__":
    main()
