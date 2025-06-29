import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import Mock
import re
import pandas as pd
import json

import backend.adapters.repository as repository
import backend.domain.model as model
import backend.service_layer.service as service



class TestService(unittest.TestCase):
    def test_get_dataframe_from_ticker(self):
        # Arrange
        ticker = "AAPL"

        # Act
        df = service.get_dataframe_from_ticker(ticker, repository.FakeSECFilingRepository())

        # Assert
        self.assertIsInstance(df, pd.DataFrame)

        # Check that columns are in date range format like '2021-09-26:2022-09-24'
        date_range_pattern = re.compile(r"\d{4}-\d{2}-\d{2}:\d{4}-\d{2}-\d{2}")
        for col in df.columns:
            self.assertIsInstance(col, str)
            self.assertTrue(date_range_pattern.match(col), f"Column '{col}' does not match date range format YYYY-MM-DD:YYYY-MM-DD")

    def test_get_consolidated_financials(self):
        # Arrange
        ticker = "AAPL"
        sec_repo = repository.FakeSECFilingRepository()
        llm_repo = Mock()

        # Mock the map_dataframes method to return a mapping
        llm_repo.map_dataframes.return_value = {
            'Revenue': 'Revenues',
            'NetIncomeLoss': 'NetIncome'
        }

        # Mock the Company.join_financial_statements method
        original_join_method = model.Company.join_financial_statements

        # Create a test DataFrame that would be the result of joining
        test_result_df = pd.DataFrame({
            '2020-01-01:2020-12-31': [100, 200],
            '2021-01-01:2021-12-31': [110, 210],
            '2022-01-01:2022-12-31': [120, 220]
        }, index=['Revenue', 'NetIncomeLoss'])

        model.Company.join_financial_statements = Mock(return_value=test_result_df)

        try:
            # Act
            result = service.get_consolidated_financials(ticker, sec_repo, llm_repo, form_type='10-K', statement_type='income_statement')

            # Assert
            self.assertIsInstance(result, model.CombinedIncomeStatements)
            self.assertEqual(len(result.df), 2)  # Two metrics in the dataframe
            self.assertEqual(len(result.df.columns), 3)  # Three years of data

            # Check that the correct methods were called
            self.assertTrue(model.Company.join_financial_statements.called)

        finally:
            # Restore the original method
            model.Company.join_financial_statements = original_join_method

    def test_get_combined_income_statements(self):
        # Arrange
        ticker = "AAPL"
        sec_repo = repository.FakeSECFilingRepository()
        llm_repo = Mock()

        # Mock the map_dataframes method to return a mapping
        llm_repo.map_dataframes.return_value = {
            'Revenue': 'Revenues',
            'NetIncomeLoss': 'NetIncome'
        }

        # Mock the get_consolidated_financials function
        original_get_consolidated = service.get_consolidated_financials

        # Create a test DataFrame that would be the result of consolidation
        test_result_df = pd.DataFrame({
            '2020-01-01:2020-12-31': [100, 200],
            '2021-01-01:2021-12-31': [110, 210],
            '2022-01-01:2022-12-31': [120, 220]
        }, index=['Revenue', 'NetIncomeLoss'])

        service.get_consolidated_financials = Mock(return_value=test_result_df)

        try:
            # Act
            result = service.get_combined_income_statements(ticker, sec_repo, llm_repo, form_type='10-K')

            # Assert
            self.assertIsInstance(result, model.CombinedIncomeStatements)
            self.assertEqual(result.ticker, ticker)
            self.assertEqual(result.form_type, '10-K')

            # Check the data is correctly stored
            pd.testing.assert_frame_equal(result.df, test_result_df)

            # Check that metrics can be accessed
            revenue = result.get_metric('Revenue')
            self.assertIsNotNone(revenue)
            self.assertEqual(revenue['2020-01-01:2020-12-31'], 100)
            self.assertEqual(revenue['2021-01-01:2021-12-31'], 110)
            self.assertEqual(revenue['2022-01-01:2022-12-31'], 120)

            # Check that periods can be accessed
            period_data = result.get_period('2020-01-01:2020-12-31')
            self.assertIsNotNone(period_data)
            self.assertEqual(period_data['Revenue'], 100)
            self.assertEqual(period_data['NetIncomeLoss'], 200)

            # Check utility methods
            self.assertEqual(len(result.get_all_periods()), 3)
            self.assertEqual(len(result.get_all_metrics()), 2)

            # Check that get_consolidated_financials was called with right parameters
            service.get_consolidated_financials.assert_called_once_with(
                ticker,
                sec_repo,
                llm_repository=llm_repo,
                form_type='10-K',
                statement_type='income_statement'
            )

        finally:
            # Restore the original method
            service.get_consolidated_financials = original_get_consolidated




