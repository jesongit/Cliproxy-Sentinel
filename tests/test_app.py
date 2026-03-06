from pathlib import Path

from cliproxyapi.app import (
    _default_config_path,
    _resolve_startup_mode,
    _startup_mode_message,
)


def test_default_config_path_points_to_root_config_yaml() -> None:
    expected = Path(__file__).resolve().parents[1] / "config.yaml"
    assert _default_config_path() == expected


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
