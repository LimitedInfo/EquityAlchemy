from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class FilingType:
    annual_report = '10-K'
    quarterly_report = '10-Q'


class Filing:
    def __init__(self, cik, form, filing_date, accession_number, primary_document, filing_repository) -> None:
        self.cik = cik # Central Index Key, unique identifier for a company or individual.
        self.form = form
        self.filing_date = filing_date
        self.accession_number = accession_number # A 20-character string that uniquely identifies a specific filing in the EDGAR system.
        self.primary_document = primary_document # The main document file within the filing submission.
        self._repository = filing_repository
        self._income_statement = None
        self._filing_url = None
        self._data = None

    @property
    def data(self):
        if self._data is None:
            self._data = self._repository.get_filing_data(self.cik, self.accession_number, self.primary_document)
        return self._data

    @property
    def filing_url(self):
        if self._filing_url is None:
            self._filing_url = self._repository.get_filing_url(self.cik, self.accession_number, self.primary_document)
        return self._filing_url

    @property
    def income_statement(self):
        if self._income_statement is None and self.data is not None:
            self._income_statement = IncomeStatement(self.data['StatementsOfIncome'], self.form)
        return self._income_statement


class Company:
    def __init__(self, name: str, ticker, filing_repository) -> None:
        self.name = name
        self.ticker = ticker
        self._repository = filing_repository
        self._cik = None
        self._filings = None

    @property
    def cik(self):
        if self._cik is None:
            self._cik = self._repository.get_cik_by_ticker(self.ticker)
        return self._cik

    @property
    def filings(self):
        if self._filings is None:
            print("getting filings")

            self._filings = self._repository.get_filings(self.cik)
            print("filings retrieved")


        return self._filings

    def get_filings_by_type(self, filing_type: FilingType):
        return [filing for filing in self.filings if filing.form == filing_type]

    def join_financial_statements(self, financial_statements, llm_repository=None):
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

            if llm_repository:
                index_mapping = llm_repository.map_dataframes(financial_statements[0], current_df)

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
        filings_to_process = self.filings
        if form_type:
            filings_to_process = [f for f in filings_to_process if f.form == form_type]

        sorted_filings = sorted(filings_to_process, key=lambda f: f.filing_date, reverse=True)

        valid_filings = []
        for filing in sorted_filings:
            if hasattr(filing, statement_type) and hasattr(getattr(filing, statement_type), 'table'):
                valid_filings.append(filing)

        if not valid_filings:
            return []

        covered_years = set()
        selected_filings = []

        all_available_years = set()
        for filing in valid_filings:
            statement = getattr(filing, statement_type)
            for col in statement.table.columns:
                year = col.split('-')[0]
                all_available_years.add(year)

        filing_contributions = {}

        for filing in valid_filings:
            statement = getattr(filing, statement_type)
            filing_years = set()
            for col in statement.table.columns:
                year = col.split('-')[0]
                filing_years.add(year)

            filing_contributions[filing] = filing_years

        if valid_filings:
            newest_filing = valid_filings[0]
            selected_filings.append(newest_filing)
            covered_years.update(filing_contributions[newest_filing])

        if len(valid_filings) > 1:
            oldest_filing = valid_filings[-1]
            new_years = filing_contributions[oldest_filing] - covered_years
            if new_years:
                selected_filings.append(oldest_filing)
                covered_years.update(filing_contributions[oldest_filing])

        remaining_filings = [f for f in valid_filings if f not in selected_filings]
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



class IncomeStatement:
    def __init__(self, data: dict, form: str) -> None:
        self.raw_data = data
        self.df = self._process_data()
        self.form = form

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


class CombinedIncomeStatements:
    def __init__(self, income_statements: list[IncomeStatement], ticker: str, form_type: str = None) -> None:
        self.income_statements = income_statements
        self.ticker = ticker
        self.form_type = form_type
        self.df = self._combine_statements()

    def _combine_statements(self) -> pd.DataFrame:
        if not self.income_statements:
            return pd.DataFrame()

        tables = [stmt.table for stmt in self.income_statements if not stmt.table.empty]

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
        return f"CombinedIncomeStatements for {self.ticker} ({self.form_type})\n{self.df}"
