import pytest
import pandas as pd
from backend.service_layer import service
from backend.service_layer import uow
from backend.domain import model
from collections import defaultdict


def test_consolidated_quarterly_periods_structure():
    """Test that get_consolidated_income_statements with form_type='10-Q' returns
    one annual period and 3 quarterly periods for each year (except first/last years)"""

    with uow.UnitOfWork() as uow_instance:
        combined = service.get_consolidated_income_statements('GES', uow_instance, '10-Q')

        sorted_columns = sorted(combined.df.columns, key=lambda x: x.split(':')[0])
        print("\nAll columns sorted by start date:")
        for col in sorted_columns:
            print(f"  {col}")

        year_periods = defaultdict(list)
        for col in sorted_columns:
            start_date = col.split(':')[0]
            end_date = col.split(':')[1]
            year = start_date.split('-')[0]

            start_pd = pd.to_datetime(start_date)
            end_pd = pd.to_datetime(end_date)
            period_length = (end_pd - start_pd).days

            if period_length > 350 and period_length < 380:
                period_type = 'annual'
            elif period_length > 85 and period_length < 95:
                period_type = 'quarterly'
            else:
                period_type = 'other'

            year_periods[year].append({
                'column': col,
                'type': period_type,
                'length_days': period_length
            })

        print("\nPeriods by year:")
        for year in sorted(year_periods.keys()):
            periods = year_periods[year]
            annual_count = sum(1 for p in periods if p['type'] == 'annual')
            quarterly_count = sum(1 for p in periods if p['type'] == 'quarterly')

            print(f"\n{year}:")
            print(f"  Annual periods: {annual_count}")
            print(f"  Quarterly periods: {quarterly_count}")

            for period in periods:
                print(f"    {period['column']} ({period['type']}, {period['length_days']} days)")

        years = sorted(year_periods.keys())
        middle_years = years[1:-1] if len(years) > 2 else []

        print(f"\nTotal years: {len(years)}")
        print(f"First year: {years[0] if years else 'None'}")
        print(f"Last year: {years[-1] if years else 'None'}")
        print(f"Middle years: {middle_years}")

        for year in middle_years:
            periods = year_periods[year]
            annual_count = sum(1 for p in periods if p['type'] == 'annual')
            quarterly_count = sum(1 for p in periods if p['type'] == 'quarterly')

            assert annual_count == 1, f"Year {year} should have exactly 1 annual period, but has {annual_count}"
            assert quarterly_count == 3, f"Year {year} should have exactly 3 quarterly periods, but has {quarterly_count}"

        if years:
            first_year_periods = year_periods[years[0]]
            first_year_annual = sum(1 for p in first_year_periods if p['type'] == 'annual')
            first_year_quarterly = sum(1 for p in first_year_periods if p['type'] == 'quarterly')

            assert first_year_annual <= 1, f"First year {years[0]} should have at most 1 annual period"
            assert first_year_quarterly <= 3, f"First year {years[0]} should have at most 3 quarterly periods"

            last_year_periods = year_periods[years[-1]]
            last_year_annual = sum(1 for p in last_year_periods if p['type'] == 'annual')
            last_year_quarterly = sum(1 for p in last_year_periods if p['type'] == 'quarterly')

            assert last_year_annual <= 1, f"Last year {years[-1]} should have at most 1 annual period"
            assert last_year_quarterly <= 3, f"Last year {years[-1]} should have at most 3 quarterly periods"

        assert combined.ticker == 'GES', "Ticker should be GES"
        assert combined.form_type == '10-Q', "Form type should be 10-Q"
        assert not combined.df.empty, "Combined dataframe should not be empty"


if __name__ == "__main__":
    test_consolidated_quarterly_periods_structure()
