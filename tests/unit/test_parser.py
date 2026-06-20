"""Tests for the message parser."""

from datetime import UTC, datetime
from pathlib import Path

from tempmail_cli.models import Message
from tempmail_cli.parser import _score_link, parse_message

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _make_message(text: str | None = None, html: str | None = None) -> Message:
    return Message(
        id="1",
        from_address="test@example.com",
        from_name="Test Sender",
        subject="Test Subject",
        received_at=datetime.now(UTC),
        text_body=text,
        html_body=html,
        seen=False,
    )


class TestCodeExtraction:
    def test_code_with_marker_word(self):
        msg = _make_message(text="Your code is 123456 please verify")
        result = parse_message(msg)
        assert "123456" in result.codes
        assert result.best_code == "123456"

    def test_six_digit_otp(self):
        msg = _make_message(text="Enter this OTP: 654321")
        result = parse_message(msg)
        assert "654321" in result.codes

    def test_four_digit_pin(self):
        msg = _make_message(text="Your PIN is 1234")
        result = parse_message(msg)
        assert "1234" in result.codes

    def test_alphanumeric_code(self):
        msg = _make_message(text="Verification: ABC123DEF")
        result = parse_message(msg)
        assert "ABC123DEF" in result.codes

    def test_no_code(self):
        msg = _make_message(text="Hello, no codes here!")
        result = parse_message(msg)
        assert result.codes == []
        assert result.best_code is None

    def test_multiple_codes(self):
        msg = _make_message(text="Code: 111111 also try 222222")
        result = parse_message(msg)
        assert len(result.codes) >= 2

    def test_code_in_html(self):
        html = (FIXTURES_DIR / "sample_email_with_code.html").read_text()
        msg = _make_message(html=html)
        result = parse_message(msg)
        assert "482913" in result.codes

    def test_best_code_is_most_confident(self):
        msg = _make_message(text="Your verification code is 999999 and also 1234")
        result = parse_message(msg)
        assert result.best_code == "999999"


class TestLinkExtraction:
    def test_confirms_link_from_html(self):
        html = '<a href="https://example.com/confirm?token=abc">Confirm</a>'
        msg = _make_message(html=html)
        result = parse_message(msg)
        assert "https://example.com/confirm?token=abc" in result.links

    def test_best_link_is_confirmation(self):
        html = """
        <a href="https://example.com/unsubscribe">Unsubscribe</a>
        <a href="https://example.com/verify?token=xyz">Verify Email</a>
        """
        msg = _make_message(html=html)
        result = parse_message(msg)
        assert result.best_link == "https://example.com/verify?token=xyz"

    def test_no_links(self):
        msg = _make_message(text="No links here")
        result = parse_message(msg)
        assert result.links == []
        assert result.best_link is None

    def test_excluded_links_not_best(self):
        html = """
        <a href="https://example.com/privacy">Privacy</a>
        <a href="https://example.com/confirm">Confirm</a>
        """
        msg = _make_message(html=html)
        result = parse_message(msg)
        assert result.best_link == "https://example.com/confirm"

    def test_activate_link(self):
        html = '<a href="https://example.com/activate?id=123">Activate</a>'
        msg = _make_message(html=html)
        result = parse_message(msg)
        assert result.best_link == "https://example.com/activate?id=123"


class TestScoreLink:
    def test_confirm_keyword(self):
        assert _score_link("https://example.com/confirm", "") > 0

    def test_no_keyword(self):
        assert _score_link("https://example.com/about", "") == 0

    def test_verify_keyword(self):
        assert _score_link("https://example.com/verify", "") > 0
