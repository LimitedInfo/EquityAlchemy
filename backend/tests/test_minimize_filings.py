import unittest
from datetime import datetime
from backend.domain.model import Company, Filing
from backend.domain.minimize_maximize_data_from_filings import (
    minimize_quarterly_filings_for_maximum_coverage,
    minimize_quarterly_filings_by_year_sampling,
    get_quarterly_coverage_summary,
    _extract_quarters_from_filing_date
)


class TestMinimizeFilings(unittest.TestCase):

    def setUp(self):
        self.test_filings = [
            Filing('123', '10-Q', '2024-04-24', 'acc1', 'doc1.htm'),
            Filing('123', '10-Q', '2024-07-24', 'acc2', 'doc2.htm'),
            Filing('123', '10-Q', '2024-10-24', 'acc3', 'doc3.htm'),
            Filing('123', '10-Q', '2023-04-24', 'acc4', 'doc4.htm'),
            Filing('123', '10-Q', '2023-07-24', 'acc5', 'doc5.htm'),
            Filing('123', '10-Q', '2023-10-23', 'acc6', 'doc6.htm'),
        ]
        self.company = Company('Test Co', 'TEST', '123', self.test_filings)

    def test_extract_quarters_from_filing_date(self):
        quarters_april = _extract_quarters_from_filing_date('2024-04-24')
        expected_april = {'2023-Q4', '2023-Q3', '2023-Q2', '2023-Q1'}
        self.assertEqual(quarters_april, expected_april)

        quarters_july = _extract_quarters_from_filing_date('2024-07-24')
        expected_july = {'2024-Q1', '2023-Q4', '2023-Q3', '2023-Q2'}
        self.assertEqual(quarters_july, expected_july)

        quarters_october = _extract_quarters_from_filing_date('2024-10-24')
        expected_october = {'2024-Q2', '2024-Q1', '2023-Q4', '2023-Q3'}
        self.assertEqual(quarters_october, expected_october)

    def test_minimize_quarterly_filings_empty_company(self):
        empty_company = Company('Empty', 'EMPTY', '000', [])
        result = minimize_quarterly_filings_for_maximum_coverage(empty_company)
        self.assertEqual(result, [])

    def test_minimize_quarterly_filings_no_quarterly_filings(self):
        annual_filing = Filing('123', '10-K', '2024-03-15', 'acc1', 'doc1.htm')
        company_no_quarterly = Company('Test', 'TEST', '123', [annual_filing])
        result = minimize_quarterly_filings_for_maximum_coverage(company_no_quarterly)
        self.assertEqual(result, [])

    def test_minimize_quarterly_filings_basic_functionality(self):
        result = minimize_quarterly_filings_for_maximum_coverage(self.company)

        self.assertGreater(len(result), 0)
        self.assertLessEqual(len(result), len(self.test_filings))

        for filing in result:
            self.assertEqual(filing.form, '10-Q')
            self.assertIn(filing, self.test_filings)

    def test_get_quarterly_coverage_summary(self):
        selected_filings = minimize_quarterly_filings_for_maximum_coverage(self.company)
        summary = get_quarterly_coverage_summary(self.company, selected_filings)

        self.assertIn('total_filings_available', summary)
        self.assertIn('selected_filings_count', summary)
        self.assertIn('coverage_percentage', summary)
        self.assertIn('covered_quarters', summary)

        self.assertEqual(summary['total_filings_available'], len(self.test_filings))
        self.assertEqual(summary['selected_filings_count'], len(selected_filings))
        self.assertGreaterEqual(summary['coverage_percentage'], 0)
        self.assertLessEqual(summary['coverage_percentage'], 100)

    def test_filing_selection_includes_newest(self):
        result = minimize_quarterly_filings_for_maximum_coverage(self.company)

        newest_filing = max(self.test_filings, key=lambda f: f.filing_date)
        self.assertIn(newest_filing, result)

    def test_filing_dates_are_sorted_descending(self):
        result = minimize_quarterly_filings_for_maximum_coverage(self.company)

        if len(result) > 1:
            dates = [filing.filing_date for filing in result]
            sorted_dates = sorted(dates, reverse=True)
            self.assertEqual(dates, sorted_dates)

    def test_year_sampling_basic_functionality(self):
        result = minimize_quarterly_filings_by_year_sampling(self.company, year_interval=2)

        self.assertGreater(len(result), 0)
        self.assertLessEqual(len(result), len(self.test_filings))

        for filing in result:
            self.assertEqual(filing.form, '10-Q')
            self.assertIn(filing, self.test_filings)

    def test_year_sampling_reduces_filings(self):
        complete_result = minimize_quarterly_filings_for_maximum_coverage(self.company)
        sampling_result = minimize_quarterly_filings_by_year_sampling(self.company, year_interval=2)

        self.assertLessEqual(len(sampling_result), len(complete_result))

    def test_year_sampling_different_intervals(self):
        result_2year = minimize_quarterly_filings_by_year_sampling(self.company, year_interval=2)
        result_3year = minimize_quarterly_filings_by_year_sampling(self.company, year_interval=3)

        self.assertLessEqual(len(result_3year), len(result_2year))


if __name__ == '__main__':
    unittest.main()
