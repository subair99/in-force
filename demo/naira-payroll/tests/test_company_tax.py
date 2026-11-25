"""SYNTHETIC DEMO."""

from payroll.company_tax import capital_gains_tax


def test_gain_on_building():
    assert capital_gains_tax(50_000_000) == 5_000_000.0
