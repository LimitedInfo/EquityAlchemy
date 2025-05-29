from dataclasses import dataclass
import pandas as pd
from abc import ABC, abstractmethod
from typing import List, Optional



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


class Filing:
    def __init__(self, cik: str, form: str, filing_date: str, accession_number: str,
                 primary_document: str, data: dict = None, filing_url: str = None,
                 cover_page: CoverPage = None) -> None:
        self.cik = cik
        self.form = form
        self.filing_date = filing_date
        self.accession_number = accession_number
        self.primary_document = primary_document
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
            if 'StatementsOfIncome' in self._data:
                self._income_statement = IncomeStatement(self._data['StatementsOfIncome'], self.form, self._data.get('cov'))
        return self._income_statement


class Company:
    def __init__(self, name: str, ticker: str, cik: str = None, filings: list[Filing] = None) -> None:
        self.name = name
        self.ticker = ticker
        self.cik = cik
        self._filings = filings or []

    @property
    def filings(self):
        return self._filings

    @filings.setter
    def filings(self, value: list[Filing]):
        self._filings = value

    def get_filings_by_type(self, filing_type: str | list[str]):
        if isinstance(filing_type, str):
            return [filing for filing in self._filings if filing.form == filing_type]
        return [filing for filing in self._filings if filing.form in filing_type]


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

        skip_count = Company.get_skip_amount(filings_list[0], form_type)


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
                    if 'segment' in entry or 'value' not in entry:
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
            df['start_date'] = pd.to_datetime(df['start_date'])
            df['end_date'] = pd.to_datetime(df['end_date'])

        return df

    @property
    def table(self) -> pd.DataFrame:
        if self.form == '10-K':
            return self.get_annual_data()
        elif self.form == '10-Q':
            return self.get_quarterly_data()
        else:
            return pd.DataFrame()


    def get_annual_data(self, include_segment_data: bool = False) -> pd.DataFrame:
        if self.df.empty:
            return pd.DataFrame()

        if 'period_length' not in self.df.columns:
             self.df['period_length'] = (self.df['end_date'] - self.df['start_date']).dt.days

        annual_data = self.df[(self.df['period_length'] > 350) & (self.df['period_length'] < 380)].copy()

        if not include_segment_data:
            annual_data = annual_data[annual_data['segment_value'].isnull()]

        if annual_data.empty:
            return pd.DataFrame()

        annual_data['date_range'] = annual_data['start_date'].dt.strftime('%Y-%m-%d') + ':' + annual_data['end_date'].dt.strftime('%Y-%m-%d')

        pivoted_df = annual_data.pivot_table(index='metric', columns='date_range', values='value')

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

        pivoted_df = quarterly_data.pivot_table(index='metric', columns='date_range', values='value')

        nan_threshold = len(pivoted_df) * 0.5
        columns_to_drop = [col for col in pivoted_df.columns if pivoted_df[col].isna().sum() > nan_threshold]
        pivoted_df = pivoted_df.drop(columns=columns_to_drop)
        print(pivoted_df.columns)

        return pivoted_df

    def get_metric(self, metric_name: str) -> pd.DataFrame:
        return self.df[self.df['metric'] == metric_name]


class CombinedFinancialStatements:
    def __init__(self, financial_statements: list[AbstractFinancialStatement], source_filings: list[Filing], ticker: str, form_type: str = None) -> None:
        self.financial_statements = financial_statements
        self.source_filings = source_filings
        self.ticker = ticker
        self.form_type = form_type
        self.df = self._combine_statements()

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
        coverage = {}
        missing_periods = {}

        for filing in self.source_filings:
            if not filing.cover_page:
                continue

            fiscal_year = filing.cover_page.document_fiscal_year_focus
            fiscal_period = filing.cover_page.document_fiscal_period_focus

            if not fiscal_year or not fiscal_period:
                continue

            if fiscal_year not in coverage:
                coverage[fiscal_year] = set()
                missing_periods[fiscal_year] = {'Q1', 'Q2', 'Q3', 'Q4', 'FY'}

            if fiscal_period in ['Q1', 'Q2', 'Q3', 'Q4']:
                coverage[fiscal_year].add(fiscal_period)
                missing_periods[fiscal_year].discard(fiscal_period)
            elif fiscal_period == 'FY' or filing.form == '10-K':
                coverage[fiscal_year].add('FY')
                missing_periods[fiscal_year].discard('FY')

        for year in list(missing_periods.keys()):
            if not missing_periods[year]:
                del missing_periods[year]

        return {
            'coverage_by_year': {year: sorted(list(periods)) for year, periods in coverage.items()},
            'missing_periods': {year: sorted(list(periods)) for year, periods in missing_periods.items()},
            'has_complete_quarterly_coverage': self._check_complete_quarterly_coverage(coverage),
            'years_analyzed': sorted(coverage.keys())
        }

    def _check_complete_quarterly_coverage(self, coverage: dict) -> dict:
        complete_coverage = {}
        for year, periods in coverage.items():
            complete_coverage[year] = {'Q1', 'Q2', 'Q3', 'Q4'}.issubset(periods)
        return complete_coverage

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

    def create_implied_missing_quarters(self) -> None:
        if self.df.empty:
            return

        annual_columns = []
        quarterly_columns = []

        for col in self.df.columns:
            start_str, end_str = col.split(':')
            start_date = pd.to_datetime(start_str)
            end_date = pd.to_datetime(end_str)
            period_days = (end_date - start_date).days

            if 350 < period_days < 380:
                annual_columns.append(col)
            elif 85 < period_days < 95:
                quarterly_columns.append(col)

        for annual_col in annual_columns:
            annual_start_str, annual_end_str = annual_col.split(':')
            annual_start = pd.to_datetime(annual_start_str)
            annual_end = pd.to_datetime(annual_end_str)

            quarters_in_annual = []
            for q_col in quarterly_columns:
                q_start_str, q_end_str = q_col.split(':')
                q_start = pd.to_datetime(q_start_str)
                q_end = pd.to_datetime(q_end_str)

                if q_start >= annual_start and q_end <= annual_end:
                    quarters_in_annual.append(q_col)

            if len(quarters_in_annual) == 3:
                quarter_dates = []
                for q_col in quarters_in_annual:
                    q_start_str, q_end_str = q_col.split(':')
                    quarter_dates.append((pd.to_datetime(q_start_str), pd.to_datetime(q_end_str)))

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
