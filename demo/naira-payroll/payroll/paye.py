"""PAYE for monthly payroll. SYNTHETIC DEMO CODE, written as of 2025."""

# Annual taxable-income bands: (width of band in NGN, rate). Last band is open-ended.
PIT_BANDS_2025 = (
    (300_000, 0.07),
    (300_000, 0.11),
    (500_000, 0.15),
    (500_000, 0.19),
    (1_600_000, 0.21),
    (None, 0.24),
)

# Consolidated relief: a share of gross income plus a fixed floor.
CRA_RATE = 0.20
CRA_FLAT_MIN = 200_000


def consolidated_relief(gross: float) -> float:
    """Relief deducted from annual gross income before the bands apply."""
    return CRA_RATE * gross + max(CRA_FLAT_MIN, 0.01 * gross)


def compute_paye(gross: float) -> float:
    """Annual PAYE on an annual gross income, in NGN."""
    taxable = max(0.0, gross - consolidated_relief(gross))
    tax = 0.0
    for width, rate in PIT_BANDS_2025:
        if width is None or taxable <= width:
            tax += taxable * rate
            break
        tax += width * rate
        taxable -= width
    return round(tax, 2)