class TestCompany(unittest.TestCase):
    def test_cik_property_returns_string(self):
        # Arrange
        mock_repository = Mock()
        mock_repository.get_cik_by_ticker.return_value = "0001234567"
        company = model.Company("Test Company", "TEST", mock_repository)

        # Act
        result = company.cik

        # Assert
        self.assertIsInstance(result, str)

    def test_filings_property_returns_list(self):
        # Arrange
        mock_repository = Mock()
        mock_repository.get_cik_by_ticker.return_value = "0001234567"
        mock_repository.get_filings.return_value = [
            {"form": "10-K", "filingDate": "2023-01-01"},
            {"form": "10-Q", "filingDate": "2023-04-01"}
        ]
        company = model.Company("Test Company", "TEST", mock_repository)

        # Act
        result = company.filings

        # Assert
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["form"], "10-K")
        self.assertEqual(result[1]["form"], "10-Q")
        mock_repository.get_filings.assert_called_once_with("0001234567")

    def test_income_statement_property_returns_dataframe(self):
        aapl = model.Company("Apple", "AAPL", repository.FakeSECFilingRepository())
        def get_annual_filing(aapl):
            for filing in aapl.filings:
                if filing.form == "10-K":
                    return filing

        filing = get_annual_filing(aapl)
        result = filing.income_statement.table

        # Assert
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(len(result) > 0)

    def test_filter_filings(self):
        # Arrange
        mock_repository = Mock()
        mock_repository.get_cik_by_ticker.return_value = "0001234567"

        # Create mock filings with overlapping data years
        filing1 = Mock()
        filing1.form = "10-K"
        filing1.filing_date = "2024-01-15"

        # Setup income statement
        income_statement1 = Mock()
        income_statement1.table = pd.DataFrame({
            '2022-01-01:2022-12-31': [100, 200],
            '2023-01-01:2023-12-31': [110, 210],
            '2024-01-01:2024-12-31': [120, 220]
        }, index=['Revenue', 'NetIncome'])
        filing1.income_statement = income_statement1

        # Setup balance sheet
        balance_sheet1 = Mock()
        balance_sheet1.table = pd.DataFrame({
            '2023-01-01:2023-12-31': [500, 300],
            '2024-01-01:2024-12-31': [550, 330]
        }, index=['Assets', 'Liabilities'])
        filing1.balance_sheet = balance_sheet1

        filing2 = Mock()
        filing2.form = "10-K"
        filing2.filing_date = "2023-01-10"

        # Setup income statement
        income_statement2 = Mock()
        income_statement2.table = pd.DataFrame({
            '2021-01-01:2021-12-31': [90, 190],
            '2022-01-01:2022-12-31': [100, 200],
            '2023-01-01:2023-12-31': [110, 210]
        }, index=['Revenue', 'NetIncome'])
        filing2.income_statement = income_statement2

        # Setup balance sheet
        balance_sheet2 = Mock()
        balance_sheet2.table = pd.DataFrame({
            '2021-01-01:2021-12-31': [400, 250],
            '2022-01-01:2022-12-31': [450, 280],
            '2023-01-01:2023-12-31': [500, 300]
        }, index=['Assets', 'Liabilities'])
        filing2.balance_sheet = balance_sheet2

        filing3 = Mock()
        filing3.form = "10-K"
        filing3.filing_date = "2022-01-20"

        # Setup income statement
        income_statement3 = Mock()
        income_statement3.table = pd.DataFrame({
            '2020-01-01:2020-12-31': [80, 180],
            '2021-01-01:2021-12-31': [90, 190],
            '2022-01-01:2022-12-31': [100, 200]
        }, index=['Revenue', 'NetIncome'])
        filing3.income_statement = income_statement3

        # Setup balance sheet
        balance_sheet3 = Mock()
        balance_sheet3.table = pd.DataFrame({
            '2020-01-01:2020-12-31': [350, 200],
            '2021-01-01:2021-12-31': [400, 250],
            '2022-01-01:2022-12-31': [450, 280]
        }, index=['Assets', 'Liabilities'])
        filing3.balance_sheet = balance_sheet3

        mock_repository.get_filings.return_value = [filing1, filing2, filing3]
        company = model.Company("Test Company", "TEST", mock_repository)

        # Test 1: Default parameter (income_statement)
        result_default = company.filter_filings()

        # Assert for income statement
        self.assertEqual(len(result_default), 2, "Should return exactly 2 filings to cover all years")

        # Check that the returned filings are the ones we expect (oldest and newest)
        filing_dates_default = [f.filing_date for f in result_default]
        self.assertIn("2024-01-15", filing_dates_default, "Should include the newest filing")
        self.assertIn("2022-01-20", filing_dates_default, "Should include the oldest filing")

        # Check that all years of data are covered
        covered_years_default = []
        for filing in result_default:
            for col in filing.income_statement.table.columns:
                year = col.split('-')[0]
                if year not in covered_years_default:
                    covered_years_default.append(year)

        self.assertIn("2020", covered_years_default)
        self.assertIn("2021", covered_years_default)
        self.assertIn("2022", covered_years_default)
        self.assertIn("2023", covered_years_default)
        self.assertIn("2024", covered_years_default)

        # Test 2: Specify balance_sheet parameter
        result_balance = company.filter_filings(statement_type='balance_sheet')

        # Assert for balance sheet
        self.assertEqual(len(result_balance), 2, "Should return exactly 2 filings to cover all balance sheet years")

        # Check that the returned filings are the ones we expect (oldest and newest)
        filing_dates_balance = [f.filing_date for f in result_balance]
        self.assertIn("2024-01-15", filing_dates_balance, "Should include the newest filing")
        self.assertIn("2022-01-20", filing_dates_balance, "Should include the oldest filing")

        # Check that all years of data are covered
        covered_years_balance = []
        for filing in result_balance:
            for col in filing.balance_sheet.table.columns:
                year = col.split('-')[0]
                if year not in covered_years_balance:
                    covered_years_balance.append(year)

        self.assertIn("2020", covered_years_balance)
        self.assertIn("2021", covered_years_balance)
        self.assertIn("2022", covered_years_balance)
        self.assertIn("2023", covered_years_balance)
        self.assertIn("2024", covered_years_balance)

        # Test 3: Filter by form type
        filing4 = Mock()
        filing4.form = "10-Q"
        filing4.filing_date = "2024-02-15"
        income_statement4 = Mock()
        income_statement4.table = pd.DataFrame({
            '2024-01-01:2024-03-31': [30, 60],
        }, index=['Revenue', 'NetIncome'])
        filing4.income_statement = income_statement4

        mock_repository.get_filings.return_value = [filing1, filing2, filing3, filing4]
        company = model.Company("Test Company", "TEST", mock_repository)

        # Test with form_type=10-Q
        result_quarterly = company.filter_filings(form_type="10-Q")
        self.assertEqual(len(result_quarterly), 1, "Should return exactly 1 filing with form 10-Q")
        self.assertEqual(result_quarterly[0].form, "10-Q", "Should only return 10-Q filings")

    def test_join_financial_statements(self):
        # Arrange
        mock_repository = Mock()
        mock_llm_repository = Mock()

        # Setup filings with test dataframes
        filing1 = Mock()
        filing1.form = "10-K"
        filing1.filing_date = "2024-01-15"

        # Setup first income statement
        income_statement1 = Mock()
        income_statement1.table = pd.DataFrame({
            '2023-01-01:2023-12-31': [100, 200],
            '2024-01-01:2024-12-31': [110, 210]
        }, index=['Revenue', 'NetIncomeLoss'])
        filing1.income_statement = income_statement1

        filing2 = Mock()
        filing2.form = "10-K"
        filing2.filing_date = "2023-01-15"

        # Setup second income statement with different index names
        income_statement2 = Mock()
        income_statement2.table = pd.DataFrame({
            '2022-01-01:2022-12-31': [90, 190],
            '2023-01-01:2023-12-31': [100, 200]
        }, index=['Revenues', 'NetIncome'])
        filing2.income_statement = income_statement2

        # Mock repository methods
        mock_repository.get_cik_by_ticker.return_value = "0001234567"
        mock_repository.get_filings.return_value = [filing1, filing2]

        # Mock filter_filings to return our test filings
        company = model.Company("Test Company", "TEST", mock_repository)
        company.filter_filings = Mock(return_value=[filing1, filing2])

        # Mock LLMRepository's map_dataframes method
        mock_llm_repository.map_dataframes.return_value = {
            'Revenue': 'Revenues',
            'NetIncomeLoss': 'NetIncome'
        }

        # Act - Pass financial statement tables instead of filings
        result = company.join_financial_statements([income_statement1.table, income_statement2.table], llm_repository=mock_llm_repository)

        # Assert
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result.columns), 3)  # Should have 3 date columns
        self.assertTrue('2022-01-01:2022-12-31' in result.columns)
        self.assertTrue('2023-01-01:2023-12-31' in result.columns)
        self.assertTrue('2024-01-01:2024-12-31' in result.columns)

        # Check that values were correctly mapped and joined
        self.assertEqual(result.loc['Revenue', '2022-01-01:2022-12-31'], 90)
        self.assertEqual(result.loc['Revenue', '2023-01-01:2023-12-31'], 100)
        self.assertEqual(result.loc['Revenue', '2024-01-01:2024-12-31'], 110)

        # Assert that map_dataframes was called once
        self.assertEqual(mock_llm_repository.map_dataframes.call_count, 1)

        # Extract call args - this avoids pandas DataFrame comparison issues
        call_args = mock_llm_repository.map_dataframes.call_args
        df1_arg, df2_arg = call_args[0]

        # Check that the dataframes passed to map_dataframes are the correct ones
        pd.testing.assert_frame_equal(df1_arg, income_statement1.table)
        pd.testing.assert_frame_equal(df2_arg, income_statement2.table)

    def test_join_financial_statements_with_real_llm(self):
        """Test join_financial_statements with a real LLM repository instead of a mock."""
        # Skip test if environment variables for LLM are not set
        if not os.getenv("GEMINI_API_KEY"):
            self.skipTest("GEMINI_API_KEY environment variable not set")

        # Arrange
        mock_repository = Mock()

        # Setup filings with test dataframes
        filing1 = Mock()
        filing1.form = "10-K"
        filing1.filing_date = "2024-01-15"

        # Setup first income statement
        income_statement1 = Mock()
        income_statement1.table = pd.DataFrame({
            '2023-01-01:2023-12-31': [100, 200],
            '2024-01-01:2024-12-31': [110, 210]
        }, index=['Revenue', 'NetIncomeLoss'])
        filing1.income_statement = income_statement1

        filing2 = Mock()
        filing2.form = "10-K"
        filing2.filing_date = "2023-01-15"

        # Setup second income statement with different index names
        income_statement2 = Mock()
        income_statement2.table = pd.DataFrame({
            '2022-01-01:2022-12-31': [90, 190],
            '2023-01-01:2023-12-31': [100, 200]
        }, index=['Revenues', 'NetIncome'])
        filing2.income_statement = income_statement2

        # Mock repository methods
        mock_repository.get_cik_by_ticker.return_value = "0001234567"
        mock_repository.get_filings.return_value = [filing1, filing2]

        # Create company and mock filter_filings to return our test filings
        company = model.Company("Test Company", "TEST", mock_repository)
        company.filter_filings = Mock(return_value=[filing1, filing2])

        # Create a real LLMRepository
        real_llm_repository = repository.LLMRepository()

        # Act - Pass financial statement tables instead of filings
        result = company.join_financial_statements(
            [income_statement1.table, income_statement2.table],
            llm_repository=real_llm_repository
        )

        # Assert
        self.assertIsInstance(result, pd.DataFrame)
        # Should have 3 date columns
        self.assertEqual(len(result.columns), 3, "Should have 3 date columns")
        self.assertTrue('2022-01-01:2022-12-31' in result.columns)
        self.assertTrue('2023-01-01:2023-12-31' in result.columns)
        self.assertTrue('2024-01-01:2024-12-31' in result.columns)

        # Check that values are present in the result
        # The real LLM might map the fields differently, so we check for existence
        # rather than exact values
        self.assertTrue('Revenue' in result.index or 'Revenues' in result.index,
                       "Revenue metric should be in the result")
        self.assertTrue('NetIncomeLoss' in result.index or 'NetIncome' in result.index,
                       "Net income metric should be in the result")

        # If mapping worked, at least one metric should have values across all columns
        found_complete_row = False
        for idx in result.index:
            if not result.loc[idx].isna().any():
                found_complete_row = True
                break

        self.assertTrue(found_complete_row,
                       "At least one metric should have values across all time periods")




