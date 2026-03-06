from unittest.mock import Mock

import pytest

from cliproxyapi.cliproxy.client import CliproxyApiClient


def _resp(ok: bool = True, payload: dict | None = None, status_code: int = 200) -> Mock:
    m = Mock()
    m.ok = ok
    m.status_code = status_code
    m.text = "mock"
    m.json.return_value = payload or {}
    if ok:
        m.raise_for_status.return_value = None
    else:
        m.raise_for_status.side_effect = RuntimeError("http error")
    return m


def test_list_auth_files_supports_nested_shape() -> None:
    session = Mock()
    session.get.return_value = _resp(payload={"data": {"auth_files": [{"name": "a.json"}]}})
    client = CliproxyApiClient(
        api_base="https://api.example.com",
        management_key="secret",
        timeout=30,
        verify_tls=True,
        session=session,
    )

    result = client.list_auth_files()
    assert result == [{"name": "a.json"}]


def test_delete_auth_file_with_name_success() -> None:
    session = Mock()
    session.delete.return_value = _resp(ok=True)
    client = CliproxyApiClient(
        api_base="https://api.example.com",
        management_key="secret",
        timeout=30,
        verify_tls=True,
        session=session,
    )

    assert client.delete_auth_file({"name": "a.json"}) is True


def test_upload_auth_payload_fallback_to_raw_json_when_multipart_failed() -> None:
    session = Mock()
    session.post.side_effect = [_resp(ok=False, status_code=400), _resp(ok=True, status_code=200)]
    client = CliproxyApiClient(
        api_base="https://api.example.com",
        management_key="secret",
        timeout=30,
        verify_tls=True,
        session=session,
    )

    client.upload_auth_payload({"access_token": "x", "email": "a@b.com"}, filename="a.json")
    assert session.post.call_count == 2


def test_upload_auth_payload_raises_when_all_failed() -> None:
    session = Mock()
    session.post.side_effect = [_resp(ok=False, status_code=400), _resp(ok=False, status_code=500)]
    client = CliproxyApiClient(
        api_base="https://api.example.com",
        management_key="secret",
        timeout=30,
        verify_tls=True,
        session=session,
    )

    with pytest.raises(RuntimeError):
        client.upload_auth_payload({"access_token": "x"}, filename="a.json")


def test_upload_auth_payload_uses_configured_field_name() -> None:
    session = Mock()
    session.post.return_value = _resp(ok=True, status_code=200)
    client = CliproxyApiClient(
        api_base="https://api.example.com",
        management_key="secret",
        timeout=30,
        verify_tls=True,
        upload_field_name="authfile",
        session=session,
    )

    client.upload_auth_payload({"access_token": "x", "email": "a@b.com"}, filename="a.json")
    files = session.post.call_args.kwargs["files"]
    assert "authfile" in files
    assert "file" not in files
