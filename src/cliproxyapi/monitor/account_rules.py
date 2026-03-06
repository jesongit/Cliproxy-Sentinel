from __future__ import annotations

from typing import Any


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y", "on"}:
            return True
        if text in {"0", "false", "no", "n", "off"}:
            return False
    return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().rstrip("%").strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _provider_of(entry: dict[str, Any]) -> str:
    provider = entry.get("type", entry.get("provider", ""))
    return str(provider).strip().lower()


def is_codex_account(entry: dict[str, Any]) -> bool:
    return _provider_of(entry) == "codex"


def is_invalid_codex_account(entry: dict[str, Any], weekly_threshold: float) -> bool:
    if not is_codex_account(entry):
        return False

    if _as_bool(entry.get("expired")) is True:
        return True

    is_valid_raw = entry.get("is_valid")
    if is_valid_raw is not None and _as_bool(is_valid_raw) is False:
        return True

    weekly_remaining_percent = _as_float(entry.get("weekly_remaining_percent"))
    if weekly_remaining_percent is not None and weekly_remaining_percent < weekly_threshold:
        return True

    status = str(entry.get("status", "")).strip().lower()
    if status in {"invalid", "error", "expired", "disabled", "unavailable"}:
        return True

    if _as_bool(entry.get("disabled")) is True:
        return True
    if _as_bool(entry.get("unavailable")) is True:
        return True

    error_text = str(entry.get("error", "") or entry.get("error_message", "")).strip()
    if error_text:
        return True

    status_message = str(entry.get("status_message", "")).strip().lower()
    if any(flag in status_message for flag in ("invalid", "expired", "removed", "disabled")):
        return True

    return False


def plan_replenishment(
    auth_files: list[dict[str, Any]], target_count: int, weekly_threshold: float
) -> tuple[list[dict[str, Any]], int, int]:
    invalid_entries: list[dict[str, Any]] = []
    valid_count = 0

    for entry in auth_files:
        if not is_codex_account(entry):
            continue
        if is_invalid_codex_account(entry, weekly_threshold=weekly_threshold):
            invalid_entries.append(entry)
            continue
        valid_count += 1

    missing_count = max(0, target_count - valid_count)
    return invalid_entries, valid_count, missing_count
