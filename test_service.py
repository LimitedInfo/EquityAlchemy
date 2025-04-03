import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import model
import service
from repository import FakeSECFilingRepository

class TestFinancialServices:

    def test_get_combined_income_statements(self):
        # Create a fake/mock repository for testing
        fake_sec_repo = FakeSECFilingRepository()
        fake_llm_repo = MagicMock()

        # Create test data - a DataFrame that simulates consolidated financial data
        test_data = pd.DataFrame({
            '2023-12-31': [100, 50, 50, 5],
            '2024-12-31': [120, 60, 60, 6]
        }, index=['Revenue', 'Cost of Revenue', 'Gross Profit', 'EarningsPerShareBasic'])

        # Patch the get_consolidated_financials function to return our test data
        with patch('service.get_consolidated_financials', return_value=test_data):
            # Call the function we're testing
            result = service.get_combined_income_statements(
                'AAPL',
                fake_sec_repo,
                llm_repository=fake_llm_repo,
                form_type='10-K'
            )

            # These assertions verify the correct behavior
            assert isinstance(result, model.CombinedIncomeStatements)
            assert result.ticker == 'AAPL'
            assert result.form_type == '10-K'
            assert not result.df.empty
            assert 'Revenue' in result.df.index
            assert 'EarningsPerShareBasic' in result.df.index
            assert '2023-12-31' in result.df.columns
            assert '2024-12-31' in result.df.columns
