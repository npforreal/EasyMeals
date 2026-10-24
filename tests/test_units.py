from decimal import Decimal

import pytest

from app.domain.models import (
    IncompatibleUnitError,
    QuantityUnit,
    convert_quantity,
)


def test_convert_quantity_same_unit():
    qty = Decimal("500")
    assert convert_quantity(qty, QuantityUnit.GRAM, QuantityUnit.GRAM) == Decimal("500")
    assert convert_quantity(qty, QuantityUnit.PIECE, QuantityUnit.PIECE) == Decimal("500")


def test_convert_mass_units():
    # 500g -> 0.5kg
    assert convert_quantity(Decimal("500"), QuantityUnit.GRAM, QuantityUnit.KILOGRAM) == Decimal(
        "0.5"
    )
    # 2.5kg -> 2500g
    assert convert_quantity(Decimal("2.5"), QuantityUnit.KILOGRAM, QuantityUnit.GRAM) == Decimal(
        "2500"
    )


def test_convert_volume_units():
    # 750ml -> 0.75l
    assert convert_quantity(Decimal("750"), QuantityUnit.MILLILITER, QuantityUnit.LITER) == Decimal(
        "0.75"
    )
    # 1.2l -> 1200ml
    assert convert_quantity(Decimal("1.2"), QuantityUnit.LITER, QuantityUnit.MILLILITER) == Decimal(
        "1200"
    )


def test_incompatible_unit_conversion():
    # Mass to volume
    with pytest.raises(IncompatibleUnitError):
        convert_quantity(Decimal("500"), QuantityUnit.GRAM, QuantityUnit.MILLILITER)

    # Mass to piece
    with pytest.raises(IncompatibleUnitError):
        convert_quantity(Decimal("500"), QuantityUnit.GRAM, QuantityUnit.PIECE)

    # Volume to piece
    with pytest.raises(IncompatibleUnitError):
        convert_quantity(Decimal("1"), QuantityUnit.LITER, QuantityUnit.PIECE)
