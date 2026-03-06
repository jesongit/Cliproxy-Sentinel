from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

from cliproxyapi.monitor.account_rules import plan_replenishment
from cliproxyapi.registration.registrar import register_one
from cliproxyapi.settings import Settings


logger = logging.getLogger("cliproxyapi.monitor")


def _maybe_save_failed_payload(settings: Settings, payload: dict[str, Any], reason: str) -> None:
    if not settings.debug.save_failed_upload_payload:
        return
    output_dir = Path(settings.debug.failed_payload_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"upload_failed_{int(time.time())}.json"
    file_path = output_dir / file_name
    data = {
        "reason": reason,
        "payload": payload,
    }
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.warning("已保存失败载荷样本：%s", file_path)


def run_once(
    client: Any,
    settings: Settings,
    register_func: Callable[[Any], tuple[dict[str, Any] | None, str]] = register_one,
) -> dict[str, int]:
    auth_files = client.list_auth_files()
    invalid_entries, valid_count, _ = plan_replenishment(
        auth_files,
        target_count=settings.monitor.target_count,
        weekly_threshold=settings.monitor.weekly_remaining_threshold_percent,
    )
    logger.info("当前 codex 账号：有效=%s，无效=%s", valid_count, len(invalid_entries))

    deleted = 0
    for entry in invalid_entries:
        if client.delete_auth_file(entry):
            deleted += 1
            logger.info("已删除无效账号：%s", entry.get("name", entry.get("id", "未知")))
        else:
            logger.warning("删除无效账号失败：%s", entry)

    auth_files = client.list_auth_files()
    _, valid_count, missing_count = plan_replenishment(
        auth_files,
        target_count=settings.monitor.target_count,
        weekly_threshold=settings.monitor.weekly_remaining_threshold_percent,
    )
    logger.info("清理后有效=%s，需补充=%s", valid_count, missing_count)

    attempts = 0
    uploaded = 0
    while missing_count > 0 and attempts < settings.monitor.max_register_attempts:
        attempts += 1
        payload, reason = register_func(settings.registration)
        if not payload:
            logger.warning("注册失败（%s/%s）：%s", attempts, settings.monitor.max_register_attempts, reason)
            continue

        email = str(payload.get("email", "")).strip() or f"unknown-{attempts}"
        filename = settings.upload.filename_pattern.format(email=email)
        try:
            client.upload_auth_payload(payload, filename=filename)
            auth_files = client.list_auth_files()
            _, updated_valid_count, updated_missing_count = plan_replenishment(
                auth_files,
                target_count=settings.monitor.target_count,
                weekly_threshold=settings.monitor.weekly_remaining_threshold_percent,
            )
            if updated_valid_count > valid_count:
                uploaded += updated_valid_count - valid_count
                valid_count = updated_valid_count
                missing_count = updated_missing_count
                logger.info("上传生效：%s，当前有效=%s，剩余缺口=%s", filename, valid_count, missing_count)
            else:
                valid_count = updated_valid_count
                missing_count = updated_missing_count
                logger.warning(
                    "上传完成但未增加有效 codex：%s，当前有效=%s，剩余缺口=%s",
                    filename,
                    valid_count,
                    missing_count,
                )
        except Exception as exc:
            logger.error("上传或回查失败：%s", exc)
            _maybe_save_failed_payload(settings, payload, str(exc))

    if missing_count > 0:
        logger.warning("本轮结束：仍缺少=%s，成功上传=%s，尝试=%s", missing_count, uploaded, attempts)
    else:
        logger.info("本轮结束：已补齐目标数量=%s", settings.monitor.target_count)

    return {
        "deleted": deleted,
        "uploaded": uploaded,
        "attempts": attempts,
        "missing_count": missing_count,
    }


def run_forever(client: Any, settings: Settings) -> None:
    while True:
        try:
            run_once(client, settings)
        except Exception as exc:
            logger.exception("本轮执行异常：%s", exc)
        time.sleep(max(1, settings.monitor.interval_seconds))
