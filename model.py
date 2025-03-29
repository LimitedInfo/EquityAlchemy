import pandas as pd
from repository import SECFilingRepository



class Company:
    def __init__(self, name, ticker, filing_repository: SECFilingRepository):
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
        print("returning filings")
        return self._filings



class Filing:
    def __init__(self, cik, form, filing_date, accession_number, primary_document, filing_repository: SECFilingRepository):
        self.cik = cik
        self.form = form
        self.filing_date = filing_date
        self.accession_number = accession_number
        self.primary_document = primary_document
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
        if self._income_statement is None:
            self._income_statement = IncomeStatement(self.data['StatementsOfIncome'])
        return self._income_statement


class IncomeStatement:
    def __init__(self, data: dict):
        self.raw_data = data
        self.df = self._process_data()

    def _process_data(self):
        """Process the raw financial data into a structured DataFrame."""
        rows = []

        # Process each financial metric in the data
        for metric, entries in self.raw_data.items():
            for entry in entries:
                # Extract period data
                period_data = entry.get('period', {})
                start_date = None
                end_date = None

                # Handle period data based on its type
                if isinstance(period_data, dict):
                    start_date = period_data.get('startDate')
                    end_date = period_data.get('endDate')
                elif isinstance(period_data, str):
                    # If period is a string, use it as both start and end date
                    start_date = period_data
                    end_date = period_data

                # Extract segment information if available
                segment_info = None
                segment_dimension = None
                if 'segment' in entry:
                    segment_info = entry['segment'].get('value')
                    segment_dimension = entry['segment'].get('dimension')

                # Create a row for this entry
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

        # Create DataFrame from collected rows
        df = pd.DataFrame(rows)

        # Convert date columns to datetime
        if not df.empty:
            df['start_date'] = pd.to_datetime(df['start_date'])
            df['end_date'] = pd.to_datetime(df['end_date'])

        return df

    def get_annual_data(self, include_segment_data: bool = False):
        """Return only annual financial data."""
        if self.df.empty:
            return pd.DataFrame()

        # Calculate period length in days
        self.df['period_length'] = (self.df['end_date'] - self.df['start_date']).dt.days

        # Filter for periods that are approximately 1 year (between 350 and 380 days)
        annual_data = self.df[(self.df['period_length'] > 350) & (self.df['period_length'] < 380)]

        # Filter out segment data if not requested
        if not include_segment_data:
            annual_data = annual_data[annual_data['segment_value'].isnull()]

        return annual_data

    def get_quarterly_data(self):
        """Return only quarterly financial data."""
        if self.df.empty:
            return pd.DataFrame()

        # Calculate period length in days
        self.df['period_length'] = (self.df['end_date'] - self.df['start_date']).dt.days

        # Filter for periods that are approximately 3 months (between 85 and 95 days)
        quarterly_data = self.df[(self.df['period_length'] > 85) & (self.df['period_length'] < 95)]

        return quarterly_data

    def get_metric(self, metric_name):
        """Return data for a specific metric."""
        return self.df[self.df['metric'] == metric_name]