class TestSECFilingRepository(unittest.TestCase):
    def test_get_cik_by_ticker(self):
        # Arrange
        from backend.adapters.repository import SECFilingRepository
        repo = repository.FakeSECFilingRepository()

        # Act
        cik = repo.get_cik_by_ticker("AAPL")

        # Assert
        self.assertEqual(cik, "0000320193")

    def test_get_filing_data_returns_dictionary(self):
        # Arrange
        from backend.adapters.repository import SECFilingRepository

        repo = repository.FakeSECFilingRepository()

        aapl = model.Company("Apple", "AAPL", repo)
        test_form = None
        for filing in aapl.filings:
            if filing.form == "10-K":
                test_form = filing
                break

        self.assertIsNotNone(test_form, "Could not find a 10-K filing")

        # Act
        result, cover_page = repo.get_filing_data(test_form.cik, test_form.accession_number, test_form.primary_document)

        # Assert
        self.assertIsInstance(result, dict)
        print(result)
        self.assertEqual(result["CoverPage"]["DocumentType"], "10-K")

        # Also test the cover page object
        self.assertIsNotNone(cover_page)
        self.assertEqual(cover_page.document_type, "10-K")

    def test_filing_data_incomestatement_returns_dictionary(self):
        # Arrange
        from backend.adapters.repository import SECFilingRepository

        repo = repository.FakeSECFilingRepository()

        aapl = model.Company("Apple", "AAPL", repo)
        test_form = None
        for filing in aapl.filings:
            if filing.form == "10-K":
                test_form = filing
                break

        self.assertIsNotNone(test_form, "Could not find a 10-K filing")

        # Act
        result = test_form.income_statement.df
        # Assert
        self.assertIsNotNone(result, "IncomeStatement not found in filing data")
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(len(result) > 0, "IncomeStatement dataframe is empty")

        # Check for common income statement items
        common_items = ["Revenue", "NetIncomeLoss", "OperatingIncomeLoss"]
        for item in common_items:
            self.assertTrue(any(item.lower() in metric.lower() for metric in result['metric']),
                           f"Could not find {item} or similar item in income statement")

    def test_income_statement_pivot(self):
        # Arrange
        from backend.adapters.repository import SECFilingRepository
        # model is already imported globally

        repo = repository.FakeSECFilingRepository()
        aapl = model.Company("Apple", "AAPL", repo) # Use model.Company
        test_form = None
        for filing in aapl.filings:
            if filing.form == "10-K":
                test_form = filing
                break

        self.assertIsNotNone(test_form, "Could not find a 10-K filing for pivot test")
        income_statement = test_form.income_statement
        self.assertIsNotNone(income_statement, "IncomeStatement not found in filing data for pivot test")


        # Act
        # Assuming income_statement has a property like .pivoted_table
        try:
            # If the actual property/method name is different, update this line
            pivoted_df = income_statement.table
        except AttributeError:
            self.fail("IncomeStatement object does not have a 'pivoted_table' attribute/method")

        # Assert
        self.assertIsInstance(pivoted_df, pd.DataFrame)
        self.assertTrue(len(pivoted_df) > 0, "Pivoted dataframe is empty")
        self.assertTrue(len(pivoted_df.columns) > 0, "Pivoted dataframe has no columns")

        # Check index contains common items (adapt names if necessary)
        common_items = ["Revenue", "NetIncomeLoss", "OperatingIncomeLoss"]
        for item in common_items:
            self.assertTrue(any(item.lower() in idx.lower() for idx in pivoted_df.index),
                           f"Could not find {item} or similar item in pivoted index")

        # Check column format (e.g., "YYYY-MM-DD:YYYY-MM-DD")
        date_range_pattern = re.compile(r"\d{4}-\d{2}-\d{2}:\d{4}-\d{2}-\d{2}")
        for col in pivoted_df.columns:
            self.assertIsInstance(col, str)
            self.assertTrue(date_range_pattern.match(col), f"Column '{col}' does not match date range format YYYY-MM-DD:YYYY-MM-DD")

        # Check data types (should be numeric, allowing for NaNs)
        for dtype in pivoted_df.dtypes:
            self.assertTrue(pd.api.types.is_numeric_dtype(dtype), f"Column dtype {dtype} is not numeric")




