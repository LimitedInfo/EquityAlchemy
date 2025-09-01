from dataclasses import dataclass
from typing import Optional


@dataclass
class ValuationInputs:
    price: Optional[float]
    shares_outstanding: Optional[float]
    cash_and_cash_equivalents: float
    short_term_investments: float
    short_term_debt_and_current_maturities: float
    long_term_debt: float
    lease_liabilities_current: float
    lease_liabilities_noncurrent: float
    preferred_stock: float
    noncontrolling_interest: float


@dataclass
class ValuationResult:
    market_cap: Optional[float]
    enterprise_value: Optional[float]
    total_debt: float
    net_cash: float
    net_debt: float


def _safe_float(value: Optional[float]) -> float:
    return float(value) if value is not None else 0.0


def compute_market_cap(price: Optional[float], shares_outstanding: Optional[float]) -> Optional[float]:
    if price is None or shares_outstanding is None:
        return None
    try:
        return float(price) * float(shares_outstanding)
    except Exception:
        return None


def compute_valuation(inputs: ValuationInputs) -> ValuationResult:
    cash = _safe_float(inputs.cash_and_cash_equivalents)
    sti = _safe_float(inputs.short_term_investments)
    std = _safe_float(inputs.short_term_debt_and_current_maturities)
    ltd = _safe_float(inputs.long_term_debt)
    lsc = _safe_float(inputs.lease_liabilities_current)
    lsn = _safe_float(inputs.lease_liabilities_noncurrent)
    ps = _safe_float(inputs.preferred_stock)
    nci = _safe_float(inputs.noncontrolling_interest)

    total_debt = std + ltd + lsc + lsn
    net_cash = cash + sti
    net_debt = total_debt - net_cash
    market_cap = compute_market_cap(inputs.price, inputs.shares_outstanding)
    enterprise_value = None
    if market_cap is not None:
        enterprise_value = market_cap + net_debt + ps + nci

    return ValuationResult(
        market_cap=market_cap,
        enterprise_value=enterprise_value,
        total_debt=total_debt,
        net_cash=net_cash,
        net_debt=net_debt,
    )


