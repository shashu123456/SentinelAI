"""Secret redaction must mask credential values before a spec is stored."""

from app.utils.redaction import REDACTED, is_secret_key, redact_spec, redact_value


def test_is_secret_key_matches_the_runbook_pattern() -> None:
    for key in ("apiKey", "api_key", "token", "secret", "password", "Authorization", "Bearer"):
        assert is_secret_key(key), key
    for key in ("title", "version", "description", "paths", "operationId"):
        assert not is_secret_key(key), key


def test_redact_value_masks_nested_credentials() -> None:
    spec = {
        "info": {"title": "Demo", "version": "1.0"},
        "components": {
            "securitySchemes": {"apiKey": {"type": "apiKey", "name": "X-Key"}},
        },
        "paths": {
            "/login": {
                "post": {
                    "example": {"username": "alice", "password": "hunter2"},
                    "headers": {"Authorization": "Bearer sk-live-abc123"},
                }
            }
        },
    }
    masked = redact_value(spec)

    assert masked["info"]["title"] == "Demo"
    assert masked["paths"]["/login"]["post"]["example"]["password"] == REDACTED
    assert masked["paths"]["/login"]["post"]["example"]["username"] == "alice"
    assert masked["paths"]["/login"]["post"]["headers"]["Authorization"] == REDACTED
    # The value never survives anywhere in the redacted tree.
    assert "sk-live-abc123" not in str(masked)
    assert "hunter2" not in str(masked)


def test_redact_spec_returns_a_count_and_does_not_mutate_input() -> None:
    spec = {"paths": {"/x": {"default": {"apiKey": "sk-live-1", "token": "t-2"}}}}
    masked, count = redact_spec(spec)

    assert count == 2
    assert masked["paths"]["/x"]["default"]["apiKey"] == REDACTED
    # Original untouched: the scan runs on the real spec.
    assert spec["paths"]["/x"]["default"]["apiKey"] == "sk-live-1"


def test_structured_keys_like_partial_are_preserved() -> None:
    spec = {"kind": "code", "partial": True, "files_scanned": 3, "files_eligible": 3}
    masked, count = redact_spec(spec)
    assert count == 0
    assert masked == spec
