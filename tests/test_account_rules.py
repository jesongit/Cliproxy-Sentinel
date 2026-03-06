from cliproxyapi.monitor.account_rules import is_invalid_codex_account, plan_replenishment


def test_is_invalid_codex_account_by_expired_flag() -> None:
    assert is_invalid_codex_account({"type": "codex", "expired": True}, weekly_threshold=30)


def test_is_invalid_codex_account_by_weekly_remaining_percent() -> None:
    account = {"type": "codex", "status": "active", "weekly_remaining_percent": 29}
    assert is_invalid_codex_account(account, weekly_threshold=30)


def test_is_invalid_codex_account_false_for_active() -> None:
    account = {"type": "codex", "status": "active", "expired": False, "weekly_remaining_percent": 30}
    assert not is_invalid_codex_account(account, weekly_threshold=30)


def test_plan_replenishment_filters_codex_and_counts_missing() -> None:
    entries = [
        {"id": "1", "type": "codex", "status": "active", "expired": False},
        {"id": "2", "type": "codex", "expired": True},
        {"id": "3", "type": "claude", "status": "active"},
    ]
    invalid, valid_count, missing = plan_replenishment(entries, target_count=3, weekly_threshold=30)
    assert [x["id"] for x in invalid] == ["2"]
    assert valid_count == 1
    assert missing == 2
