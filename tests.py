import unittest
from unittest.mock import Mock
import re

import pandas as pd
from model import Company
import repository
import model

class TestCompany(unittest.TestCase):
    def test_cik_property_returns_string(self):
        # Arrange
        mock_repository = Mock()
        mock_repository.get_cik_by_ticker.return_value = "0001234567"
        company = Company("Test Company", "TEST", mock_repository)

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
        company = Company("Test Company", "TEST", mock_repository)

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




class TestSECFilingRepository(unittest.TestCase):
    def test_get_cik_by_ticker(self):
        # Arrange
        from repository import SECFilingRepository
        repo = repository.FakeSECFilingRepository()

        # Act
        cik = repo.get_cik_by_ticker("AAPL")

        # Assert
        self.assertEqual(cik, "0000320193")

    def test_get_filing_data_returns_dictionary(self):
        # Arrange
        from repository import SECFilingRepository

        repo = repository.FakeSECFilingRepository()

        aapl = Company("Apple", "AAPL", repo)
        for filing in aapl.filings:
            if filing.form == "10-K":
                test_form = filing

        # Act
        result = repo.get_filing_data(test_form.cik, test_form.accession_number, test_form.primary_document)

        # Assert
        self.assertIsInstance(result, dict)
        self.assertEqual(result["CoverPage"]["DocumentType"], "10-K")

    def test_filing_data_incomestatement_returns_dictionary(self):
        # Arrange
        from repository import SECFilingRepository

        repo = repository.FakeSECFilingRepository()

        aapl = Company("Apple", "AAPL", repo)
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
        from repository import SECFilingRepository
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


if __name__ == "__main__":
    unittest.main()
