"""Company tax helpers. SYNTHETIC DEMO CODE, written as of 2025."""

CGT_RATE = 0.10


def capital_gains_tax(gain: float) -> float:
    """Tax on a company's chargeable gain, charged separately from income tax."""
    return round(max(0.0, gain) * CGT_RATE, 2)
