import requests
from dotenv import load_dotenv
import model
from sec_api import XbrlApi
import os
import json

load_dotenv()


class SECFilingRepository():
    def __init__(self):
        # TODO: make this a variable
        self.headers = {"User-Agent": os.getenv("USER_AGENT")}

    def get_cik_by_ticker(self, ticker):
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
        filings_data = data.get("filings", {}).get("recent", {})
        forms = filings_data.get("form", [])
        dates = filings_data.get("filingDate", [])
        accessions = filings_data.get("accessionNumber", [])
        primary_docs = filings_data.get("primaryDocument", [])

        for form, filing_date, accession_number, primary_document in zip(forms, dates, accessions, primary_docs):
            filings.append(model.Filing(cik, form, filing_date, accession_number, primary_document, self))

        return filings

    def get_filing_data(self, cik, accession_number, primary_document):
        xbrlApi = XbrlApi(os.getenv("SEC_API_KEY"))
        data = xbrlApi.xbrl_to_json(htm_url=self.get_filing_url(cik, accession_number, primary_document))
        return data

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
                model.Filing('0000320193', '10-K', '2023-11-03', '0000320193-23-000108', 'aapl-20230930.htm', self),
                model.Filing('0000320193', '10-Q', '2023-08-03', '0000320193-23-000077', 'aapl-20230701.htm', self),
            ],
            '0000789019': [
                model.Filing('0000789019', '10-K', '2023-07-27', '0001564590-23-027480', 'msft-20230630.htm', self),
                model.Filing('0000789019', '10-Q', '2023-04-25', '0001564590-23-013716', 'msft-20230331.htm', self)
            ]
        }

        self.filing_data = {}

        file_mapping = {
            ('0000320193', '0000320193-23-000108', 'aapl-20230930.htm'): 'AAPL_10K_20241101_data.json',
            ('0000320193', '0000320193-23-000077', 'aapl-20230701.htm'): 'AAPL_10Q_20250131_data.json',
            ('0000789019', '0001564590-23-027480', 'msft-20230630.htm'): 'MSFT_10K_20240730_data.json',
            ('0000789019', '0001564590-23-013716', 'msft-20230331.htm'): 'MSFT_10Q_20250129_data.json'
        }

        test_data_dir = 'test_data'
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
        return self.filing_data.get(key, {})

    def get_filing_url(self, cik, accession_number, primary_document):
        # Return a fake URL for testing
        return f"https://fake-sec.gov/Archives/edgar/data/{int(cik)}/{accession_number}/{primary_document}"

    def _make_request(self, url, headers=None):
        # This method is not used in the fake repository
        # It's included to maintain the same interface as the real repository
        return {}
