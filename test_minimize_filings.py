from backend.domain.model import Company, Filing
from backend.domain.minimize_maximize_data_from_filings import (
    minimize_quarterly_filings_for_maximum_coverage,
    minimize_quarterly_filings_by_year_sampling,
    get_quarterly_coverage_summary
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


def main():
    company = create_test_company()

    print(f"Total quarterly filings available: {len(company.get_filings_by_type('10-Q'))}")
    print("\nAll filing dates:")
    for filing in company.get_filings_by_type('10-Q'):
        print(f"  {filing.filing_date}")

    print("\n" + "="*60)
    print("APPROACH 1: Complete Coverage (Original)")
    print("="*60)

    selected_filings_complete = minimize_quarterly_filings_for_maximum_coverage(company)

    print(f"\nComplete coverage selection - {len(selected_filings_complete)} filings needed:")
    for filing in selected_filings_complete:
        print(f"  {filing.filing_date}")

    summary_complete = get_quarterly_coverage_summary(company, selected_filings_complete)

    print(f"\nComplete Coverage Summary:")
    print(f"  Total filings available: {summary_complete['total_filings_available']}")
    print(f"  Selected filings: {summary_complete['selected_filings_count']}")
    print(f"  Reduction: {summary_complete['total_filings_available'] - summary_complete['selected_filings_count']} fewer filings")
    print(f"  Coverage percentage: {summary_complete['coverage_percentage']:.1f}%")

    print("\n" + "="*60)
    print("APPROACH 2: Year Sampling (Every Other Year)")
    print("="*60)

    selected_filings_sampling = minimize_quarterly_filings_by_year_sampling(company, year_interval=2)

    print(f"\nYear sampling selection - {len(selected_filings_sampling)} filings needed:")
    for filing in selected_filings_sampling:
        print(f"  {filing.filing_date}")

    summary_sampling = get_quarterly_coverage_summary(company, selected_filings_sampling)

    print(f"\nYear Sampling Summary:")
    print(f"  Total filings available: {summary_sampling['total_filings_available']}")
    print(f"  Selected filings: {summary_sampling['selected_filings_count']}")
    print(f"  Reduction: {summary_sampling['total_filings_available'] - summary_sampling['selected_filings_count']} fewer filings")
    print(f"  Coverage percentage: {summary_sampling['coverage_percentage']:.1f}%")
    print(f"  Covered quarters: {summary_sampling['covered_quarters']}")

    print("\n" + "="*60)
    print("APPROACH 3: Year Sampling (Every 3rd Year)")
    print("="*60)

    selected_filings_3year = minimize_quarterly_filings_by_year_sampling(company, year_interval=3)

    print(f"\nEvery 3rd year selection - {len(selected_filings_3year)} filings needed:")
    for filing in selected_filings_3year:
        print(f"  {filing.filing_date}")

    summary_3year = get_quarterly_coverage_summary(company, selected_filings_3year)

    print(f"\nEvery 3rd Year Summary:")
    print(f"  Total filings available: {summary_3year['total_filings_available']}")
    print(f"  Selected filings: {summary_3year['selected_filings_count']}")
    print(f"  Reduction: {summary_3year['total_filings_available'] - summary_3year['selected_filings_count']} fewer filings")
    print(f"  Coverage percentage: {summary_3year['coverage_percentage']:.1f}%")
    print(f"  Covered quarters: {summary_3year['covered_quarters']}")


if __name__ == "__main__":
    main()
