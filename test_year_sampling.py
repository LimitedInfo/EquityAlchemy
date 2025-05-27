from backend.domain.model import Company, Filing
from backend.domain.minimize_maximize_data_from_filings import (
    minimize_quarterly_filings_by_year_sampling,
    get_quarterly_coverage_summary,
    _extract_quarters_from_filing_date
)


def create_test_company():
    filing_dates = [
        '2025-04-23', '2024-10-24', '2024-07-24', '2024-04-24',
        '2023-10-23', '2023-07-24', '2023-04-24', '2022-10-24',
        '2022-07-25', '2022-04-25', '2021-10-25', '2021-07-27',
        '2021-04-28', '2020-10-26', '2020-07-28', '2020-04-30',
        '2019-10-29', '2019-07-29', '2019-04-29', '2018-11-02',
        '2018-08-06', '2018-05-07', '2017-11-03', '2017-08-04',
        '2017-05-10'
    ]

    filings = []
    for i, date in enumerate(filing_dates):
        filing = Filing(
            cik='123456789',
            form='10-Q',
            filing_date=date,
            accession_number=f'000123456789-{i:02d}-000001',
            primary_document=f'filing_{i}.htm'
        )
        filings.append(filing)

    company = Company(
        name='Test Company',
        ticker='TEST',
        cik='123456789',
        filings=filings
    )

    return company


def show_filing_quarters(filings):
    print("Filing Date -> Quarters Covered:")
    print("-" * 40)
    for filing in sorted(filings, key=lambda f: f.filing_date, reverse=True):
        quarters = _extract_quarters_from_filing_date(filing.filing_date)
        sorted_quarters = sorted(list(quarters))
        print(f"{filing.filing_date} -> {sorted_quarters}")


def main():
    company = create_test_company()

    print("YEAR SAMPLING APPROACH DEMONSTRATION")
    print("=" * 60)
    print(f"Total quarterly filings available: {len(company.get_filings_by_type('10-Q'))}")

    print("\n" + "="*60)
    print("EVERY OTHER YEAR (year_interval=2)")
    print("="*60)

    selected_filings_2year = minimize_quarterly_filings_by_year_sampling(company, year_interval=2)

    print(f"\nSelected {len(selected_filings_2year)} filings:")
    show_filing_quarters(selected_filings_2year)

    summary_2year = get_quarterly_coverage_summary(company, selected_filings_2year)
    print(f"\nCoverage: {summary_2year['coverage_percentage']:.1f}% of all quarters")
    print(f"Reduction: {summary_2year['total_filings_available'] - summary_2year['selected_filings_count']} fewer filings")

    years_covered = set()
    for quarter in summary_2year['covered_quarters']:
        year = quarter.split('-')[0]
        years_covered.add(year)
    print(f"Years with data: {sorted(list(years_covered))}")

    print("\n" + "="*60)
    print("EVERY THIRD YEAR (year_interval=3)")
    print("="*60)

    selected_filings_3year = minimize_quarterly_filings_by_year_sampling(company, year_interval=3)

    print(f"\nSelected {len(selected_filings_3year)} filings:")
    show_filing_quarters(selected_filings_3year)

    summary_3year = get_quarterly_coverage_summary(company, selected_filings_3year)
    print(f"\nCoverage: {summary_3year['coverage_percentage']:.1f}% of all quarters")
    print(f"Reduction: {summary_3year['total_filings_available'] - summary_3year['selected_filings_count']} fewer filings")

    years_covered_3 = set()
    for quarter in summary_3year['covered_quarters']:
        year = quarter.split('-')[0]
        years_covered_3.add(year)
    print(f"Years with data: {sorted(list(years_covered_3))}")


if __name__ == "__main__":
    main()
