"""Tests for scripts/verify_rls.py (using mocks for local verification)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from scripts.verify_rls import run_verification, verify_table_rls


def test_verify_rls_refuses_service_role_key(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://mock.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-token")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "secret-service-role")

    exit_code = run_verification()
    assert exit_code == 1


def test_verify_rls_requires_env_keys(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    exit_code = run_verification()
    assert exit_code == 1


def test_verify_table_rls_passes_when_write_rejected():
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    # SELECT succeeds
    mock_table.select.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "1"}]
    )
    # INSERT fails (denied by RLS)
    mock_table.insert.return_value.execute.side_effect = PermissionError(
        "new row violates row-level security policy"
    )
    # UPDATE fails or succeeds with 0 rows
    mock_table.update.return_value.eq.return_value.execute.side_effect = PermissionError(
        "permission denied"
    )
    # DELETE fails or succeeds with 0 rows
    mock_table.delete.return_value.eq.return_value.execute.side_effect = PermissionError(
        "permission denied"
    )

    # Should run without error
    verify_table_rls(mock_client, "ingredients")


def test_verify_table_rls_aborts_if_insert_allowed():
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    mock_table.select.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    # INSERT succeeds (RLS misconfigured!)
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "fake"}])

    with pytest.raises(SystemExit):
        verify_table_rls(mock_client, "ingredients")
