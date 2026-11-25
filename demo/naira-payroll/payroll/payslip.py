"""Monthly payslip figures. SYNTHETIC DEMO CODE."""

from payroll.paye import compute_paye


def build_payslip(employee_id: str, annual_gross: float) -> dict:
    """Figures for one month's payslip. employee_id is a made-up identifier."""
    annual_tax = compute_paye(annual_gross)
    monthly_gross = annual_gross / 12
    monthly_tax = round(annual_tax / 12, 2)
    return {
        "employee": employee_id,
        "gross": round(monthly_gross, 2),
        "paye": monthly_tax,
        "net": round(monthly_gross - monthly_tax, 2),
    }
