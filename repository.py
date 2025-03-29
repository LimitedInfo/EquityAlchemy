import requests
from dotenv import load_dotenv
import model
from sec_api import XbrlApi
import os

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
