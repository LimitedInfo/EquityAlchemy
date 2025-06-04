import argparse
import pandas as pd
import sys
import time
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from backend.service_layer import service, uow
from backend.domain import model
from tests.test_data_completeness import analyze_data_completeness, batch_analyze_companies, generate_completeness_report


def load_tickers_from_file(filepath: str) -> list[str]:
    """Load ticker symbols from a text file (one per line) or CSV file"""
    path = Path(filepath)

    if path.suffix == '.csv':
        df = pd.read_csv(filepath)
        if 'ticker' in df.columns:
            return df['ticker'].tolist()
        elif 'symbol' in df.columns:
            return df['symbol'].tolist()
        else:
            return df.iloc[:, 0].tolist()
    else:
        with open(filepath, 'r') as f:
            return [line.strip() for line in f if line.strip()]


def get_sp500_tickers() -> list[str]:
    """Get current S&P 500 tickers (requires internet connection)"""
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        tables = pd.read_html(url)
        sp500_table = tables[0]
        return sp500_table['Symbol'].tolist()
    except Exception as e:
        print(f"Error fetching S&P 500 tickers: {e}")
        return []


def batch_analyze_companies_with_timing(tickers: list[str], form_type: str = '10-K',
                                       output_csv: str = None, timing_csv: str = None) -> dict:
    """
    Analyze data completeness for multiple companies with detailed timing information.

    Args:
        tickers: List of company tickers to analyze
        form_type: Type of filing to analyze (10-K or 10-Q)
        output_csv: Optional path to save completeness results as CSV
        timing_csv: Optional path to save timing results as CSV

    Returns:
        Dictionary with summary statistics, detailed results, and timing information
    """
    results = []
    timing_results = []
    total_companies = len(tickers)
    successful_analyses = 0
    failed_analyses = 0

    print(f"\nStarting batch analysis of {total_companies} companies...")
    overall_start_time = time.time()

    with uow.UnitOfWork() as uow_instance:
        for i, ticker in enumerate(tickers):
            if i > 0 and i % 10 == 0:
                print(f"Progress: {i}/{total_companies} companies analyzed...")

            company_start_time = time.time()
            try:
                combined = service.get_consolidated_income_statements(ticker, uow_instance, form_type)
                company_load_time = time.time() - company_start_time

                analysis_start_time = time.time()
                analysis = analyze_data_completeness(combined)
                analysis_time = time.time() - analysis_start_time

                num_columns = len(combined.df.columns) if hasattr(combined, 'df') and combined.df is not None else 0
                num_rows = len(combined.df.index) if hasattr(combined, 'df') and combined.df is not None else 0

                first_column_period = None
                last_column_period = None
                if num_columns > 0:
                    sorted_columns = sorted(combined.df.columns)
                    first_column_period = sorted_columns[0]
                    last_column_period = sorted_columns[-1]

                avg_time_per_column = company_load_time / num_columns if num_columns > 0 else 0
                avg_time_per_cell = company_load_time / (num_columns * num_rows) if (num_columns * num_rows) > 0 else 0

                timing_info = {
                    'ticker': ticker,
                    'total_time': company_load_time + analysis_time,
                    'data_load_time': company_load_time,
                    'analysis_time': analysis_time,
                    'num_columns': num_columns,
                    'num_rows': num_rows,
                    'avg_time_per_column': avg_time_per_column,
                    'avg_time_per_cell': avg_time_per_cell,
                    'columns_per_second': num_columns / company_load_time if company_load_time > 0 else 0,
                    'cells_per_second': (num_columns * num_rows) / company_load_time if company_load_time > 0 else 0,
                    'first_column_period': first_column_period,
                    'last_column_period': last_column_period
                }

                analysis['first_column_period'] = first_column_period
                analysis['last_column_period'] = last_column_period

                timing_results.append(timing_info)
                results.append(analysis)
                successful_analyses += 1

                print(f"{ticker}: {company_load_time:.2f}s load, {analysis_time:.3f}s analysis, "
                      f"{num_columns} columns ({avg_time_per_column:.3f}s/col)")
                if first_column_period and last_column_period:
                    print(f"  Period range: {first_column_period} to {last_column_period}")

            except Exception as e:
                company_time = time.time() - company_start_time
                timing_info = {
                    'ticker': ticker,
                    'total_time': company_time,
                    'data_load_time': company_time,
                    'analysis_time': 0,
                    'num_columns': 0,
                    'num_rows': 0,
                    'avg_time_per_column': 0,
                    'avg_time_per_cell': 0,
                    'columns_per_second': 0,
                    'cells_per_second': 0,
                    'first_column_period': None,
                    'last_column_period': None,
                    'error': str(e)
                }
                timing_results.append(timing_info)
                results.append({
                    'ticker': ticker,
                    'error': str(e),
                    'nan_percentage': None,
                    'missing_days': None,
                    'continuous_coverage': None,
                    'first_column_period': None,
                    'last_column_period': None
                })
                failed_analyses += 1
                print(f"{ticker}: ERROR after {company_time:.2f}s - {str(e)}")

    overall_time = time.time() - overall_start_time

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
        'detailed_results': results,
        'timing_results': timing_results,
        'overall_time': overall_time
    }

    if output_csv:
        df_results = pd.DataFrame(results)
        df_results.to_csv(output_csv, index=False)
        print(f"\nCompleteness results saved to {output_csv}")

    if timing_csv:
        df_timing = pd.DataFrame(timing_results)
        df_timing.to_csv(timing_csv, index=False)
        print(f"Timing results saved to {timing_csv}")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description='Analyze data completeness for multiple companies'
    )

    parser.add_argument(
        '--tickers',
        nargs='+',
        help='List of ticker symbols to analyze'
    )

    parser.add_argument(
        '--ticker-file',
        help='Path to file containing ticker symbols (one per line or CSV)'
    )

    parser.add_argument(
        '--sp500',
        action='store_true',
        help='Analyze all S&P 500 companies'
    )

    parser.add_argument(
        '--form-type',
        default='10-K',
        choices=['10-K', '10-Q'],
        help='Type of filing to analyze (default: 10-K)'
    )

    parser.add_argument(
        '--output-csv',
        help='Path to save detailed results as CSV'
    )

    parser.add_argument(
        '--output-report',
        help='Path to save text report'
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of companies to analyze'
    )

    parser.add_argument(
        '--timing-csv',
        help='Path to save timing results as CSV'
    )

    args = parser.parse_args()

    tickers = []

    if args.tickers:
        tickers = args.tickers
    elif args.ticker_file:
        tickers = load_tickers_from_file(args.ticker_file)
    elif args.sp500:
        tickers = get_sp500_tickers()
    else:
        print("Error: Must specify --tickers, --ticker-file, or --sp500")
        parser.print_help()
        sys.exit(1)

    if args.limit:
        tickers = tickers[:args.limit]

    print(f"\nAnalyzing {len(tickers)} companies for {args.form_type} filings...")

    summary = batch_analyze_companies_with_timing(
        tickers,
        form_type=args.form_type,
        output_csv=args.output_csv,
        timing_csv=args.timing_csv
    )

    report = generate_completeness_report(summary)

    print("\n" + report)

    if args.output_report:
        with open(args.output_report, 'w') as f:
            f.write(report)
        print(f"\nReport saved to {args.output_report}")

    timing_results = summary['timing_results']
    successful_timing = [t for t in timing_results if 'error' not in t]
    if successful_timing:
        avg_load_time = sum(t['data_load_time'] for t in successful_timing) / len(successful_timing)
        avg_columns = sum(t['num_columns'] for t in successful_timing) / len(successful_timing)
        avg_time_per_col = sum(t['avg_time_per_column'] for t in successful_timing) / len(successful_timing)
        total_columns = sum(t['num_columns'] for t in successful_timing)

        print("\nTIMING STATISTICS:")
        print(f"Total processing time: {summary['overall_time']:.2f}s")
        print(f"Average load time per company: {avg_load_time:.2f}s")
        print(f"Average columns per company: {avg_columns:.1f}")
        print(f"Average time per column: {avg_time_per_col:.3f}s")
        print(f"Total columns processed: {total_columns}")
        print(f"Overall throughput: {total_columns/summary['overall_time']:.1f} columns/second")

    print("\nSUMMARY STATISTICS:")
    print(f"Success rate: {summary['successful_analyses']}/{summary['total_companies']} "
          f"({summary['successful_analyses']/summary['total_companies']*100:.1f}%)")
    print(f"Average NaN %: {summary['average_nan_percentage']}%")
    print(f"Average missing days: {summary['average_missing_days']}")
    print(f"Continuous coverage: {summary['continuous_coverage_percentage']}%")


if __name__ == "__main__":
    main()
