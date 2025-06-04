import pytest
import pandas as pd
from datetime import datetime, timedelta
from backend.service_layer import service
from backend.service_layer import uow
from backend.domain import model
from typing import Dict, List, Tuple


def analyze_data_completeness(combined: model.CombinedFinancialStatements) -> Dict:
    """
    Analyze a CombinedFinancialStatements object for data completeness.

    Returns a dict with:
    - total_cells: Total number of cells in the dataframe
    - nan_count: Number of NaN values
    - nan_percentage: Percentage of NaN values
    - missing_days: Number of days missing in the date range coverage
    - date_gaps: List of date gaps found
    - continuous_coverage: Whether the date range is continuous
    """
    df = combined.df

    total_cells = df.size
    nan_count = df.isna().sum().sum()
    nan_percentage = (nan_count / total_cells * 100) if total_cells > 0 else 0

    periods = []
    for col in df.columns:
        start_str, end_str = col.split(':')
        start_date = pd.to_datetime(start_str)
        end_date = pd.to_datetime(end_str)
        periods.append((start_date, end_date))

    periods.sort(key=lambda x: x[0])

    missing_days = 0
    date_gaps = []

    if len(periods) > 1:
        for i in range(len(periods) - 1):
            current_end = periods[i][1]
            next_start = periods[i + 1][0]
            gap_days = (next_start - current_end).days - 1

            if gap_days > 0:
                missing_days += gap_days
                date_gaps.append({
                    'from': current_end.strftime('%Y-%m-%d'),
                    'to': next_start.strftime('%Y-%m-%d'),
                    'days_missing': gap_days
                })

    continuous_coverage = missing_days == 0

    overall_start = periods[0][0] if periods else None
    overall_end = periods[-1][1] if periods else None

    return {
        'ticker': combined.ticker,
        'form_type': combined.form_type,
        'total_cells': total_cells,
        'nan_count': nan_count,
        'nan_percentage': round(nan_percentage, 2),
        'missing_days': missing_days,
        'date_gaps': date_gaps,
        'continuous_coverage': continuous_coverage,
        'date_range': {
            'start': overall_start.strftime('%Y-%m-%d') if overall_start else None,
            'end': overall_end.strftime('%Y-%m-%d') if overall_end else None
        },
        'total_periods': len(periods),
        'total_metrics': len(df.index)
    }


def test_single_company_data_completeness():
    """Test data completeness for a single company"""
    with uow.UnitOfWork() as uow_instance:
        combined = service.get_consolidated_income_statements('AAPL', uow_instance, '10-K')

        analysis = analyze_data_completeness(combined)

        print(f"\nData Completeness Analysis for {analysis['ticker']} ({analysis['form_type']}):")
        print(f"Date Range: {analysis['date_range']['start']} to {analysis['date_range']['end']}")
        print(f"Total Periods: {analysis['total_periods']}")
        print(f"Total Metrics: {analysis['total_metrics']}")
        print(f"Total Cells: {analysis['total_cells']}")
        print(f"NaN Count: {analysis['nan_count']} ({analysis['nan_percentage']}%)")
        print(f"Missing Days: {analysis['missing_days']}")
        print(f"Continuous Coverage: {analysis['continuous_coverage']}")

        if analysis['date_gaps']:
            print("\nDate Gaps Found:")
            for gap in analysis['date_gaps']:
                print(f"  {gap['from']} to {gap['to']}: {gap['days_missing']} days missing")

        assert analysis['total_cells'] > 0, "Should have data cells"
        assert analysis['nan_percentage'] < 50, "NaN percentage should be less than 50%"


