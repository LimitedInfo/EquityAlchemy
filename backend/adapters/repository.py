import abc
import requests

from dotenv import load_dotenv
from domain import model
from adapters.filing_mapper import FilingMapper
from sec_api import XbrlApi, QueryApi
import os
import json
import google.generativeai as genai
import traceback
import pandas as pd
from typing import Optional, Iterable
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from adapters.orm import CombinedFinancialStatementsORM, StockPriceORM, SignificantMoveORM
from typing import Protocol
from datetime import date
from decimal import Decimal
from domain import (
    StockTicker, PricePoint, SignificantMove, StockPriceSeries,
    PriceRepository, SignificantMoveRepository
)


load_dotenv()

class SECFilingRepository():
    def __init__(self):
        self.headers = {"User-Agent": os.getenv("USER_AGENT")}
        self.queryApi = QueryApi(os.getenv("SEC_API_KEY"))

    def get_cik_by_ticker(self, ticker):
        ticker_file_path = os.path.join(os.path.dirname(__file__), 'company_tickers.json')

        with open(ticker_file_path, 'r') as f:
            data = json.load(f)

        for item in data.values():
            if item['ticker'].lower() == ticker.lower():
                cik = str(item['cik_str']).zfill(10)
                return cik
        return None

    def get_ticker_by_cik(self, cik):
        ticker_file_path = os.path.join(os.path.dirname(__file__), 'company_tickers.json')

        with open(ticker_file_path, 'r') as f:
            data = json.load(f)

        cik_normalized = str(cik).zfill(10)
        cik_unpadded = str(cik).lstrip('0') or '0'

        for item in data.values():
            item_cik = str(item['cik_str']).zfill(10)
            if item_cik == cik_normalized or str(item['cik_str']) == cik_unpadded:
                return item['ticker']
        return None

    def get_all_filings_in_period(self, start_date: date, end_date: date, form_type):

        search_parameters = {
        "query": "<PLACEHOLDER>", # will be set during runtime
        "from": "0", # will be incremented by 50 during runtime
        "size": "50",
        "sort": [{ "filedAt": { "order": "desc" } }]
        }

        # open the file to store the filing URLs
        log_file = open("filing_urls.csv", "a")

        search_parameters["from"] = 0

        form_type_query = f'formType:"{form_type}"'
        date_range_query = f"filedAt:[{start_date} TO {end_date}]"
        search_parameters["query"] = form_type_query + " AND " + date_range_query

        print("Starting filing search for: ", search_parameters["query"])

        # paginate through results by increasing "from" parameter
        # until all results are fecthed and no more filings are returned
        # uncomment line below to fetch all 10,000 filings per month
        # for from_param in range(0, 9950, 50):
        url_strings = []
        cik_list = []
        for from_param in range(0, 100000, 50):
            search_parameters["from"] = from_param

            response = self.queryApi.get_filings(search_parameters)

            # stop if no more filings are returned
            if len(response["filings"]) == 0:
                break

            # for each filing, get the URL of the filing
            # set in the dict key "linkToFilingDetails"
            urls_list = list(
                map(lambda x: x["linkToFilingDetails"], response["filings"])
            )

            # transform the list of URLs into a single string by
            # joining all list elements, add a new-line character between each element
            urls_string = "\n".join(urls_list) + "\n"

            for url in urls_list:
                cik = url.split('/data/')[1].split('/')[0]
                cik_list.append(cik)

            url_strings.append(urls_string)

        log_file.write("\n".join(url_strings))
        log_file.close()
        return url_strings, cik_list

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
        result = {}

        for attr_name, attr_value in vars(stmt).items():
            if attr_name.startswith('_'):
                continue

            if attr_name == 'df':
                json_str = attr_value.to_json(orient="split", date_format="iso")
                result['data'] = json.loads(json_str)
            elif attr_name in ['financial_statements', 'source_filings']:
                continue
            else:
                try:
                    json.dumps(attr_value)
                    result[attr_name] = attr_value
                except (TypeError, ValueError):
                    result[attr_name] = str(attr_value) if attr_value is not None else None

        if not hasattr(stmt, 'sec_filings_url'):
            result['sec_filings_url'] = None

        return result

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


