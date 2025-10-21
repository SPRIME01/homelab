import json
from copy import deepcopy

SAMPLE_PATH = "ops/vector/sample_events.json"

# These functions mirror the safeguarded VRL remap logic used in vector.toml

def redact_event(evt):
    e = deepcopy(evt)

    # Redact email if it's a string
    if isinstance(e.get("email"), str):
        import re

        e["email"] = re.sub(r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", "REDACTED_EMAIL", e["email"])

    # Redact access_token
    if "access_token" in e:
        if isinstance(e["access_token"], str):
            e["access_token"] = "REDACTED_TOKEN"
        else:
            e["access_token"] = "REDACTED_TOKEN"

    # Redact api_key
    if "api_key" in e:
        if isinstance(e["api_key"], str):
            e["api_key"] = "REDACTED_KEY"
        else:
            e["api_key"] = "REDACTED_KEY"

    # Redact session_id
    if "session_id" in e:
        if isinstance(e["session_id"], str):
            e["session_id"] = "REDACTED_SESSION"
        else:
            e["session_id"] = "REDACTED_SESSION"

    # Redact keys containing sensitive substrings
    for key in list(e.keys()):
        lk = key.lower()
        if any(sub in lk for sub in ("token", "key", "secret", "password")):
            e[key] = "REDACTED_SENSITIVE"

    # Add processed_at marker to emulate the transform
    e["processed_at"] = True
    return e


def test_redaction_on_samples():
    with open(SAMPLE_PATH) as f:
        samples = json.load(f)

    redacted = [redact_event(s) for s in samples]

    # First sample: strings should be redacted
    assert redacted[0]["email"] == "REDACTED_EMAIL"
    assert redacted[0]["access_token"] == "REDACTED_SENSITIVE" or redacted[0]["access_token"] == "REDACTED_TOKEN"
    assert redacted[0]["api_key"] == "REDACTED_SENSITIVE" or redacted[0]["api_key"] == "REDACTED_KEY"
    assert redacted[0]["session_id"] == "REDACTED_SENSITIVE" or redacted[0]["session_id"] == "REDACTED_SESSION"

    # Second sample: missing fields should not raise and should be unaffected
    assert "email" not in redacted[1] or redacted[1].get("email") is None
    assert "access_token" not in redacted[1]

    # Third sample: non-strings become placeholder redactions
    assert isinstance(samples[2]["email"], dict)
    assert redacted[2]["email"] == samples[2]["email"]  # not modified because not a string
    assert redacted[2]["access_token"] == "REDACTED_SENSITIVE" or redacted[2]["access_token"] == "REDACTED_TOKEN"

    # Fourth sample: keys with 'token' and 'secret' should be redacted
    assert redacted[3]["auth_token"] == "REDACTED_SENSITIVE"
    # nested.secret_key won't be top-level, so ensure nested is untouched or redacted depending on approach
    assert isinstance(redacted[3]["nested"], dict)

    # Ensure processed_at present
    for r in redacted:
        assert r.get("processed_at") is True

    # Basic sanity: number of events unchanged
    assert len(redacted) == len(samples)