class TestLLMRepository(unittest.TestCase):
    def test_map_dataframes(self):
        # Arrange
        from unittest.mock import MagicMock, patch
        import pandas as pd

        # Create two test dataframes with similar but differently named indices
        df1 = pd.DataFrame({
            'value': [100, 200, 300, 400, 500]
        }, index=['Revenue', 'NetIncomeLoss', 'OperatingIncomeLoss',
                  'WeightedAverageNumberOfSharesOutstanding', 'EarningsPerShareBasic'])

        df2 = pd.DataFrame({
            'value': [110, 210, 310, 410, 510]
        }, index=['Revenues', 'NetIncome', 'OperatingIncome',
                  'WeightedAverageShares', 'BasicEPS'])

        # Create expected mapping result
        expected_mapping = {
            'Revenue': 'Revenues',
            'NetIncomeLoss': 'NetIncome',
            'OperatingIncomeLoss': 'OperatingIncome',
            'WeightedAverageNumberOfSharesOutstanding': 'WeightedAverageShares',
            'EarningsPerShareBasic': 'BasicEPS'
        }

        # Create a proper mock response with a text property that returns a string
        mock_response = MagicMock()
        # Set the text property as a string property, not a MagicMock object
        mock_response.text = json.dumps(expected_mapping)

        # Mock the LLM client
        mock_client = MagicMock()
        # Configure the mock to return our mock_response when generate_content is called
        mock_client.generate_content.return_value = mock_response

        # Create repository with mock client
        repo = repository.LLMRepository()
        repo.gemini_client = mock_client

        # Act
        result = repo.map_dataframes(df1, df2, client=mock_client)

        # Assert
        self.assertEqual(result, expected_mapping)
        # Simply verify the method was called once without checking specific arguments
        mock_client.generate_content.assert_called_once()

    def test_make_index_readable(self):
        # Arrange
        from unittest.mock import MagicMock

        # Create test index names
        index_names = ['NetIncomeLoss', 'OperatingIncomeLoss', 'WeightedAverageNumberOfSharesOutstanding',
                      'EarningsPerShareBasic', 'Revenue']

        # Create expected mapping result
        expected_mapping = {
            'NetIncomeLoss': 'Net Income',
            'OperatingIncomeLoss': 'Operating Income',
            'WeightedAverageNumberOfSharesOutstanding': 'Average Shares Outstanding',
            'EarningsPerShareBasic': 'EPS (Basic)',
            'Revenue': 'Revenue'
        }

        # Create a mock response
        mock_response = MagicMock()
        mock_response.text = json.dumps(expected_mapping)

        # Mock the LLM client
        mock_client = MagicMock()
        mock_client.generate_content.return_value = mock_response

        # Create repository with mock client
        repo = repository.LLMRepository()
        repo.gemini_client = mock_client

        # Act
        result = repo.make_index_readable(index_names, client=mock_client)

        # Assert
        self.assertEqual(result, expected_mapping)
        mock_client.generate_content.assert_called_once()

        # Check that all original names are preserved as keys
        for name in index_names:
            self.assertIn(name, result)

        # Check that values are more readable (when they should be changed)
        self.assertEqual(result['NetIncomeLoss'], 'Net Income')
        self.assertEqual(result['Revenue'], 'Revenue') # Should remain unchanged as it's already readable


