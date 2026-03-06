from __future__ import annotations

import json
from typing import Any

import requests


AUTH_FILES_PATH = "/v0/management/auth-files"


def extract_auth_files(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []

    direct_files = payload.get("files")
    if isinstance(direct_files, list):
        return [x for x in direct_files if isinstance(x, dict)]

    data = payload.get("data")
    if isinstance(data, dict):
        auth_files = data.get("auth_files")
        if isinstance(auth_files, list):
            return [x for x in auth_files if isinstance(x, dict)]
        nested_files = data.get("files")
        if isinstance(nested_files, list):
            return [x for x in nested_files if isinstance(x, dict)]
    return []


class CliproxyApiClient:
    def __init__(
        self,
        api_base: str,
        management_key: str,
        *,
        timeout: int,
        verify_tls: bool,
        upload_field_name: str = "file",
        session: requests.Session | None = None,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        self.verify_tls = verify_tls
        self.upload_field_name = upload_field_name.strip() or "file"
        self.session = session or requests.Session()
        self.headers = {"Authorization": f"Bearer {management_key}"}

    def _url(self, path: str) -> str:
        return f"{self.api_base}{path}"

    def list_auth_files(self) -> list[dict[str, Any]]:
        resp = self.session.get(
            self._url(AUTH_FILES_PATH),
            headers=self.headers,
            timeout=self.timeout,
            verify=self.verify_tls,
        )
        resp.raise_for_status()
        return extract_auth_files(resp.json())

    def delete_auth_file(self, entry: dict[str, Any]) -> bool:
        name = str(entry.get("name", "")).strip()
        file_id = str(entry.get("id", "")).strip()

        if name:
            resp = self.session.delete(
                self._url(AUTH_FILES_PATH),
                params={"name": name},
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify_tls,
            )
            if resp.ok:
                return True

        if file_id:
            for kwargs in (
                {"params": {"id": file_id}},
                {"json": {"id": file_id}},
                {"json": {"auth_file_id": file_id}},
            ):
                resp = self.session.delete(
                    self._url(AUTH_FILES_PATH),
                    headers=self.headers,
                    timeout=self.timeout,
                    verify=self.verify_tls,
                    **kwargs,
                )
                if resp.ok:
                    return True
        return False

    def upload_auth_payload(self, payload: dict[str, Any], filename: str) -> None:
        token_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        resp = self.session.post(
            self._url(AUTH_FILES_PATH),
            headers=self.headers,
            files={self.upload_field_name: (filename, token_bytes, "application/json")},
            timeout=self.timeout,
            verify=self.verify_tls,
        )
        if resp.ok:
            return

        raw_headers = dict(self.headers)
        raw_headers["Content-Type"] = "application/json"
        resp = self.session.post(
            self._url(AUTH_FILES_PATH),
            params={"name": filename},
            headers=raw_headers,
            data=token_bytes,
            timeout=self.timeout,
            verify=self.verify_tls,
        )
        if resp.ok:
            return

        raise RuntimeError(f"上传 token 失败: HTTP {resp.status_code}, body={resp.text[:300]}")
