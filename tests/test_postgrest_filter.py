"""Tests for PostgREST filter injection sanitation (S6)."""

from app.storage.repository import _sanitize_postgrest_search


def test_sanitize_postgrest_search_strips_filter_operators():
    # Normal search preserved
    assert _sanitize_postgrest_search("thịt bò") == "thịt bò"
    assert _sanitize_postgrest_search("  rau muống  ") == "rau muống"

    # Attempt to inject PostgREST filter operators: , ( ) . : * % \ "
    injected_term = "thit,id.eq.00000000-0000-0000-0000-000000000000"
    sanitized = _sanitize_postgrest_search(injected_term)
    assert "," not in sanitized
    assert "." not in sanitized
    assert sanitized == "thitideq00000000-0000-0000-0000-000000000000"

    # Wildcard and paren stripping
    complex_payload = 'name.ilike.*admin*),(select%20*%20from"users")'
    sanitized2 = _sanitize_postgrest_search(complex_payload)
    for char in [",", "(", ")", ".", ":", "*", "%", "\\", '"']:
        assert char not in sanitized2

    # Empty payload after sanitize
    assert _sanitize_postgrest_search("...,,,***%%%") == ""
