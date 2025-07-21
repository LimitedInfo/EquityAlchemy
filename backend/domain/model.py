from dataclasses import dataclass
import pandas as pd
from abc import ABC, abstractmethod
from typing import List, Optional, Protocol
import json
import os
from datetime import datetime, date
from decimal import Decimal

def load_xbrl_mappings():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    mapping_file = os.path.join(current_dir, 'xbrl_mappings.json')
    with open(mapping_file, 'r') as f:
        return json.load(f)


@dataclass(frozen=True)
class FilingType:
    annual_report = '10-K'
    quarterly_report = '10-Q'


@dataclass
class CoverPage:
    document_type: Optional[str] = None
    document_quarterly_report: Optional[bool] = None
    document_period_end_date: Optional[str] = None
    document_transition_report: Optional[bool] = None
    entity_file_number: Optional[str] = None
    entity_incorporation_state_country_code: Optional[str] = None
    entity_tax_identification_number: Optional[str] = None
    entity_address_line1: Optional[str] = None
    entity_address_city: Optional[str] = None
    entity_address_country: Optional[str] = None
    entity_address_postal_code: Optional[str] = None
    city_area_code: Optional[str] = None
    local_phone_number: Optional[str] = None
    security_12b_title: Optional[str] = None
    trading_symbol: Optional[str] = None
    security_exchange_name: Optional[str] = None
    entity_current_reporting_status: Optional[str] = None
    entity_interactive_data_current: Optional[str] = None
    entity_filer_category: Optional[str] = None
    entity_small_business: Optional[bool] = None
    entity_emerging_growth_company: Optional[bool] = None
    entity_shell_company: Optional[bool] = None
    entity_common_stock_shares_outstanding: Optional[int] = None
    entity_registrant_name: Optional[str] = None
    entity_central_index_key: Optional[str] = None
    amendment_flag: Optional[bool] = None
    document_fiscal_year_focus: Optional[str] = None
    document_fiscal_period_focus: Optional[str] = None
    current_fiscal_year_end_date: Optional[str] = None
    entity_common_stock_shares_outstanding: Optional[int] = None


