import abc
import requests

from dotenv import load_dotenv
import backend.domain.model as model
from backend.adapters.filing_mapper import FilingMapper
from sec_api import XbrlApi
import os
import json
import google.generativeai as genai
import traceback
import pandas as pd
from typing import Optional, Iterable
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.adapters.orm import CombinedFinancialStatementsORM
from typing import Protocol


load_dotenv()

class SECFilingRepository():
    def __init__(self):
        self.headers = {"User-Agent": os.getenv("USER_AGENT")}

    def get_cik_by_ticker(self, ticker):
        # TODO: Cache this
        ticker_url = "https://www.sec.gov/files/company_tickers.json"
        data = self._make_request(ticker_url, self.headers)

        for item in data.values():
            if item['ticker'].lower() == ticker.lower():
                cik = str(item['cik_str']).zfill(10)
                return cik
        return None

    def get_filings(self, cik):
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        data = self._make_request(submissions_url)

        filings = []

        # Process recent filings
        filings_data = data.get("filings", {}).get("recent", {})
        forms = filings_data.get("form", [])
        dates = filings_data.get("filingDate", [])
        accessions = filings_data.get("accessionNumber", [])
        primary_docs = filings_data.get("primaryDocument", [])
        isXBRL = filings_data.get("isXBRL", [])

        for form, filing_date, accession_number, primary_document, is_xbrl in zip(forms, dates, accessions, primary_docs, isXBRL):
            if form in ['10-q', '10-k', '10-K', '10-Q', '10-Q/A', '10-K/A', '10-q/a', '10-k/a'] and is_xbrl:
                filing = model.Filing(cik, form, filing_date, accession_number, primary_document, is_xbrl)
                filings.append(filing)

        # Process non-recent filings
        older_files = data.get("filings", {}).get("files", [])
        if older_files:
            for file_info in older_files:
                older_url = f"https://data.sec.gov/submissions/{file_info['name']}"
                older_data = self._make_request(older_url)

                older_forms = older_data.get("form", [])
                older_dates = older_data.get("filingDate", [])
                older_accessions = older_data.get("accessionNumber", [])
                older_primary_docs = older_data.get("primaryDocument", [])
                older_isXBRL = older_data.get("isXBRL", [])
                for form, filing_date, accession_number, primary_document, is_xbrl in zip(older_forms, older_dates, older_accessions, older_primary_docs, older_isXBRL):
                    if form in ['10-q', '10-k', '10-K', '10-Q', '10-Q/A', '10-K/A', '10-q/a', '10-k/a'] and is_xbrl:
                        filing = model.Filing(cik, form, filing_date, accession_number, primary_document, is_xbrl)
                        filings.append(filing)

        return filings

    def get_cover_page_properties(self, filing):
        return filing.data.get('CoverPage', {})

    def get_filing_data(self, cik, accession_number, primary_document):
        xbrlApi = XbrlApi(os.getenv("SEC_API_KEY"))
        try:
            data = xbrlApi.xbrl_to_json(htm_url=self.get_filing_url(cik, accession_number, primary_document))
            cover_page = FilingMapper.map_cover_page_from_api(data) if data else None
            return data, cover_page
        except Exception as e:
            print(f"Error getting filing data for {cik} {accession_number} {primary_document}: {e}")
            return None, None

    def get_filing_url(self, cik, accession_number, primary_document):
        filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_number}/{primary_document}"
        return filing_url

    def _make_request(self, url: str, headers: dict = None) -> dict:
        session = requests.Session()
        session.headers.update(self.headers)
        try:
            response = session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed for URL: {url}")
            print(f"Error: {str(e)}")
            print(f"Status code: {response.status_code if 'response' in locals() else 'N/A'}")
            print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
            raise