def test_perfect_annual_coverage():
    """Test that consecutive annual periods have 0 missing days"""
    test_data = {
        'Revenues': {
            '2010-01-01:2010-12-31': 1000,
            '2011-01-01:2011-12-31': 1100,
            '2012-01-01:2012-12-31': 1200,
            '2013-01-01:2013-12-31': 1300,
            '2014-01-01:2014-12-31': 1400,
            '2015-01-01:2015-12-31': 1500,
            '2016-01-01:2016-12-31': 1600,
            '2017-01-01:2017-12-31': 1700,
            '2018-01-01:2018-12-31': 1800,
            '2019-01-01:2019-12-31': 1900,
            '2020-01-01:2020-12-31': 2000,
            '2021-01-01:2021-12-31': 2100,
            '2022-01-01:2022-12-31': 2200,
            '2023-01-01:2023-12-31': 2300,
            '2024-01-01:2024-12-31': 2400
        },
        'NetIncome': {
            '2010-01-01:2010-12-31': 100,
            '2011-01-01:2011-12-31': 110,
            '2012-01-01:2012-12-31': 120,
            '2013-01-01:2013-12-31': 130,
            '2014-01-01:2014-12-31': 140,
            '2015-01-01:2015-12-31': 150,
            '2016-01-01:2016-12-31': 160,
            '2017-01-01:2017-12-31': 170,
            '2018-01-01:2018-12-31': 180,
            '2019-01-01:2019-12-31': 190,
            '2020-01-01:2020-12-31': 200,
            '2021-01-01:2021-12-31': 210,
            '2022-01-01:2022-12-31': 220,
            '2023-01-01:2023-12-31': 230,
            '2024-01-01:2024-12-31': 240
        }
    }

    df = pd.DataFrame(test_data)

    combined = model.CombinedFinancialStatements(
        financial_statements=[],
        source_filings=[],
        ticker='TEST',
        form_type='10-K'
    )
    combined.df = df

    analysis = analyze_data_completeness(combined)

    assert analysis['missing_days'] == 0, f"Expected 0 missing days, got {analysis['missing_days']}"
    assert analysis['continuous_coverage'] == True, "Should have continuous coverage"
    assert len(analysis['date_gaps']) == 0, "Should have no date gaps"
    assert analysis['nan_count'] == 0, "Should have no NaN values in test data"


def test_quarterly_coverage_with_gaps():
    """Test quarterly data with intentional gaps"""
    test_data = {
        'Revenues': {
            '2023-01-01:2023-03-31': 1000,
            '2023-04-01:2023-06-30': 1100,
            '2023-10-01:2023-12-31': 1300,
            '2024-01-01:2024-03-31': 1400
        },
        'NetIncome': {
            '2023-01-01:2023-03-31': 100,
            '2023-04-01:2023-06-30': 110,
            '2023-10-01:2023-12-31': 130,
            '2024-01-01:2024-03-31': 140
        }
    }

    df = pd.DataFrame(test_data)

    combined = model.CombinedFinancialStatements(
        financial_statements=[],
        source_filings=[],
        ticker='TEST',
        form_type='10-Q'
    )
    combined.df = df

    analysis = analyze_data_completeness(combined)

    assert analysis['missing_days'] == 92, f"Expected 92 missing days (Q3 2023), got {analysis['missing_days']}"
    assert analysis['continuous_coverage'] == False, "Should not have continuous coverage"
    assert len(analysis['date_gaps']) == 1, "Should have one date gap"
    assert analysis['date_gaps'][0]['days_missing'] == 92, "Gap should be 92 days"


def analyze_multiple_companies(tickers: List[str], form_type: str = '10-K') -> List[Dict]:
    """Analyze data completeness for multiple companies"""
    results = []

    with uow.UnitOfWork() as uow_instance:
        for ticker in tickers:
            try:
                combined = service.get_consolidated_income_statements(ticker, uow_instance, form_type)
                analysis = analyze_data_completeness(combined)
                results.append(analysis)
            except Exception as e:
                print(f"Error analyzing {ticker}: {str(e)}")
                results.append({
                    'ticker': ticker,
                    'error': str(e)
                })

    return results


