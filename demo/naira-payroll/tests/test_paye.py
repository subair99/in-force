"""Tests pinned to the 2025 results. SYNTHETIC DEMO."""

from payroll.paye import compute_paye


def test_below_relief_pays_nothing():
    assert compute_paye(200_000) == 0.0


def test_mid_income():
    # gross 3,000,000: relief 600,000 + 200,000 = 800,000; taxable 2,200,000
    # 300k@7% + 300k@11% + 500k@15% + 500k@19% + 600k@21% = 21k + 33k + 75k + 95k + 126k
    assert compute_paye(3_000_000) == 350_000.0