class Filing:
    def __init__(self, cik: str, form: str, filing_date: str, accession_number: str,
                 primary_document: str, is_xbrl: bool, data: dict = None, filing_url: str = None,
                 cover_page: CoverPage = None) -> None:
        self.cik = cik
        self.form = form
        self.filing_date = filing_date
        self.accession_number = accession_number
        self.primary_document = primary_document
        self.is_xbrl = is_xbrl
        self._data = data
        self._filing_url = filing_url
        self._income_statement = None
        self._cover_page = cover_page

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value: dict):
        self._data = value
        if 'StatementsOfIncome' not in self._data and 'StatementsOfComprehensiveIncome' in self._data:
            self._data['StatementsOfIncome'] = self._data['StatementsOfComprehensiveIncome']
        self._income_statement = None

    @property
    def filing_url(self):
        return self._filing_url

    @filing_url.setter
    def filing_url(self, value: str):
        self._filing_url = value

    @property
    def cover_page(self):
        return self._cover_page

    @cover_page.setter
    def cover_page(self, value: CoverPage):
        self._cover_page = value

    @property
    def income_statement(self):
        if self._income_statement is None and self._data is not None:
            combined_data = {}
            xbrl_mappings = load_xbrl_mappings()
            standardized_tags = set()  # Track which tags have been standardized

            # Apply XBRL mappings first to identify standardized metrics
            standardized_metrics = {}

            # Process income statement metrics
            if 'StatementsOfIncome' in self._data:
                income_metrics = ['Revenue', 'COGS', 'IncomeTaxExpenseBenefit', 'OperatingIncomeLoss', 'NetIncomeLossAttributableToNoncontrollingInterest', 'NetIncomeLossAttributableToNonredeemableNoncontrollingInterest']
                standardized_income = self._apply_xbrl_mappings(
                    self._data['StatementsOfIncome'],
                    xbrl_mappings,
                    income_metrics
                )
                standardized_metrics.update(standardized_income)

                # Track which original tags were standardized
                for standard_name in standardized_income:
                    if standard_name in xbrl_mappings:
                        mapping = xbrl_mappings[standard_name]
                        for tag in mapping.get('primary', []) + mapping.get('secondary', []):
                            standardized_tags.add(tag.split(':')[-1])

            # Process cash flow metrics
            if 'StatementsOfCashFlows' in self._data:
                cash_flow_metrics = ['OperatingCashFlow', 'CapitalExpenditures']
                standardized_cash_flow = self._apply_xbrl_mappings(
                    self._data['StatementsOfCashFlows'],
                    xbrl_mappings,
                    cash_flow_metrics
                )
                standardized_metrics.update(standardized_cash_flow)

                # Track which original tags were standardized
                for standard_name in standardized_cash_flow:
                    if standard_name in xbrl_mappings:
                        mapping = xbrl_mappings[standard_name]
                        for tag in mapping.get('primary', []) + mapping.get('secondary', []):
                            standardized_tags.add(tag.split(':')[-1])

            # First add Revenue and COGS if they exist (to ensure they're #1 and #2)
            if 'Revenue' in standardized_metrics:
                combined_data['Revenue'] = standardized_metrics['Revenue']
            if 'COGS' in standardized_metrics:
                combined_data['COGS'] = standardized_metrics['COGS']

            # Now add all non-standardized items
            if 'StatementsOfIncome' in self._data:
                for metric_name, values in self._data['StatementsOfIncome'].items():
                    if metric_name not in standardized_tags:
                        combined_data[metric_name] = values if isinstance(values, list) else [values]

            # Add the remaining standardized metrics (excluding Revenue and COGS which are already added)
            for metric_name, values in standardized_metrics.items():
                if metric_name not in ['Revenue', 'COGS']:
                    combined_data[metric_name] = values

            self._income_statement = IncomeStatement(combined_data, self.form, self._data.get('cov'))
        return self._income_statement

    def _apply_xbrl_mappings(self, statement_data: dict, xbrl_mappings: dict, metrics_to_process: list = None) -> dict:
        """Apply XBRL mappings to standardize metric names."""
        standardized_data = {}

        if metrics_to_process is None:
            metrics_to_process = list(xbrl_mappings.keys())

        # print(f"\n  [MAP] Starting XBRL mapping for statement with keys: {list(statement_data.keys())}")

        for standard_name in metrics_to_process:
            if standard_name not in xbrl_mappings:
                continue

            mapping = xbrl_mappings[standard_name]
            found_values = []

            # print(f"    [MAP] Processing '{standard_name}'...")

            # Collect all matching values from primary tags
            primary_tags = mapping.get('primary', [])
            for tag in primary_tags:
                tag_name = tag.split(':')[-1]
                if tag_name in statement_data:
                    values = statement_data[tag_name]
                    # print(f"      [MAP] Found PRIMARY tag '{tag_name}' for '{standard_name}'")
                    if not isinstance(values, list):
                        values = [values]
                    found_values.extend(values)

            # If no primary tags found, collect from secondary tags
            if not found_values:
                secondary_tags = mapping.get('secondary', [])
                # print(f"      [MAP] No primary tags found for '{standard_name}'. Checking {len(secondary_tags)} secondary tags...")
                for tag in secondary_tags:
                    tag_name = tag.split(':')[-1]
                    if tag_name in statement_data:
                        values = statement_data[tag_name]
                        # print(f"      [MAP] Found SECONDARY tag '{tag_name}' for '{standard_name}'")
                        if not isinstance(values, list):
                            values = [values]
                        found_values.extend(values)

            if found_values:
                standardized_data[standard_name] = found_values
            else:
                print(f"      [MAP] No tags found for '{standard_name}' in this statement.")

        return standardized_data