class TestRegressions(unittest.TestCase):
    def test_get_consolidated_financials_no_attribute_error(self):
        """Test that get_consolidated_financials doesn't raise AttributeError when processing filings."""
        # Skip test if environment variables for LLM are not set
        if not os.getenv("GEMINI_API_KEY"):
            self.skipTest("GEMINI_API_KEY environment variable not set")

        # Arrange
        mock_sec_repository = Mock()
        mock_llm_repository = Mock()

        # Create fake filings that mimic the structure we need
        filing1 = Mock()
        filing1.form = "10-K"

        # Create an income statement object that returns a table when accessed
        income_statement1 = Mock()
        income_statement1.table = pd.DataFrame({
            '2023-01-01:2023-12-31': [100, 200],
        }, index=['Revenue', 'NetIncomeLoss'])

        # Set the income_statement attribute on the filing
        filing1.income_statement = income_statement1

        filing2 = Mock()
        filing2.form = "10-K"

        # Create another income statement for the second filing
        income_statement2 = Mock()
        income_statement2.table = pd.DataFrame({
            '2022-01-01:2022-12-31': [90, 190],
        }, index=['Revenues', 'NetIncome'])

        filing2.income_statement = income_statement2

        # Mock the filter_filings method to return our test filings
        mock_company = Mock()
        mock_company.filter_filings.return_value = [filing1, filing2]

        # Mock Company constructor to return our mock company
        original_company = model.Company
        model.Company = Mock(return_value=mock_company)

        # Set up mock for join_financial_statements to return a valid result
        expected_result = pd.DataFrame({
            '2022-01-01:2022-12-31': [90, 190],
            '2023-01-01:2023-12-31': [100, 200]
        }, index=['Revenue', 'NetIncomeLoss'])
        mock_company.join_financial_statements.return_value = expected_result

        try:
            # Act
            # This should not raise an AttributeError
            result = service.get_consolidated_financials(
                "TEST",
                mock_sec_repository,
                mock_llm_repository,
                form_type='10-K',
                statement_type='income_statement'
            )

            # Assert
            self.assertIsInstance(result, model.CombinedIncomeStatements)
            pd.testing.assert_frame_equal(result.df, expected_result)

            # Check that the correct methods were called with the right parameters
            model.Company.assert_called_once_with("TEST", "TEST", mock_sec_repository)
            mock_company.filter_filings.assert_called_once_with(
                form_type='10-K',
                statement_type='income_statement'
            )

            # Most importantly, check that join_financial_statements was called
            # with a list of DataFrame objects, not Filing objects
            call_args = mock_company.join_financial_statements.call_args
            financial_statements_arg = call_args[0][0]

            self.assertIsInstance(financial_statements_arg, list)
            self.assertEqual(len(financial_statements_arg), 2)

            for df in financial_statements_arg:
                self.assertIsInstance(df, pd.DataFrame)

            # And check that these are the correct dataframes
            pd.testing.assert_frame_equal(financial_statements_arg[0], income_statement1.table)
            pd.testing.assert_frame_equal(financial_statements_arg[1], income_statement2.table)

        finally:
            # Restore the original Company class
            model.Company = original_company


if __name__ == "__main__":
    unittest.main()
