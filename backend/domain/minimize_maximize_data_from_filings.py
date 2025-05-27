from datetime import datetime
from typing import List, Set, Tuple
from .model import Company, Filing


def minimize_quarterly_filings_for_maximum_coverage(company: Company) -> List[Filing]:
    quarterly_filings = company.get_filings_by_type('10-Q')

    if not quarterly_filings:
        return []

    sorted_filings = sorted(quarterly_filings, key=lambda f: f.filing_date, reverse=True)

    filing_quarters = {}
    all_quarters = set()

    for filing in sorted_filings:
        quarters = _extract_quarters_from_filing_date(filing.filing_date)
        filing_quarters[filing] = quarters
        all_quarters.update(quarters)

    if not all_quarters:
        return []

    all_years = set()
    for quarter in all_quarters:
        year = quarter.split('-')[0]
        all_years.add(year)

    selected_filings = []
    covered_quarters = set()

    for year in sorted(all_years, reverse=True):
        year_quarters = {q for q in all_quarters if q.startswith(year)}
        uncovered_year_quarters = year_quarters - covered_quarters

        if not uncovered_year_quarters:
            continue

        year_filings = []
        for filing in sorted_filings:
            filing_year_quarters = filing_quarters[filing] & year_quarters
            if filing_year_quarters:
                year_filings.append((filing, filing_year_quarters))

        year_filings.sort(key=lambda x: len(x[1]), reverse=True)

        year_covered = set()
        for filing, filing_year_quarters in year_filings:
            new_quarters = filing_year_quarters - year_covered
            if new_quarters and filing not in selected_filings:
                selected_filings.append(filing)
                year_covered.update(filing_year_quarters)
                covered_quarters.update(filing_year_quarters)

                if year_covered == year_quarters:
                    break

    return sorted(selected_filings, key=lambda f: f.filing_date, reverse=True)


def minimize_quarterly_filings_by_year_sampling(company: Company, year_interval: int = 2) -> List[Filing]:
    quarterly_filings = company.get_filings_by_type('10-Q')

    if not quarterly_filings:
        return []

    sorted_filings = sorted(quarterly_filings, key=lambda f: f.filing_date, reverse=True)

    filing_quarters = {}
    all_quarters = set()

    for filing in sorted_filings:
        quarters = _extract_quarters_from_filing_date(filing.filing_date)
        filing_quarters[filing] = quarters
        all_quarters.update(quarters)

    if not all_quarters:
        return []

    all_years = set()
    for quarter in all_quarters:
        year = int(quarter.split('-')[0])
        all_years.add(year)

    sorted_years = sorted(all_years, reverse=True)
    selected_years = []

    for i, year in enumerate(sorted_years):
        if i == 0 or i % year_interval == 0:
            selected_years.append(str(year))

    selected_filings = []

    for year in selected_years:
        year_quarters = {q for q in all_quarters if q.startswith(year)}

        year_filings = []
        for filing in sorted_filings:
            filing_year_quarters = filing_quarters[filing] & year_quarters
            if filing_year_quarters:
                year_filings.append((filing, filing_year_quarters))

        year_filings.sort(key=lambda x: len(x[1]), reverse=True)

        year_covered = set()
        for filing, filing_year_quarters in year_filings:
            new_quarters = filing_year_quarters - year_covered
            if new_quarters and filing not in selected_filings:
                selected_filings.append(filing)
                year_covered.update(filing_year_quarters)

                if year_covered == year_quarters:
                    break

    return sorted(selected_filings, key=lambda f: f.filing_date, reverse=True)


def _extract_quarters_from_filing_date(filing_date: str) -> Set[str]:
    filing_dt = datetime.strptime(filing_date, '%Y-%m-%d')
    filing_year = filing_dt.year
    filing_month = filing_dt.month

    quarters = set()

    if filing_month <= 5:
        quarters.add(f"{filing_year-1}-Q1")
        quarters.add(f"{filing_year-1}-Q2")
        quarters.add(f"{filing_year-1}-Q3")
        quarters.add(f"{filing_year-1}-Q4")
    elif filing_month <= 8:
        quarters.add(f"{filing_year-1}-Q2")
        quarters.add(f"{filing_year-1}-Q3")
        quarters.add(f"{filing_year-1}-Q4")
        quarters.add(f"{filing_year}-Q1")
    elif filing_month <= 11:
        quarters.add(f"{filing_year-1}-Q3")
        quarters.add(f"{filing_year-1}-Q4")
        quarters.add(f"{filing_year}-Q1")
        quarters.add(f"{filing_year}-Q2")
    else:
        quarters.add(f"{filing_year-1}-Q4")
        quarters.add(f"{filing_year}-Q1")
        quarters.add(f"{filing_year}-Q2")
        quarters.add(f"{filing_year}-Q3")

    return quarters


def get_quarterly_coverage_summary(company: Company, selected_filings: List[Filing] = None) -> dict:
    if selected_filings is None:
        selected_filings = minimize_quarterly_filings_for_maximum_coverage(company)

    all_quarters = set()
    covered_quarters = set()

    for filing in company.get_filings_by_type('10-Q'):
        quarters = _extract_quarters_from_filing_date(filing.filing_date)
        all_quarters.update(quarters)

    for filing in selected_filings:
        quarters = _extract_quarters_from_filing_date(filing.filing_date)
        covered_quarters.update(quarters)

    return {
        'total_filings_available': len(company.get_filings_by_type('10-Q')),
        'selected_filings_count': len(selected_filings),
        'total_quarters_available': len(all_quarters),
        'quarters_covered': len(covered_quarters),
        'coverage_percentage': (len(covered_quarters) / len(all_quarters)) * 100 if all_quarters else 0,
        'selected_filing_dates': [f.filing_date for f in selected_filings],
        'covered_quarters': sorted(list(covered_quarters)),
        'missed_quarters': sorted(list(all_quarters - covered_quarters))
    }
