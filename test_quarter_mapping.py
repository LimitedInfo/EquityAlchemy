from backend.domain.minimize_maximize_data_from_filings import _extract_quarters_from_filing_date

def test_quarter_mapping():
    test_dates = [
        '2024-04-24',  # April filing
        '2024-07-24',  # July filing
        '2024-10-24',  # October filing
        '2024-12-15',  # December filing
    ]

    print("Quarter Mapping Test:")
    print("=" * 50)

    for date in test_dates:
        quarters = _extract_quarters_from_filing_date(date)
        sorted_quarters = sorted(list(quarters))
        print(f"Filing date {date} covers quarters: {sorted_quarters}")

    print("\nThis shows that:")
    print("- April filings cover the previous year's Q1-Q4")
    print("- July filings cover previous year Q2-Q4 + current year Q1")
    print("- October filings cover previous year Q3-Q4 + current year Q1-Q2")
    print("- December filings cover previous year Q4 + current year Q1-Q3")

if __name__ == "__main__":
    test_quarter_mapping()
