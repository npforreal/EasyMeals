"""Tests for request input limits, body size limits, and forbidden extra parameters (S5, S7)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.constants import PLAN_MAX_DAYS, PLAN_MIN_DAYS
from app.domain.models import QuantityUnit
from app.main import app
from app.schemas import (
    PantryLotInput,
    StatelessGeneratePlanRequest,
)


def test_stateless_generate_plan_period_limits():
    today = date.today()
    # PLAN_MAX_DAYS (7) is allowed
    req_valid = StatelessGeneratePlanRequest(
        start_date=today,
        days=PLAN_MAX_DAYS,
    )
    assert req_valid.days == PLAN_MAX_DAYS

    # PLAN_MIN_DAYS (1) is allowed
    req_min = StatelessGeneratePlanRequest(
        start_date=today,
        days=PLAN_MIN_DAYS,
    )
    assert req_min.days == PLAN_MIN_DAYS

    # Exceeding PLAN_MAX_DAYS is rejected (e.g. 8 days)
    with pytest.raises(ValidationError):
        StatelessGeneratePlanRequest(
            start_date=today,
            days=PLAN_MAX_DAYS + 1,
        )

    # Below PLAN_MIN_DAYS is rejected (e.g. 0 days)
    with pytest.raises(ValidationError):
        StatelessGeneratePlanRequest(
            start_date=today,
            days=PLAN_MIN_DAYS - 1,
        )


def test_schema_forbid_extra_and_quantity_limits():
    ing_id = uuid4()
    lot_id = uuid4()

    # Valid
    lot = PantryLotInput(
        id=lot_id,
        ingredient_id=ing_id,
        purchased_quantity=Decimal("500"),
        remaining_quantity=Decimal("500"),
        unit=QuantityUnit.GRAM,
    )
    assert lot.purchased_quantity == Decimal("500")

    # Extra field rejected (extra='forbid')
    with pytest.raises(ValidationError):
        PantryLotInput(
            id=lot_id,
            ingredient_id=ing_id,
            purchased_quantity=Decimal("500"),
            remaining_quantity=Decimal("500"),
            unit=QuantityUnit.GRAM,
            unexpected_field="hack",  # type: ignore
        )

    # Excessive quantity rejected (DoS protection > 100,000)
    with pytest.raises(ValidationError):
        PantryLotInput(
            id=lot_id,
            ingredient_id=ing_id,
            purchased_quantity=Decimal("1000000"),
            remaining_quantity=Decimal("500"),
            unit=QuantityUnit.GRAM,
        )


def test_pantry_lot_limit_in_request():
    # Maximum 500 lots in pantry
    excessive_lots = [
        PantryLotInput(
            id=uuid4(),
            ingredient_id=uuid4(),
            purchased_quantity=Decimal("100"),
            remaining_quantity=Decimal("100"),
            unit=QuantityUnit.GRAM,
        )
        for _ in range(501)
    ]

    with pytest.raises(ValidationError):
        StatelessGeneratePlanRequest(
            pantry=excessive_lots,
            start_date=date.today(),
            days=7,
        )


def test_payload_body_size_limit_413():
    client = TestClient(app)
    # Generate a massive payload exceeding 256 KB
    huge_padding = "x" * (260 * 1024)
    res = client.post(
        "/api/planner/generate",
        content=huge_padding,
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 413
    assert "vượt quá giới hạn" in res.json()["detail"]


def test_stateless_generate_plan_options_validation():
    client = TestClient(app)
    today = date.today().isoformat()

    # 1. Unknown key in options -> 422 (extra="forbid")
    res_unknown = client.post(
        "/api/planner/generate",
        json={
            "pantry": [],
            "start_date": today,
            "days": 3,
            "options": {"unexpected_key": "malicious"},
        },
    )
    assert res_unknown.status_code == 422

    # 2. Invalid type for allow_leftovers -> 422
    res_invalid_type = client.post(
        "/api/planner/generate",
        json={
            "pantry": [],
            "start_date": today,
            "days": 3,
            "options": {"allow_leftovers": "not_a_boolean"},
        },
    )
    assert res_invalid_type.status_code == 422

    # 3. Valid options -> 200
    res_valid = client.post(
        "/api/planner/generate",
        json={
            "pantry": [],
            "start_date": today,
            "days": 3,
            "options": {"allow_leftovers": False},
        },
    )
    assert res_valid.status_code == 200
