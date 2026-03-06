from __future__ import annotations

from email.message import EmailMessage

import logging
from requests.cookies import RequestsCookieJar

from cliproxyapi.registration import internal_registration as ir


class DummyResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        url: str = "",
        json_data: dict | None = None,
        text: str = "",
        headers: dict | None = None,
        history: list | None = None,
    ) -> None:
        self.status_code = status_code
        self.url = url
        self._json_data = json_data or {}
        self.text = text
        self.headers = headers or {}
        self.history = history or []

    def json(self) -> dict:
        return self._json_data


def _build_mail(*, to_addr: str, subject: str) -> EmailMessage:
    msg = EmailMessage()
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["From"] = "noreply@openai.com"
    msg.set_content(subject)
    return msg


class FakeOauthSession:
    def __init__(self) -> None:
        self.cookies = RequestsCookieJar()
        self.proxies: dict[str, str] = {}
        self.get_calls: list[str] = []
        self.post_calls: list[str] = []

    def get(self, url: str, **_kwargs) -> DummyResponse:
        self.get_calls.append(url)
        return DummyResponse(status_code=200, url=url, text="ok")

    def post(self, url: str, **_kwargs) -> DummyResponse:
        self.post_calls.append(url)
        if url.endswith("/api/accounts/authorize/continue"):
            return DummyResponse(
                status_code=200,
                url=url,
                json_data={"page": {"type": "password"}},
            )
        if url.endswith("/api/accounts/password/verify"):
            return DummyResponse(
                status_code=200,
                url=url,
                json_data={
                    "continue_url": "/email-verification",
                    "page": {"type": "email_otp_verification"},
                },
            )
        if url.endswith("/api/accounts/email-otp/validate"):
            return DummyResponse(
                status_code=401,
                url=url,
                text="unauthorized",
            )
        raise AssertionError(f"未预期的 POST 请求: {url}")


def test_poll_verification_code_skips_old_mail_id(monkeypatch) -> None:
    email_addr = "foo@example.com"
    old_mail = _build_mail(to_addr=email_addr, subject="Your ChatGPT code is 111111")
    new_mail = _build_mail(to_addr=email_addr, subject="Your ChatGPT code is 222222")

    monkeypatch.setattr(
        ir,
        "_fetch_recent_imap_messages",
        lambda: [(b"10", old_mail), (b"11", new_mail)],
    )
    monkeypatch.setattr(ir, "_interruptible_sleep", lambda *_args, **_kwargs: None)

    code = ir.poll_verification_code(
        account={"email": email_addr},
        timeout=0.1,
        min_mail_id_exclusive=10,
    )
    assert code == "222222"


def test_perform_oauth_login_send_otp_once_and_use_mail_baseline(monkeypatch) -> None:
    session = FakeOauthSession()

    monkeypatch.setattr(ir, "build_sentinel_token", lambda *_args, **_kwargs: "sentinel-token")
    monkeypatch.setattr(ir, "generate_pkce", lambda: ("verifier", "challenge"))
    monkeypatch.setattr(
        ir,
        "_fetch_recent_imap_messages",
        lambda: [(b"120", _build_mail(to_addr="someone@example.com", subject="noop"))],
    )

    captured: dict[str, int | None] = {}

    def _fake_poll(*args, **kwargs):
        captured["baseline"] = kwargs.get("min_mail_id_exclusive")
        return "654321"

    monkeypatch.setattr(ir, "poll_verification_code", _fake_poll)

    result = ir.perform_oauth_login(
        session=session,
        email="foo@example.com",
        password="P@ssw0rd",
        account_data={"email": "foo@example.com"},
        log=lambda _msg: None,
    )

    assert result is None
    assert captured["baseline"] == 120
    assert len([u for u in session.get_calls if "/api/accounts/email-otp/send" in u]) == 1


def test_follow_and_extract_code_from_html_text() -> None:
    class FakeSession:
        def get(self, _url: str, **_kwargs) -> DummyResponse:
            return DummyResponse(
                status_code=200,
                url="https://auth.openai.com/sign-in-with-chatgpt/codex/consent",
                text='<a href="http://localhost:1455/auth/callback?code=abc123&state=xyz">continue</a>',
            )

    code = ir._follow_and_extract_code(FakeSession(), "https://auth.openai.com/consent")
    assert code == "abc123"


def test_message_matches_target_requires_exact_recipient() -> None:
    msg = EmailMessage()
    msg["To"] = "atest@pid.im"
    assert ir._message_matches_target(msg, "test@pid.im") is False


def test_message_matches_target_accepts_same_email_with_display_name() -> None:
    msg = EmailMessage()
    msg["To"] = "OpenAI Team <Test177281@Pid.Im>"
    assert ir._message_matches_target(msg, "test177281@pid.im") is True


def test_poll_verification_code_logs_target_and_recipients(monkeypatch, caplog) -> None:
    email_addr = "test@pid.im"
    mail = _build_mail(to_addr="OpenAI Team <test@pid.im>", subject="Your ChatGPT code is 123456")

    monkeypatch.setattr(ir, "_fetch_recent_imap_messages", lambda: [(b"12", mail)])
    monkeypatch.setattr(ir, "_interruptible_sleep", lambda *_args, **_kwargs: None)

    caplog.set_level(logging.INFO, logger="cliproxyapi.registration")
    code = ir.poll_verification_code(account={"email": email_addr}, timeout=1)

    assert code == "123456"
    assert "目标邮箱=test@pid.im" in caplog.text
    assert "收件人=test@pid.im" in caplog.text


def test_poll_verification_code_skips_baseline_mail_and_no_log(monkeypatch, caplog) -> None:
    email_addr = "test@pid.im"
    old_mail = _build_mail(to_addr=email_addr, subject="Your ChatGPT code is 654321")

    monkeypatch.setattr(ir, "_fetch_recent_imap_messages", lambda: [(b"10", old_mail)])
    monkeypatch.setattr(ir, "_interruptible_sleep", lambda *_args, **_kwargs: None)

    caplog.set_level(logging.INFO, logger="cliproxyapi.registration")
    code = ir.poll_verification_code(
        account={"email": email_addr},
        timeout=0.05,
        min_mail_id_exclusive=10,
    )

    assert code is None
    assert "邮件ID=10" not in caplog.text


def test_perform_oauth_login_fails_when_send_otp_non_200(monkeypatch) -> None:
    class SendOtpFailSession(FakeOauthSession):
        def get(self, url: str, **_kwargs) -> DummyResponse:
            self.get_calls.append(url)
            if url.endswith("/api/accounts/email-otp/send"):
                return DummyResponse(status_code=500, url=url, text="server error")
            return DummyResponse(status_code=200, url=url, text="ok")

    session = SendOtpFailSession()

    monkeypatch.setattr(ir, "build_sentinel_token", lambda *_args, **_kwargs: "sentinel-token")
    monkeypatch.setattr(ir, "generate_pkce", lambda: ("verifier", "challenge"))
    monkeypatch.setattr(ir, "_fetch_recent_imap_messages", lambda: [])
    monkeypatch.setattr(ir, "poll_verification_code", lambda *_args, **_kwargs: "123456")

    result = ir.perform_oauth_login(
        session=session,
        email="foo@example.com",
        password="P@ssw0rd",
        account_data={"email": "foo@example.com"},
        log=lambda _msg: None,
    )

    assert result is None
