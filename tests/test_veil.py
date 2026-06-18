from pii_veil import Veil


def v():
    # Force the regex backend so tests are deterministic and need no model.
    return Veil(use_presidio=False)


def test_backend_is_regex_when_presidio_disabled():
    assert v().backend == "regex"


def test_email_is_masked():
    assert v().scrub_text("contact john@acme.com please") == "contact <EMAIL_ADDRESS> please"


def test_phone_is_masked():
    out = v().scrub_text("call 07911 123456 today")
    assert "<PHONE_NUMBER>" in out
    assert "07911" not in out


def test_ip_is_masked():
    assert "<IP_ADDRESS>" in v().scrub_text("from 192.168.0.42 at noon")


def test_non_string_passes_through():
    assert v().scrub_value(5) == 5
    assert v().scrub_value(None) is None


def test_scrub_rows_masks_strings_keeps_numbers():
    rows = [{"email": "a@b.com", "qty": 5, "note": "ok"}]
    out = v().scrub_rows(rows)
    assert out[0]["email"] == "<EMAIL_ADDRESS>"
    assert out[0]["qty"] == 5
    assert out[0]["note"] == "ok"


def test_scrub_rows_respects_column_allowlist():
    rows = [{"email": "a@b.com", "free_text": "reach me at a@b.com"}]
    out = v().scrub_rows(rows, columns=["free_text"])
    assert out[0]["email"] == "a@b.com"            # not in the column list
    assert out[0]["free_text"] == "reach me at <EMAIL_ADDRESS>"


def test_empty_and_clean_text_unchanged():
    assert v().scrub_text("") == ""
    assert v().scrub_text("just some yield numbers 94.2 percent") == "just some yield numbers 94.2 percent"