class FakeSECFilingRepository:
    def __init__(self):
        self.tickers_to_cik = {
            'aapl': '0000320193',
            'msft': '0000789019',
            'goog': '0001652044',
            'amzn': '0001018724',
            'fb': '0001326801'
        }

        self.filings_by_cik = {
            '0000320193': [
                model.Filing('0000320193', '10-K', '2024-11-01', '0000320193-24-000123', 'aapl-20240928.htm'),
                model.Filing('0000320193', '10-K', '2020-10-30', '0000320193-20-000096', 'aapl-20200926.htm'),
                model.Filing('0000320193', '10-Q', '2025-01-31', '0000320193-25-000008', 'aapl-20241228.htm'),
            ],
            '0000789019': [
                model.Filing('0000789019', '10-K', '2024-07-30', '0000950170-24-087843', 'msft-20240630.htm'),
                model.Filing('0000789019', '10-Q', '2025-01-29', '0000950170-25-010491', 'msft-20241231.htm')
            ]
        }

        self.filing_data = {}

        file_mapping = {
            ('0000320193', '0000320193-24-000123', 'aapl-20240928.htm'): 'AAPL_10K_20241101_data.json',
            ('0000320193', '0000320193-20-000096', 'aapl-20200926.htm'): 'AAPL_10K_20201030_data.json',
            ('0000320193', '0000320193-25-000008', 'aapl-20241228.htm'): 'AAPL_10Q_20250131_data.json',
            ('0000789019', '0000950170-24-087843', 'msft-20240630.htm'): 'MSFT_10K_20240730_data.json',
            ('0000789019', '0000950170-25-010491', 'msft-20241231.htm'): 'MSFT_10Q_20250129_data.json'
        }

        test_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'test_data')
        print(f"Loading test data from: {test_data_dir}")
        for key, filename in file_mapping.items():
            filepath = os.path.join(test_data_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.filing_data[key] = json.load(f)
            except FileNotFoundError:
                print(f"Warning: Test data file not found: {filepath}")
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from file: {filepath}")
            except Exception as e:
                print(f"Warning: Error loading file {filepath}: {e}")

    def get_cik_by_ticker(self, ticker):
        return self.tickers_to_cik.get(ticker.lower())

    def get_filings(self, cik):
        return self.filings_by_cik.get(cik, [])

    def get_filing_data(self, cik, accession_number, primary_document):
        key = (cik, accession_number, primary_document)
        data = self.filing_data.get(key, {})
        cover_page = FilingMapper.map_cover_page_from_api(data) if data else None
        return data, cover_page

    def get_filing_url(self, cik, accession_number, primary_document):
        return f"https://fake-sec.gov/Archives/edgar/data/{int(cik)}/{accession_number}/{primary_document}"

    def _make_request(self, url, headers=None):
        return {}


class LLMRepository:
    def __init__(self):
        self.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
        self.GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
        self.REDIRECT_URI = os.getenv("REDIRECT_URI")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_client = self.authenticate_gemini()

    def authenticate_gemini(self):
        if not self.gemini_api_key:
            raise ValueError("Gemini API key is required")

        import google.generativeai as genai
        genai.configure(api_key=self.gemini_api_key)
        return genai.GenerativeModel('gemini-1.5-flash')

    def map_dataframes(self, df1, df2, client=None, max_retries=2):
        import pandas as pd
        import traceback

        if client is None:
            client = self.gemini_client

        df1_numeric = df1.apply(pd.to_numeric)
        df2_numeric = df2.apply(pd.to_numeric)

        print(f"\n=== DEBUG: DATAFRAME MAPPING ===")
        print(f"DF1 index types: {[idx for idx in df1.index]}")
        print(f"DF2 index types: {[idx for idx in df2.index]}")

        problematic_indices = []

        for attempt in range(max_retries + 1):  # +1 for the initial attempt
            try:
                if attempt > 0:
                    print(f"Retry attempt {attempt} for mapping. Problematic indices: {problematic_indices}")
                    exclude_note = f"EXCLUDE these problematic indices that caused errors in previous attempts: {problematic_indices}"
                else:
                    exclude_note = ""

                prompt = f"""
                I have two dataframes with different index labels that I need to map between:

                DataFrame 1 indexes: {list(df1_numeric.index)}
                DataFrame 2 indexes: {list(df2_numeric.index)}

                Create a JSON mapping where the keys are from DataFrame 1 and values are the matching indexes from DataFrame 2.
                Only output the raw JSON mapping without any formatting, code blocks, or newlines.
                ONLY return the rows for which you can determine a definitive mapping.
                Pay careful attention to the fields EarningsPerShareBasic, EarningsPerShareDiluted,
                WeightedAverageNumberOfSharesOutstanding, and WeightedAverageNumberOfSharesDiluted.
                You also seem to have trouble mapping 'WeightedAverageNumberOfDilutedSharesOutstanding'
                make sure to only include ONE \"Of\" in the mapping, like WeightedAverageNumberOfDilutedSharesOutstanding.
                {exclude_note}"""

                print(f"Sending prompt to LLM with {len(list(df1_numeric.index))} rows from DF1 and {len(list(df2_numeric.index))} rows from DF2")

                response = client.generate_content(
                    prompt,
                    generation_config={
                        'response_mime_type': 'application/json',
                    }
                )

                response_text = response.text
                print(f"Raw LLM response: {response_text[:200]}...") # Print first 200 chars to avoid huge logs

                if '```' in response_text:
                    response_text = response_text.split('```')[1].strip()
                    print(f"After code block extraction: {response_text[:200]}...")
                if 'json' in response_text:
                    response_text = response_text.split('json')[1].strip()
                    print(f"After json identifier removal: {response_text[:200]}...")

                mapping = json.loads(response_text)
                print(f"Parsed mapping: {mapping}")

                if isinstance(mapping, list):
                    print("Converting list of dictionaries to a single dictionary")
                    single_mapping = {}
                    for item in mapping:
                        if isinstance(item, dict):
                            single_mapping.update(item)
                    mapping = single_mapping
                    print(f"Converted mapping: {mapping}")

                valid_mapping = {}
                for source_idx, target_idx in mapping.items():
                    if source_idx not in df1.index:
                        print(f"WARNING: Mapping contains source index '{source_idx}' not in DF1 - skipping")
                        problematic_indices.append(source_idx)
                        continue
                    if target_idx not in df2.index:
                        print(f"WARNING: Mapping contains target index '{target_idx}' not in DF2 - skipping")
                        problematic_indices.append(source_idx)
                        continue

                    valid_mapping[source_idx] = target_idx

                if not valid_mapping:
                    raise ValueError("No valid mappings found in LLM response")

                print(f"Successfully created valid mapping with {len(valid_mapping)} entries")
                return valid_mapping

            except json.JSONDecodeError as json_err:
                print(f"Error parsing JSON (attempt {attempt+1}/{max_retries+1}): {json_err}")
                print(f"Response text: {response_text}")

                if attempt == max_retries:
                    print("Maximum retries reached. Returning empty mapping.")
                    return {}
            except ValueError as val_err:
                print(f"Value error in mapping (attempt {attempt+1}/{max_retries+1}): {val_err}")

                if attempt == max_retries:
                    print("Maximum retries reached. Returning empty mapping.")
                    return {}
            except Exception as e:
                print(f"Unexpected error in mapping (attempt {attempt+1}/{max_retries+1}): {e}")
                traceback.print_exc()

                if attempt == max_retries:
                    print("Maximum retries reached. Returning empty mapping.")
                    return {}

        return {}

    def make_index_readable(self, index_names: list[str], client=None, max_retries=2):


        if client is None:
            client = self.gemini_client

        for attempt in range(max_retries + 1):
            try:
                prompt = f"""
                Convert these financial metric names to more readable, human-friendly names.
                Keep them concise but clear. Return a JSON mapping where keys are original names and values are readable names.
                Original names: {list(index_names)}

                Only output the raw JSON mapping without any formatting, code blocks, or newlines. If a name is already readable,
                keep it as is. Example format: {{"TechnicalName": "Readable Name", "AnotherTechnicalName": "Another Readable Name"}}
                """

                print(f"Sending prompt to LLM to make {len(index_names)} index names readable")

                response = client.generate_content(
                    prompt,
                    generation_config={
                        'response_mime_type': 'application/json',
                    }
                )

                response_text = response.text
                print(f"Raw LLM response: {response_text[:200]}...") # Print first 200 chars to avoid huge logs

                if '```' in response_text:
                    response_text = response_text.split('```')[1].strip()
                    print(f"After code block extraction: {response_text[:200]}...")
                if 'json' in response_text:
                    response_text = response_text.split('json')[1].strip()
                    print(f"After json identifier removal: {response_text[:200]}...")

                mapping = json.loads(response_text)
                print(f"Parsed mapping: {mapping}")

                if isinstance(mapping, list):
                    print("Converting list of dictionaries to a single dictionary in make_index_readable")
                    single_mapping = {}
                    for item in mapping:
                        if isinstance(item, dict):
                            single_mapping.update(item)
                    mapping = single_mapping
                    print(f"Converted mapping: {mapping}")

                valid_mapping = {}
                for source_idx, readable_name in mapping.items():
                    if source_idx in index_names:
                        valid_mapping[source_idx] = readable_name
                    else:
                        print(f"WARNING: Mapping contains source index '{source_idx}' not in original index names - skipping")

                for name in index_names:
                    if name not in valid_mapping:
                        valid_mapping[name] = name
                        print(f"Adding missing index '{name}' with unchanged name")

                print(f"Successfully created readable mapping with {len(valid_mapping)} entries")
                return valid_mapping

            except json.JSONDecodeError as json_err:
                print(f"Error parsing JSON (attempt {attempt+1}/{max_retries+1}): {json_err}")
                print(f"Response text: {response_text}")

                if attempt == max_retries:
                    print("Maximum retries reached. Returning unchanged names.")
                    return {name: name for name in index_names}

            except Exception as e:
                print(f"Unexpected error in make_index_readable (attempt {attempt+1}/{max_retries+1}): {e}")
                traceback.print_exc()

                if attempt == max_retries:
                    print("Maximum retries reached. Returning unchanged names.")
                    return {name: name for name in index_names}

        return {name: name for name in index_names}

class CombinedFinancialStatementsRepository(Protocol):
    @abc.abstractmethod
    def add(self, stmt: model.CombinedFinancialStatements) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def add_many(self, stmts: Iterable[model.CombinedFinancialStatements]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, ticker: str, form_type: str) -> Optional[model.CombinedFinancialStatements]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_ticker(self, ticker: str) -> list[model.CombinedFinancialStatements]:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, ticker: str, form_type: str) -> None:
        raise NotImplementedError