def test_multiple_companies_completeness():
    """Test data completeness for multiple companies"""
    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']

    results = analyze_multiple_companies(test_tickers, '10-K')

    print("\nMulti-Company Data Completeness Summary:")
    print("-" * 80)

    for result in results:
        if 'error' in result:
            print(f"{result['ticker']}: ERROR - {result['error']}")
        else:
            print(f"{result['ticker']}: "
                  f"NaN: {result['nan_percentage']}%, "
                  f"Missing Days: {result['missing_days']}, "
                  f"Continuous: {result['continuous_coverage']}, "
                  f"Date Range: {result['date_range']['start']} to {result['date_range']['end']}")

    successful_results = [r for r in results if 'error' not in r]
    assert len(successful_results) > 0, "Should have at least one successful analysis"

    for result in successful_results:
        assert result['nan_percentage'] < 80, f"{result['ticker']} has too many NaN values"


def batch_analyze_companies(tickers: List[str], form_type: str = '10-K',
                          output_csv: str = None) -> Dict:
    """
    Analyze data completeness for a large batch of companies.

    Args:
        tickers: List of company tickers to analyze
        form_type: Type of filing to analyze (10-K or 10-Q)
        output_csv: Optional path to save results as CSV

    Returns:
        Dictionary with summary statistics and detailed results
    """
    results = []
    total_companies = len(tickers)
    successful_analyses = 0
    failed_analyses = 0

    print(f"\nStarting batch analysis of {total_companies} companies...")

    with uow.UnitOfWork() as uow_instance:
        for i, ticker in enumerate(tickers):
            if i > 0 and i % 10 == 0:
                print(f"Progress: {i}/{total_companies} companies analyzed...")

            try:
                combined = service.get_consolidated_income_statements(ticker, uow_instance, form_type)
                analysis = analyze_data_completeness(combined)
                results.append(analysis)
                successful_analyses += 1
            except Exception as e:
                results.append({
                    'ticker': ticker,
                    'error': str(e),
                    'nan_percentage': None,
                    'missing_days': None,
                    'continuous_coverage': None
                })
                failed_analyses += 1

    successful_results = [r for r in results if 'error' not in r]

    if successful_results:
        avg_nan_percentage = sum(r['nan_percentage'] for r in successful_results) / len(successful_results)
        avg_missing_days = sum(r['missing_days'] for r in successful_results) / len(successful_results)
        continuous_coverage_pct = sum(1 for r in successful_results if r['continuous_coverage']) / len(successful_results) * 100

        companies_with_gaps = [r for r in successful_results if not r['continuous_coverage']]
        companies_with_high_nan = [r for r in successful_results if r['nan_percentage'] > 20]
    else:
        avg_nan_percentage = 0
        avg_missing_days = 0
        continuous_coverage_pct = 0
        companies_with_gaps = []
        companies_with_high_nan = []

    summary = {
        'total_companies': total_companies,
        'successful_analyses': successful_analyses,
        'failed_analyses': failed_analyses,
        'average_nan_percentage': round(avg_nan_percentage, 2),
        'average_missing_days': round(avg_missing_days, 2),
        'continuous_coverage_percentage': round(continuous_coverage_pct, 2),
        'companies_with_gaps': len(companies_with_gaps),
        'companies_with_high_nan': len(companies_with_high_nan),
        'detailed_results': results
    }

    if output_csv:
        df_results = pd.DataFrame(results)
        df_results.to_csv(output_csv, index=False)
        print(f"\nResults saved to {output_csv}")

    return summary