class Company:
    def __init__(self,
                 name: str,
                 ticker: str,
                 cik: Optional[str] = None,
                 filings: Optional[List[Filing]] = None,
                 shares_outstanding: Optional[int] = None,
                 cusip: Optional[str] = None,
                 exchange: Optional[str] = None,
                 is_delisted: Optional[bool] = None,
                 category: Optional[str] = None,
                 sector: Optional[str] = None,
                 industry: Optional[str] = None,
                 sic: Optional[str] = None,
                 sic_sector: Optional[str] = None,
                 sic_industry: Optional[str] = None,
                 fama_sector: Optional[str] = None,
                 fama_industry: Optional[str] = None,
                 currency: Optional[str] = None,
                 location: Optional[str] = None,
                 sec_api_id: Optional[str] = None) -> None:
        self.name = name
        self.ticker = ticker
        self.cik = cik
        self._filings = filings or []
        self._shares_outstanding = shares_outstanding
        self.cusip = cusip
        self.exchange = exchange
        self.is_delisted = is_delisted
        self.category = category
        self.sector = sector
        self.industry = industry
        self.sic = sic
        self.sic_sector = sic_sector
        self.sic_industry = sic_industry
        self.fama_sector = fama_sector
        self.fama_industry = fama_industry
        self.currency = currency
        self.location = location
        self.sec_api_id = sec_api_id

    @property
    def filings(self):
        return self._filings

    @property
    def shares_outstanding(self) -> Optional[int]:
        if self._shares_outstanding is not None:
            return self._shares_outstanding

        if not self._filings:
            return None

        for filing in self._filings:
            if (filing.cover_page and
                filing.cover_page.entity_common_stock_shares_outstanding is not None):
                return filing.cover_page.entity_common_stock_shares_outstanding

        return None

    @shares_outstanding.setter
    def shares_outstanding(self, value: Optional[int]):
        self._shares_outstanding = value

    @filings.setter
    def filings(self, value: list[Filing]):
        self._filings = value

    def get_filings_by_type(self, filing_type: str | list[str]):
        filings = self._filings

        if isinstance(filing_type, str):
            return [filing for filing in filings if filing.form == filing_type]
        return [filing for filing in filings if filing.form in filing_type]


    def filter_filings(self, form_type: str='10-K', statement_type: str='income_statement') -> list[Filing]:
        """return the minimal list of filings that covers the maximum number of years. """

        filings_to_process = self.get_filings_by_type(form_type)

         # filter out filings that don't have data.
        filings_to_load = [filing for filing in filings_to_process if filing.data]
        sorted_filings = sorted(filings_to_load, key=lambda f: f.filing_date, reverse=True)

        covered_years = set()
        selected_filings = []

        all_available_years = set()
        for filing in sorted_filings:
            statement = getattr(filing, statement_type)
            for col in statement.table.columns:
                year = col.split('-')[0]
                all_available_years.add(year)

        filing_contributions = {}

        for filing in sorted_filings:
            statement = getattr(filing, statement_type)
            filing_years = set()
            for col in statement.table.columns:
                year = col.split('-')[0]
                filing_years.add(year)

            filing_contributions[filing] = filing_years

        if sorted_filings:
            newest_filing = sorted_filings[0]
            selected_filings.append(newest_filing)
            covered_years.update(filing_contributions[newest_filing])

        if len(sorted_filings) > 1:
            oldest_filing = sorted_filings[-1]
            new_years = filing_contributions[oldest_filing] - covered_years
            if new_years:
                selected_filings.append(oldest_filing)
                covered_years.update(filing_contributions[oldest_filing])

        remaining_filings = [f for f in sorted_filings if f not in selected_filings]
        while all_available_years - covered_years and remaining_filings:
            best_filing = None
            max_new_years = 0

            for filing in remaining_filings:
                new_years = len(filing_contributions[filing] - covered_years)
                if new_years > max_new_years:
                    max_new_years = new_years
                    best_filing = filing

            if best_filing and max_new_years > 0:
                selected_filings.append(best_filing)
                covered_years.update(filing_contributions[best_filing])
                remaining_filings.remove(best_filing)
            else:
                break


        return selected_filings

    def get_most_recent_filing(filings_list: list[Filing], form_type: str):
        if form_type == '10-K':
            return filings_list[0]
        elif form_type == '10-Q':
            return filings_list[3]

    def get_skip_amount(last_filing: Filing, form_type: str):
        if last_filing.data and last_filing.income_statement:
            print(f"Years covered in last filing ({last_filing.filing_date}):")
            print(last_filing.income_statement.table.columns)

        year_interval = len(last_filing.income_statement.table.columns)
        return (year_interval - 1) * 3 if form_type == '10-Q' else (year_interval - 1) * 1

    def select_filings_with_processing_pattern(self,filings_list: List[Filing], form_type: str) -> List[Filing]:
        if form_type == '10-K':
            process_count = 1
        elif form_type == '10-Q':
            process_count = 3

        first_filing_with_data = next((filing for filing in filings_list if filing.income_statement and filing.income_statement.table.columns is not None), filings_list[0])
        print(len(first_filing_with_data.income_statement.table.columns))
        if len(first_filing_with_data.income_statement.table.columns) <= 0:
            print('no data found in first filing, skipping...')
            return []

        skip_count = Company.get_skip_amount(first_filing_with_data, form_type)


        if process_count <= 0:
            return []

        selected = []
        idx = 0
        total_filings = len(filings_list)

        while idx < total_filings:
            # Process N filings
            end_process_idx = min(idx + process_count, total_filings)
            selected.extend(filings_list[idx:end_process_idx])
            idx = end_process_idx

            # If we've processed all filings, break
            if idx >= total_filings:
                break

            # Skip M filings
            idx += skip_count

        # Add the last filing if it's not already in the list
        if form_type == '10-K':
            if filings_list[-1] not in selected:
                selected.append(filings_list[-1])
        elif form_type == '10-Q':
            for filing in filings_list[-3:]:
                if filing not in selected:
                    selected.append(filing)

        return selected