class PostgresCombinedFinancialStatementsRepository(CombinedFinancialStatementsRepository):
    def __init__(self, session: Session):
        self.session = session

    def _serialize(self, stmt: model.CombinedFinancialStatements) -> dict:
        json_str = stmt.df.to_json(orient="split", date_format="iso")
        return {
            "ticker": stmt.ticker,
            "form_type": stmt.form_type,
            "data": json.loads(json_str)
        }

    def _deserialize_to_domain(self, orm_obj: CombinedFinancialStatementsORM) -> model.CombinedFinancialStatements:
        from io import StringIO
        df = pd.read_json(StringIO(json.dumps(orm_obj.data)), orient="split")

        stmt = model.CombinedFinancialStatements(
            financial_statements=[],
            source_filings=[],
            ticker=orm_obj.ticker,
            form_type=orm_obj.form_type
        )
        stmt.df = df
        return stmt

    def add(self, stmt: model.CombinedFinancialStatements) -> None:
        data = self._serialize(stmt)
        orm_obj = CombinedFinancialStatementsORM(**data)
        self.session.add(orm_obj)

    def add_many(self, stmts: Iterable[model.CombinedFinancialStatements]) -> None:
        mappings = [self._serialize(stmt) for stmt in stmts]
        self.session.bulk_insert_mappings(CombinedFinancialStatementsORM, mappings)

    def get(self, ticker: str, form_type: str) -> Optional[model.CombinedFinancialStatements]:
        stmt = select(CombinedFinancialStatementsORM).where(
            CombinedFinancialStatementsORM.ticker == ticker,
            CombinedFinancialStatementsORM.form_type == form_type
        )
        orm_obj = self.session.execute(stmt).scalar_one_or_none()

        if orm_obj is None:
            return None

        return self._deserialize_to_domain(orm_obj)

    def get_by_ticker(self, ticker: str) -> list[model.CombinedFinancialStatements]:
        stmt = select(CombinedFinancialStatementsORM).where(
            CombinedFinancialStatementsORM.ticker == ticker
        )
        orm_objs = self.session.execute(stmt).scalars().all()

        return [self._deserialize_to_domain(orm_obj) for orm_obj in orm_objs]

    def delete(self, ticker: str, form_type: str) -> None:
        stmt = select(CombinedFinancialStatementsORM).where(
            CombinedFinancialStatementsORM.ticker == ticker,
            CombinedFinancialStatementsORM.form_type == form_type
        )
        orm_obj = self.session.execute(stmt).scalar_one_or_none()

        if orm_obj:
            self.session.delete(orm_obj)