class PostgresPriceRepository(PriceRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_series(self, ticker: StockTicker, start_date: date, end_date: date) -> Optional[StockPriceSeries]:
        stmt = select(StockPriceORM).where(
            and_(
                StockPriceORM.ticker == ticker.symbol,
                StockPriceORM.date >= start_date,
                StockPriceORM.date <= end_date
            )
        ).order_by(StockPriceORM.date)

        results = self.session.execute(stmt).scalars().all()

        if not results:
            return None

        price_points = []
        for orm_obj in results:
            price_point = PricePoint(
                date=orm_obj.date,
                price=Decimal(str(orm_obj.price)),
                market_reference_price=Decimal(str(orm_obj.market_reference_price))
            )
            price_points.append(price_point)

        return StockPriceSeries(ticker, price_points)

    def add_many(self, points: list[PricePoint], ticker: StockTicker) -> None:
        for point in points:
            existing = self.session.execute(
                select(StockPriceORM).where(
                    and_(
                        StockPriceORM.ticker == ticker.symbol,
                        StockPriceORM.date == point.date
                    )
                )
            ).scalar_one_or_none()

            if not existing:
                orm_obj = StockPriceORM(
                    ticker=ticker.symbol,
                    date=point.date,
                    price=float(point.price),
                    market_reference_price=float(point.market_reference_price)
                )
                self.session.add(orm_obj)

        self.session.commit()

    def get_latest_date(self, ticker: StockTicker) -> Optional[date]:
        stmt = select(StockPriceORM.date).where(
            StockPriceORM.ticker == ticker.symbol
        ).order_by(StockPriceORM.date.desc()).limit(1)

        result = self.session.execute(stmt).scalar_one_or_none()
        return result.date() if result else None


class PostgresSignificantMoveRepository(SignificantMoveRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, move: SignificantMove) -> None:
        orm_obj = SignificantMoveORM(
            ticker=move.ticker.symbol,
            occurred_at=move.occurred_at,
            pct_change=float(move.pct_change),
            catalyst=move.catalyst
        )
        self.session.add(orm_obj)
        self.session.commit()

        move.id = str(orm_obj.id)

    def add_many(self, moves: list[SignificantMove]) -> None:
        for move in moves:
            existing = self.session.execute(
                select(SignificantMoveORM).where(
                    and_(
                        SignificantMoveORM.ticker == move.ticker.symbol,
                        SignificantMoveORM.occurred_at == move.occurred_at
                    )
                )
            ).scalar_one_or_none()

            if not existing:
                orm_obj = SignificantMoveORM(
                    ticker=move.ticker.symbol,
                    occurred_at=move.occurred_at,
                    pct_change=float(move.pct_change),
                    catalyst=move.catalyst
                )
                self.session.add(orm_obj)
                move.id = str(orm_obj.id)

        self.session.commit()

    def list_between(self, ticker: StockTicker, start_date: date, end_date: date) -> list[SignificantMove]:
        stmt = select(SignificantMoveORM).where(
            and_(
                SignificantMoveORM.ticker == ticker.symbol,
                SignificantMoveORM.occurred_at >= start_date,
                SignificantMoveORM.occurred_at <= end_date
            )
        ).order_by(SignificantMoveORM.occurred_at)

        results = self.session.execute(stmt).scalars().all()

        moves = []
        for orm_obj in results:
            move = SignificantMove(
                id=str(orm_obj.id),
                ticker=ticker,
                occurred_at=orm_obj.occurred_at,
                pct_change=Decimal(str(orm_obj.pct_change)),
                catalyst=orm_obj.catalyst
            )
            moves.append(move)

        return moves

    def update_catalyst(self, move_id: str, catalyst: str) -> None:
        stmt = select(SignificantMoveORM).where(SignificantMoveORM.id == move_id)
        result = self.session.execute(stmt).scalar_one_or_none()

        if result:
            result.catalyst = catalyst
            self.session.commit()


class FakePriceRepository(PriceRepository):
    def __init__(self):
        self.price_data = {}

    def get_series(self, ticker: StockTicker, start_date: date, end_date: date) -> Optional[StockPriceSeries]:
        ticker_data = self.price_data.get(ticker.symbol, [])

        filtered_points = [
            point for point in ticker_data
            if start_date <= point.date.date() <= end_date
        ]

        if not filtered_points:
            return None

        return StockPriceSeries(ticker, filtered_points)

    def add_many(self, points: list[PricePoint], ticker: StockTicker) -> None:
        if ticker.symbol not in self.price_data:
            self.price_data[ticker.symbol] = []

        existing_dates = {point.date.date() for point in self.price_data[ticker.symbol]}

        for point in points:
            if point.date.date() not in existing_dates:
                self.price_data[ticker.symbol].append(point)

        self.price_data[ticker.symbol].sort(key=lambda p: p.date)

    def get_latest_date(self, ticker: StockTicker) -> Optional[date]:
        ticker_data = self.price_data.get(ticker.symbol, [])
        if not ticker_data:
            return None
        return max(point.date.date() for point in ticker_data)


class FakeSignificantMoveRepository(SignificantMoveRepository):
    def __init__(self):
        self.moves = []
        self.next_id = 1

    def add(self, move: SignificantMove) -> None:
        move.id = str(self.next_id)
        self.next_id += 1
        self.moves.append(move)

    def add_many(self, moves: list[SignificantMove]) -> None:
        for move in moves:
            existing = any(
                m.ticker == move.ticker and m.occurred_at == move.occurred_at
                for m in self.moves
            )
            if not existing:
                self.add(move)

    def list_between(self, ticker: StockTicker, start_date: date, end_date: date) -> list[SignificantMove]:
        return [
            move for move in self.moves
            if (move.ticker == ticker and
                start_date <= move.occurred_at.date() <= end_date)
        ]

    def update_catalyst(self, move_id: str, catalyst: str) -> None:
        for move in self.moves:
            if move.id == move_id:
                move.catalyst = catalyst
                break