class PriceData:
    def __init__(self, ticker: str, start_date: datetime, end_date: datetime) -> None:
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date


class AbstractFinancialStatement(ABC):
    def __init__(self, data: dict, form: str, fiscal_period: str) -> None:
        self.data = data
        self.form = form
        self.fiscal_period = fiscal_period
        self.df = self._process_data()

    @abstractmethod
    def _process_data(self) -> pd.DataFrame:
        pass

    @property
    @abstractmethod
    def table(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_annual_data(self, include_segment_data: bool = False) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_quarterly_data(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_metric(self, metric_name: str) -> pd.DataFrame:
        pass

    def get_all_metrics(self) -> list[str]:
        if self.df.empty:
            return []
        return self.df['metric'].unique().tolist() if 'metric' in self.df.columns else []

    def get_all_periods(self) -> list[str]:
        table = self.table
        if table.empty:
            return []
        return list(table.columns)


class IncomeStatement(AbstractFinancialStatement):
    def __init__(self, data: dict, form: str, fiscal_period: str) -> None:
        AbstractFinancialStatement.__init__(self, data, form, fiscal_period)

    def _process_data(self) -> pd.DataFrame:
        rows = []

        for metric, entries in self.data.items():
                if isinstance(entries, dict):
                    entries = [entries]
                # at some point to implement segment data we can make a change here.
                for entry in entries:
                    if 'segment' in entry or 'value' not in entry or '<div' in entry:
                        continue

                    period_data = entry.get('period', {})
                    start_date = None
                    end_date = None

                    if isinstance(period_data, dict):
                        start_date = period_data.get('startDate')
                        end_date = period_data.get('endDate')
                    elif isinstance(period_data, str):
                        start_date = period_data
                        end_date = period_data

                    segment_info = None
                    segment_dimension = None
                    if 'segment' in entry:
                        if isinstance(entry['segment'], list):
                            continue

                        segment_info = entry['segment'].get('value')
                        segment_dimension = entry['segment'].get('dimension')

                    row = {
                        'metric': metric,
                        'value': float(entry['value']),
                        'start_date': start_date,
                        'end_date': end_date,
                        'unit': entry.get('unitRef'),
                        'decimals': entry.get('decimals'),
                        'segment_value': segment_info,
                        'segment_dimension': segment_dimension
                    }
                    rows.append(row)

        df = pd.DataFrame(rows)

        if not df.empty:
            df['start_date'] = pd.to_datetime(df['start_date'], format='ISO8601')
            df['end_date'] = pd.to_datetime(df['end_date'], format='ISO8601')

        return df

    @property
    def table(self) -> pd.DataFrame:
        if self.form == '10-K':
            pivoted_df = self.get_annual_data()
        elif self.form == '10-Q':
            pivoted_df =  self.get_quarterly_data()
        else:
            return pd.DataFrame()

        if (not pivoted_df.empty and
            len(pivoted_df.columns) > 0 and
            'OperatingCashFlow' in pivoted_df.index and
            'CapitalExpenditures' in pivoted_df.index):
            pivoted_df.loc['FreeCashFlow'] = pivoted_df.loc['OperatingCashFlow'] - abs(pivoted_df.loc['CapitalExpenditures'])

        return pivoted_df


    def get_annual_data(self, include_segment_data: bool = False) -> pd.DataFrame:
        if self.df.empty:
            return pd.DataFrame()

        if 'period_length' not in self.df.columns:
             self.df['period_length'] = (self.df['end_date'] - self.df['start_date']).dt.days

        annual_data = self.df[(self.df['period_length'] > 350) & (self.df['period_length'] < 380)].copy()
        if annual_data.empty:
            print('no annual data found, could be that period is not annual')
            return pd.DataFrame()

        if not include_segment_data:
            annual_data = annual_data[annual_data['segment_value'].isnull()]

        if annual_data.empty:
            return pd.DataFrame()

        annual_data['date_range'] = annual_data['start_date'].dt.strftime('%Y-%m-%d') + ':' + annual_data['end_date'].dt.strftime('%Y-%m-%d')

        original_metric_order = annual_data['metric'].unique()

        # Ensure Revenue and COGS are first if they exist
        priority_metrics = []
        if 'Revenue' in original_metric_order:
            priority_metrics.append('Revenue')
        if 'COGS' in original_metric_order:
            priority_metrics.append('COGS')

        # Add remaining metrics
        other_metrics = [m for m in original_metric_order if m not in priority_metrics]
        final_metric_order = priority_metrics + other_metrics

        pivoted_df = annual_data.pivot_table(index='metric', columns='date_range', values='value', sort=False)

        pivoted_df = pivoted_df.reindex(final_metric_order)

        nan_threshold = len(pivoted_df) * 0.5
        columns_to_drop = [col for col in pivoted_df.columns if pivoted_df[col].isna().sum() > nan_threshold]
        pivoted_df = pivoted_df.drop(columns=columns_to_drop)
        print(pivoted_df.columns)

        return pivoted_df

    def get_quarterly_data(self) -> pd.DataFrame:
        if self.df.empty:
            return pd.DataFrame()

        if 'period_length' not in self.df.columns:
            self.df['period_length'] = (self.df['end_date'] - self.df['start_date']).dt.days

        quarterly_data = self.df[(self.df['period_length'] > 85) & (self.df['period_length'] < 95)].copy()

        if quarterly_data.empty:
            return pd.DataFrame()

        quarterly_data['date_range'] = quarterly_data['start_date'].dt.strftime('%Y-%m-%d') + ':' + quarterly_data['end_date'].dt.strftime('%Y-%m-%d')

        original_metric_order = quarterly_data['metric'].unique()

        # Ensure Revenue and COGS are first if they exist
        priority_metrics = []
        if 'Revenue' in original_metric_order:
            priority_metrics.append('Revenue')
        if 'COGS' in original_metric_order:
            priority_metrics.append('COGS')

        # Add remaining metrics
        other_metrics = [m for m in original_metric_order if m not in priority_metrics]
        final_metric_order = priority_metrics + other_metrics

        pivoted_df = quarterly_data.pivot_table(index='metric', columns='date_range', values='value', sort=False)

        pivoted_df = pivoted_df.reindex(final_metric_order)

        nan_threshold = len(pivoted_df) * 0.5
        columns_to_drop = [col for col in pivoted_df.columns if pivoted_df[col].isna().sum() > nan_threshold]
        pivoted_df = pivoted_df.drop(columns=columns_to_drop)
        print(pivoted_df.columns)

        return pivoted_df

    def get_metric(self, metric_name: str) -> pd.DataFrame:
        return self.df[self.df['metric'] == metric_name]


class CombinedFinancialStatements:
    def __init__(self, financial_statements: list[AbstractFinancialStatement], source_filings: list[Filing], ticker: str, company_name: str, form_type: str = None) -> None:
        self.financial_statements = financial_statements
        self.source_filings = source_filings
        self.ticker = ticker
        self.company_name = company_name
        self.form_type = form_type
        self.df = self._combine_statements()
        self.sec_filings_url = None
        self.has_more_than_one_continuous_period = None

    def _combine_statements(self) -> pd.DataFrame:
        if not self.financial_statements:
            return pd.DataFrame()

        tables = [stmt.table for stmt in self.financial_statements if not stmt.table.empty]

        if not tables:
            return pd.DataFrame()

        if len(tables) == 1:
            return tables[0].copy()

        result_df = tables[0].copy()

        for current_df in tables[1:]:
            if current_df.empty:
                continue

            new_columns = [col for col in current_df.columns if col not in result_df.columns]
            if new_columns:
                for col in new_columns:
                    for idx in result_df.index:
                        if idx in current_df.index:
                            result_df.loc[idx, col] = current_df.loc[idx, col]

        for col in result_df.columns:
            result_df[col] = result_df[col].apply(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) and abs(x) >= 1000 else x)

        return result_df

    def get_metric(self, metric_name):
        if metric_name in self.df.index:
            return self.df.loc[metric_name]
        return None

    def get_period(self, period):
        if period in self.df.columns:
            return self.df[period]
        return None

    def get_all_periods(self):
        return list(self.df.columns)

    def get_all_metrics(self):
        return list(self.df.index)

    def __str__(self) -> str:
        return f"CombinedFinancialStatements for {self.ticker} ({self.form_type})\n{self.df}"

    def analyze_period_coverage(self) -> dict:
        if self.df.empty:
            return {
                'coverage_by_year': {},
                'missing_periods': {},
                'has_continuous_coverage': False,
                'years_analyzed': []
            }

        periods = []
        for col in self.df.columns:
            start_str, end_str = col.split(':')
            start_date = pd.to_datetime(start_str, format='ISO8601')
            end_date = pd.to_datetime(end_str, format='ISO8601')
            periods.append((start_date, end_date))

        periods.sort(key=lambda x: x[0])

        coverage_by_year = {}
        years_analyzed = set()

        for start_date, end_date in periods:
            year = start_date.year
            years_analyzed.add(year)
            quarter = f"Q{(start_date.month - 1) // 3 + 1}"

            if year not in coverage_by_year:
                coverage_by_year[year] = set()
            coverage_by_year[year].add(quarter)

        has_continuous_coverage = True
        for i in range(len(periods) - 1):
            current_end = periods[i][1]
            next_start = periods[i + 1][0]
            if (next_start - current_end).days > 1:
                has_continuous_coverage = False
                break

        missing_periods = {}
        for year in years_analyzed:
            quarters = coverage_by_year[year]
            missing = {'Q1', 'Q2', 'Q3', 'Q4'} - quarters
            if missing:
                missing_periods[year] = sorted(list(missing))

        return {
            'coverage_by_year': {year: sorted(list(periods)) for year, periods in coverage_by_year.items()},
            'missing_periods': missing_periods,
            'has_continuous_coverage': has_continuous_coverage,
            'years_analyzed': sorted(list(years_analyzed))
        }

    def get_filings_for_period(self, fiscal_year: str, fiscal_period: str) -> list[Filing]:
        matching_filings = []
        for filing in self.source_filings:
            if (filing.cover_page and
                filing.cover_page.document_fiscal_year_focus == fiscal_year and
                filing.cover_page.document_fiscal_period_focus == fiscal_period):
                matching_filings.append(filing)
        return matching_filings

    def get_missing_periods_summary(self) -> str:
        analysis = self.analyze_period_coverage()
        if not analysis['missing_periods']:
            return f"Complete coverage for all analyzed years: {', '.join(analysis['years_analyzed'])}"

        summary_parts = []
        for year, missing in analysis['missing_periods'].items():
            summary_parts.append(f"{year}: missing {', '.join(missing)}")

        return "Missing periods - " + "; ".join(summary_parts)

    def create_implied_missing_quarters(self) -> pd.DataFrame:
        """Modify the dataframe in place to create implied missing quarters"""
        if self.df.empty:
            print('No data to create implied missing quarters')
            return self.df

        annual_columns = []
        quarterly_columns = []

        for col in self.df.columns:
            start_str, end_str = col.split(':')
            start_date = pd.to_datetime(start_str, format='ISO8601')
            end_date = pd.to_datetime(end_str, format='ISO8601')
            period_days = (end_date - start_date).days

            if 350 < period_days < 380:
                annual_columns.append(col)
            elif 85 < period_days < 95:
                quarterly_columns.append(col)

        for annual_col in annual_columns:
            annual_start_str, annual_end_str = annual_col.split(':')
            annual_start = pd.to_datetime(annual_start_str, format='ISO8601')
            annual_end = pd.to_datetime(annual_end_str, format='ISO8601')

            quarters_in_annual = []
            for q_col in quarterly_columns:
                q_start_str, q_end_str = q_col.split(':')
                q_start = pd.to_datetime(q_start_str, format='ISO8601')
                q_end = pd.to_datetime(q_end_str, format='ISO8601')

                if q_start >= annual_start and q_end <= annual_end:
                    quarters_in_annual.append(q_col)

            if len(quarters_in_annual) == 3:
                quarter_dates = []
                for q_col in quarters_in_annual:
                    q_start_str, q_end_str = q_col.split(':')
                    quarter_dates.append((pd.to_datetime(q_start_str, format='ISO8601'), pd.to_datetime(q_end_str, format='ISO8601')))

                quarter_dates.sort(key=lambda x: x[0])

                if quarter_dates[0][0] == annual_start:
                    implied_start = quarter_dates[-1][1] + pd.Timedelta(days=1)
                    implied_end = annual_end
                elif quarter_dates[-1][1] == annual_end:
                    implied_start = annual_start
                    implied_end = quarter_dates[0][0] - pd.Timedelta(days=1)
                else:
                    for i in range(len(quarter_dates) - 1):
                        if (quarter_dates[i+1][0] - quarter_dates[i][1]).days > 1:
                            implied_start = quarter_dates[i][1] + pd.Timedelta(days=1)
                            implied_end = quarter_dates[i+1][0] - pd.Timedelta(days=1)
                            break
                    else:
                        continue

                implied_col_name = f"{implied_start.strftime('%Y-%m-%d')}:{implied_end.strftime('%Y-%m-%d')}"

                if implied_col_name not in self.df.columns:
                    self.df[implied_col_name] = self.df[annual_col].fillna(0)
                    for q_col in quarters_in_annual:
                        self.df[implied_col_name] -= self.df[q_col].fillna(0)

        self.df.drop(columns=annual_columns, inplace=True)
        return self.df

    def clean_dataframe(self):
        self.df = self.df.map(self.convert_to_millions)
        self.df = self.df.loc[[not self.is_sparse_row(row) for _, row in self.df.iterrows()]]
        self.df = self.df.loc[:, [not self.is_sparse_column(self.df[col]) for col in self.df.columns]]
        self.has_more_than_one_continuous_period = self.has_more_than_one_continuous_period_check()
        print(self.has_more_than_one_continuous_period)
        return self.df

    def has_more_than_one_continuous_period_check(self) -> bool:
        if self.df.empty or len(self.df.columns) == 0:
            return False

        date_columns = []
        for col in self.df.columns:
            try:
                start_str, end_str = col.split(':')
                start_date = pd.to_datetime(start_str, format='ISO8601')
                end_date = pd.to_datetime(end_str, format='ISO8601')
                date_columns.append((col, start_date, end_date))
            except:
                continue

        if not date_columns:
            return False

        date_columns.sort(key=lambda x: x[1])

        continuous_periods = []
        current_period = [date_columns[0]]

        for i in range(1, len(date_columns)):
            prev_col, prev_start, prev_end = current_period[-1]
            curr_col, curr_start, curr_end = date_columns[i]

            days_gap = (curr_start - prev_end).days

            if days_gap <= 1 or (prev_start.year + 1 == curr_start.year and
                                 prev_start.month == 1 and prev_start.day == 1 and
                                 prev_end.month == 12 and prev_end.day == 31 and
                                 curr_start.month == 1 and curr_start.day == 1 and
                                 curr_end.month == 12 and curr_end.day == 31):
                current_period.append(date_columns[i])
            else:
                continuous_periods.append(current_period)
                current_period = [date_columns[i]]

        continuous_periods.append(current_period)

        longest_period = max(continuous_periods, key=len)

        columns_to_keep = [col_info[0] for col_info in longest_period]

        # self.df = self.df[columns_to_keep]

        return len(continuous_periods) > 1

    def convert_to_millions(self, val):
        try:
            # Check if it's a numeric value
            num = float(val)

            # Only convert to millions if number is at least 1,000
            if abs(num) >= 1_000:
                return round(num / 1_000_000, 2)
            else:
                return num
        except (ValueError, TypeError):
            # Return original value if not numeric
            return val

    def is_sparse_row(self, row):
        numeric_values = 0
        zero_or_nan_values = 0

        for val in row:
            try:
                num = float(val)
                numeric_values += 1
                if num == 0 or pd.isna(num):
                    zero_or_nan_values += 1
            except (ValueError, TypeError):
                pass

        if numeric_values == 0:
            return False

        sparse_percentage = zero_or_nan_values / numeric_values if numeric_values > 0 else 0
        return sparse_percentage > 0.5

    def is_sparse_column(self, column):
        numeric_values = 0
        zero_or_nan_values = 0

        for val in column:
            try:
                num = float(val)
                numeric_values += 1
                if num == 0 or pd.isna(num):
                    zero_or_nan_values += 1
            except (ValueError, TypeError):
                pass

        if numeric_values == 0:
            return False

        sparse_percentage = zero_or_nan_values / numeric_values if numeric_values > 0 else 0
        return sparse_percentage > 0.5

class StockTicker:
    def __init__(self, symbol: str):
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Stock ticker must be a non-empty string")

        symbol = symbol.upper().strip()
        if not symbol.isalnum() or len(symbol) > 10:
            raise ValueError("Stock ticker must be alphanumeric and max 10 characters")

        self._symbol = symbol

    @property
    def symbol(self) -> str:
        return self._symbol

    def __str__(self) -> str:
        return self._symbol

    def __repr__(self) -> str:
        return f"StockTicker('{self._symbol}')"

    def __eq__(self, other) -> bool:
        if not isinstance(other, StockTicker):
            return False
        return self._symbol == other._symbol

    def __hash__(self) -> int:
        return hash(self._symbol)


@dataclass(frozen=True)
class PricePoint:
    date: datetime
    price: Decimal
    market_reference_price: Optional[Decimal] = None

    def __post_init__(self):
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.market_reference_price is not None and self.market_reference_price <= 0:
            raise ValueError("Market reference price must be positive")


class PriceTimeSeries:
    def __init__(self, ticker: str, price_points: List[PricePoint]):
        self.ticker = ticker
        self.price_points = price_points

    def most_recent_price(self) -> PricePoint:
        return self.price_points[-1]

    def table(self) -> pd.DataFrame:
        if not self.price_points:
            return pd.DataFrame()

        data = []
        has_market_data = any(point.market_reference_price is not None for point in self.price_points)

        for point in self.price_points:
            row_data = {
                'Date': point.date,
                'Price': float(point.price)
            }

            if has_market_data and point.market_reference_price is not None:
                row_data['Market_Price'] = float(point.market_reference_price)
            elif has_market_data:
                row_data['Market_Price'] = None

            data.append(row_data)

        df = pd.DataFrame(data)

        if df.empty:
            return df

        df['Date'] = pd.to_datetime(df['Date'])
        df = df.set_index('Date')

        if has_market_data and 'Market_Price' in df.columns:
            df['Relative_Performance'] = (df['Price'] / df['Market_Price']) * 100

        if len(df) > 1:
            df['Price_Change_Pct'] = df['Price'].pct_change() * 100
            if has_market_data and 'Market_Price' in df.columns:
                df['Market_Change_Pct'] = df['Market_Price'].pct_change() * 100

        df['Price'] = df['Price'].round(2)

        if has_market_data and 'Market_Price' in df.columns:
            df['Market_Price'] = df['Market_Price'].round(2)
            if 'Relative_Performance' in df.columns:
                df['Relative_Performance'] = df['Relative_Performance'].round(2)

        if 'Price_Change_Pct' in df.columns:
            df['Price_Change_Pct'] = df['Price_Change_Pct'].round(2)
            if 'Market_Change_Pct' in df.columns:
                df['Market_Change_Pct'] = df['Market_Change_Pct'].round(2)

        df.columns.name = f'{self.ticker} Price Data'

        return df


class MarketDataProvider(Protocol):
    @abstractmethod
    def fetch_prices(self, ticker: str, start_date: date, end_date: date) -> List[PricePoint]:
        pass
