from __future__ import annotations

import argparse
import logging

from cliproxyapi.cliproxy.client import CliproxyApiClient
from cliproxyapi.logging_setup import setup_logging
from cliproxyapi.monitor.scheduler import run_forever, run_once
from cliproxyapi.settings import Settings, load_settings

logger = logging.getLogger(__name__)

def _resolve_startup_mode(args_once: bool, config_once: bool) -> tuple[str, str]:
    if args_once:
        return "once", "cli"
    if config_once:
        return "once", "config"
    return "forever", "default"


def _startup_mode_message(mode: str, source: str, interval_seconds: int) -> str:
    mode_text = "单轮执行" if mode == "once" else "持续监控"
    source_text_map = {
        "cli": "命令行参数 --once",
        "config": "配置项 app.once",
        "default": "默认配置",
    }
    source_text = source_text_map.get(source, source)
    strategy_text_map = {
        "cli": "仅执行一轮监控，强制新增 1 个账号，完成后退出。",
        "config": "仅执行一轮监控，按缺口补齐账号，完成后退出。",
        "default": f"每 {interval_seconds} 秒执行一轮监控，按目标数量自动补齐账号。",
    }
    strategy_text = strategy_text_map.get(source, "按默认流程执行监控任务。")
    return f"启动模式：{mode_text}（来源：{source_text}）。执行策略：{strategy_text}"


def _validate_settings(settings: Settings) -> None:
    errors: list[str] = []

    if not settings.cliproxy.api_base:
        errors.append("`cliproxy.api_base` 不能为空。")
    if not settings.cliproxy.management_key:
        errors.append("`cliproxy.management_key` 不能为空。")
    if not settings.registration.imap.host:
        errors.append("`registration.imap.host` 不能为空。")
    if not settings.registration.imap.username:
        errors.append("`registration.imap.username` 不能为空。")
    if not settings.registration.imap.password:
        errors.append("`registration.imap.password` 不能为空。")
    if settings.registration.imap.fetch_limit < 1:
        errors.append("`registration.imap.fetch_limit` 必须大于等于 1。")
    if settings.registration.imap.poll_interval_seconds < 1:
        errors.append("`registration.imap.poll_interval_seconds` 必须大于等于 1。")
    if settings.registration.imap.otp_timeout_seconds < 1:
        errors.append("`registration.imap.otp_timeout_seconds` 必须大于等于 1。")
    if settings.monitor.target_count < 1:
        errors.append("`monitor.target_count` 必须大于等于 1。")
    if settings.monitor.interval_seconds < 1:
        errors.append("`monitor.interval_seconds` 必须大于等于 1。")
    if settings.monitor.max_register_attempts < 1:
        errors.append("`monitor.max_register_attempts` 必须大于等于 1。")
    if not 0 <= settings.monitor.weekly_remaining_threshold_percent <= 100:
        errors.append("`monitor.weekly_remaining_threshold_percent` 必须在 0 到 100 之间。")

    if errors:
        detail = "\n".join(f"{index}. {message}" for index, message in enumerate(errors, start=1))
        raise SystemExit(f"配置错误，共 {len(errors)} 项：\n{detail}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="监控 CLIProxyAPI 的 codex 账号并自动补齐。")
    parser.add_argument("--once", action="store_true", help="仅执行一轮后退出")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()
    _validate_settings(settings)
    setup_logging(settings.app.log_level)
    mode, source = _resolve_startup_mode(args_once=args.once, config_once=settings.app.once)
    logger.info(
        _startup_mode_message(
            mode=mode,
            source=source,
            interval_seconds=settings.monitor.interval_seconds,
        )
    )

    client = CliproxyApiClient(
        api_base=settings.cliproxy.api_base,
        management_key=settings.cliproxy.management_key,
        timeout=settings.cliproxy.timeout_seconds,
        verify_tls=settings.cliproxy.verify_tls,
        upload_field_name=settings.upload.field_name,
    )

    if mode == "once":
        run_once(client, settings, force_add_one=(source == "cli"))
        return

    run_forever(client, settings)


if __name__ == "__main__":
    main()