def generate_completeness_report(summary: Dict) -> str:
    """Generate a detailed text report from batch analysis summary"""
    report = []
    report.append("=" * 80)
    report.append("DATA COMPLETENESS BATCH ANALYSIS REPORT")
    report.append("=" * 80)
    report.append(f"\nTotal Companies Analyzed: {summary['total_companies']}")
    report.append(f"Successful Analyses: {summary['successful_analyses']}")
    report.append(f"Failed Analyses: {summary['failed_analyses']}")
    report.append(f"\nAVERAGE METRICS:")
    report.append(f"- Average NaN Percentage: {summary['average_nan_percentage']}%")
    report.append(f"- Average Missing Days: {summary['average_missing_days']} days")
    report.append(f"- Companies with Continuous Coverage: {summary['continuous_coverage_percentage']}%")
    report.append(f"- Companies with Date Gaps: {summary['companies_with_gaps']}")
    report.append(f"- Companies with >20% NaN: {summary['companies_with_high_nan']}")

    successful_results = [r for r in summary['detailed_results'] if 'error' not in r]

    if successful_results:
        report.append("\nBEST PERFORMING COMPANIES (Lowest NaN %):")
        best_companies = sorted(successful_results, key=lambda x: x['nan_percentage'])[:5]
        for company in best_companies:
            report.append(f"- {company['ticker']}: {company['nan_percentage']}% NaN, "
                        f"{company['missing_days']} missing days")

        report.append("\nWORST PERFORMING COMPANIES (Highest NaN %):")
        worst_companies = sorted(successful_results, key=lambda x: x['nan_percentage'], reverse=True)[:5]
        for company in worst_companies:
            report.append(f"- {company['ticker']}: {company['nan_percentage']}% NaN, "
                        f"{company['missing_days']} missing days")

        report.append("\nCOMPANIES WITH DATE GAPS:")
        gap_companies = [r for r in successful_results if not r['continuous_coverage']][:10]
        for company in gap_companies:
            gap_info = ", ".join([f"{g['days_missing']} days" for g in company['date_gaps']])
            report.append(f"- {company['ticker']}: {gap_info}")

    failed_results = [r for r in summary['detailed_results'] if 'error' in r]
    if failed_results:
        report.append(f"\nFAILED ANALYSES ({len(failed_results)} companies):")
        for result in failed_results[:10]:
            report.append(f"- {result['ticker']}: {result['error']}")

    report.append("\n" + "=" * 80)

    return "\n".join(report)


def test_large_batch_analysis():
    """Test analyzing a large batch of companies"""
    sp500_sample = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'BRK.B', 'NVDA', 'JPM', 'JNJ',
        'V', 'PG', 'UNH', 'HD', 'MA', 'DIS', 'PYPL', 'BAC', 'NFLX', 'ADBE',
        'CRM', 'PFE', 'TMO', 'CSCO', 'PEP', 'ABT', 'ABBV', 'NKE', 'CVX', 'WMT',
        'MRK', 'LLY', 'AVGO', 'MDT', 'UPS', 'T', 'ORCL', 'TXN', 'HON', 'COST',
        'IBM', 'QCOM', 'GE', 'MMM', 'CAT', 'BA', 'GS', 'AMGN', 'SBUX', 'LMT'
    ]

    summary = batch_analyze_companies(sp500_sample[:20], form_type='10-K')

    report = generate_completeness_report(summary)
    print(report)

    assert summary['successful_analyses'] > 0, "Should have at least some successful analyses"
    assert summary['average_nan_percentage'] < 50, "Average NaN percentage should be reasonable"

    with open('data_completeness_report.txt', 'w') as f:
        f.write(report)
    print("\nFull report saved to data_completeness_report.txt")


def test_specific_company_with_known_coverage():
    """Test a specific company with known date coverage pattern"""
    with uow.UnitOfWork() as uow_instance:
        combined = service.get_consolidated_income_statements('AAPL', uow_instance, '10-K')

        analysis = analyze_data_completeness(combined)

        print(f"\nDetailed Analysis for {analysis['ticker']}:")
        print(f"Total cells: {analysis['total_cells']}")
        print(f"NaN count: {analysis['nan_count']}")
        print(f"NaN percentage: {analysis['nan_percentage']}%")
        print(f"Missing days: {analysis['missing_days']}")
        print(f"Continuous coverage: {analysis['continuous_coverage']}")

        if analysis['date_gaps']:
            print("\nDate gaps found:")
            for gap in analysis['date_gaps']:
                print(f"  From {gap['from']} to {gap['to']}: {gap['days_missing']} days")

        print(f"\nDate range: {analysis['date_range']['start']} to {analysis['date_range']['end']}")
        print(f"Number of periods: {analysis['total_periods']}")
        print(f"Number of metrics: {analysis['total_metrics']}")


if __name__ == "__main__":
    test_single_company_data_completeness()
    test_perfect_annual_coverage()
    test_quarterly_coverage_with_gaps()
    test_multiple_companies_completeness()
    test_large_batch_analysis()
    test_specific_company_with_known_coverage()
