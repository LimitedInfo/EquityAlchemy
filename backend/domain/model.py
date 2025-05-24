from dataclasses import dataclass
import pandas as pd
from abc import ABC, abstractmethod

from backend.service_layer import uow


@dataclass(frozen=True)
class FilingType:
    annual_report = '10-K'
    quarterly_report = '10-Q'


class Filing:
    def __init__(self, cik: str, form: str, filing_date: str, accession_number: str,
                 primary_document: str, data: dict = None, filing_url: str = None) -> None:
        self.cik = cik
        self.form = form
        self.filing_date = filing_date
        self.accession_number = accession_number
        self.primary_document = primary_document
        self._data = data
        self._filing_url = filing_url
        self._income_statement = None

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
    def income_statement(self):
        if self._income_statement is None and self._data is not None:
            if 'StatementsOfIncome' in self._data:
                self._income_statement = IncomeStatement(self._data['StatementsOfIncome'], self.form)
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

    def get_filings_by_type(self, filing_type: str):
        return [filing for filing in self._filings if filing.form == filing_type]

    def join_financial_statements(self, financial_statements: list[pd.DataFrame], index_mapping: dict = None) -> pd.DataFrame:
        if len(financial_statements) < 2:
            if financial_statements and hasattr(financial_statements[0], 'copy'):
                return financial_statements[0].copy()
            elif financial_statements:
                if isinstance(financial_statements[0], pd.DataFrame):
                    return financial_statements[0].copy()
                else:
                    return pd.DataFrame()
            else:
                return pd.DataFrame()

        if not isinstance(financial_statements[0], pd.DataFrame):
            raise TypeError("Expected a DataFrame object, but got {0}".format(type(financial_statements[0])))

        result_df = financial_statements[0].copy()

        for i, statement in enumerate(financial_statements[1:], 1):
            if not isinstance(statement, pd.DataFrame):
                raise TypeError("Expected a DataFrame object at index {0}, but got {1}".format(i, type(statement)))

            current_df = statement

            if current_df.empty:
                continue

            if index_mapping:
                mapped_df = current_df.copy()
                new_index = []

                for idx in current_df.index:
                    found = False
                    for base_idx, mapped_idx in index_mapping.items():
                        if idx == mapped_idx:
                            new_index.append(base_idx)
                            found = True
                            break

                    if not found:
                        new_index.append(idx)

                mapped_df.index = new_index

                new_columns = [col for col in mapped_df.columns if col not in result_df.columns]
                if new_columns:
                    for col in new_columns:
                        for idx in result_df.index:
                            if idx in mapped_df.index:
                                result_df.loc[idx, col] = mapped_df.loc[idx, col]

        return result_df

    def filter_filings(self, form_type: str='10-K', statement_type: str='income_statement') -> list[Filing]:
        """return the minimal list of filings that covers the maximum number of years. """

        filings_to_process = self._filings
        if form_type:
            filings_to_process = [f for f in filings_to_process if f.form == form_type]

        sorted_filings = sorted(filings_to_process, key=lambda f: f.filing_date, reverse=True)

        # load the data for the filings
        with uow.UnitOfWork() as uow_instance:
            for filing in sorted_filings:
                filing._data = uow_instance.sec_filings.get_filing_data(
                    filing.cik,
                    filing.accession_number,
                    filing.primary_document
                )

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


class AbstractFinancialStatement(ABC):
    def __init__(self, data: dict, form: str) -> None:
        self.raw_data = data
        self.form = form
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
    def __init__(self, data: dict, form: str) -> None:
        super().__init__(data, form)

    def _process_data(self) -> pd.DataFrame:
        rows = []

        for metric, entries in self.raw_data.items():
            for entry in entries:

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

        return pivoted_df

    def get_metric(self, metric_name: str) -> pd.DataFrame:
        return self.df[self.df['metric'] == metric_name]


class CombinedFinancialStatements:
    def __init__(self, financial_statements: list[AbstractFinancialStatement], ticker: str, form_type: str = None) -> None:
        self.financial_statements = financial_statements
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

    def __str__(self) -> str:
        return f"CombinedFinancialStatements for {self.ticker} ({self.form_type})\n{self.df}"
