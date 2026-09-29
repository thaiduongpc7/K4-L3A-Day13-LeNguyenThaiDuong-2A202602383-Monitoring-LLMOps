from __future__ import annotations

from app.logging_config import scrub_event


def test_scrub_event_redacts_nested_strings_before_rendering() -> None:
    event = {
        "event": "request_failed",
        "error_detail": "Call student@vinuni.edu.vn",
        "payload": {
            "items": ["090 123 4567", "4111 1111 1111 1111"],
        },
    }

    scrubbed = scrub_event(None, "error", event)

    assert "student@vinuni.edu.vn" not in str(scrubbed)
    assert "090 123 4567" not in str(scrubbed)
    assert "4111 1111 1111 1111" not in str(scrubbed)
    assert scrubbed["payload"]["items"][0] == "[REDACTED_PHONE_VN]"
