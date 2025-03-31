import requests
from dotenv import load_dotenv
import model
from sec_api import XbrlApi
import os
import json
import google.generativeai as genai
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
                model.Filing('0000320193', '10-K', '2024-11-01', '0000320193-24-000123', 'aapl-20240928.htm', self),
                model.Filing('0000320193', '10-K', '2020-10-30', '0000320193-20-000096', 'aapl-20200926.htm', self),
                model.Filing('0000320193', '10-Q', '2025-01-31', '0000320193-25-000008', 'aapl-20241228.htm', self),
            ],
            '0000789019': [
                model.Filing('0000789019', '10-K', '2024-07-30', '0000950170-24-087843', 'msft-20240630.htm', self),
                model.Filing('0000789019', '10-Q', '2025-01-29', '0000950170-25-010491', 'msft-20241231.htm', self)
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

        # Configure the API key for all future calls
        import google.generativeai as genai
        genai.configure(api_key=self.gemini_api_key)
        # Return a generative model instance instead of the module itself
        return genai.GenerativeModel('gemini-1.5-flash')

    def map_dataframes(self, df1, df2, client=None, max_retries=2):
        import pandas as pd
        import traceback

        if client is None:
            client = self.gemini_client

        # First convert all numeric data to float for consistency
        df1_numeric = df1.apply(pd.to_numeric)
        df2_numeric = df2.apply(pd.to_numeric)

        # Print the index types for debugging
        print(f"\n=== DEBUG: DATAFRAME MAPPING ===")
        print(f"DF1 index types: {[idx for idx in df1.index]}")
        print(f"DF2 index types: {[idx for idx in df2.index]}")

        # Keep track of problematic indices that might have caused errors
        problematic_indices = []

        for attempt in range(max_retries + 1):  # +1 for the initial attempt
            try:
                # If this is a retry, modify the prompt to avoid problematic indices
                if attempt > 0:
                    print(f"Retry attempt {attempt} for mapping. Problematic indices: {problematic_indices}")
                    # Add information about problematic indices to the prompt
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
                {exclude_note}
                """

                print(f"Sending prompt to LLM with {len(list(df1_numeric.index))} rows from DF1 and {len(list(df2_numeric.index))} rows from DF2")

                # Correct the API call to use the appropriate method
                response = client.generate_content(
                    prompt,
                    generation_config={
                        'response_mime_type': 'application/json',
                    }
                )

                # Get the response text
                response_text = response.text
                print(f"Raw LLM response: {response_text[:200]}...") # Print first 200 chars to avoid huge logs

                # Clean up any code blocks or formatting
                if '```' in response_text:
                    # Extract content between code blocks
                    response_text = response_text.split('```')[1].strip()
                    print(f"After code block extraction: {response_text[:200]}...")
                if 'json' in response_text:
                    # Remove json language identifier
                    response_text = response_text.split('json')[1].strip()
                    print(f"After json identifier removal: {response_text[:200]}...")

                # Parse the JSON response
                mapping = json.loads(response_text)
                print(f"Parsed mapping: {mapping}")

                # Handle case where the mapping is a list of dictionaries instead of a single dictionary
                if isinstance(mapping, list):
                    print("Converting list of dictionaries to a single dictionary")
                    single_mapping = {}
                    for item in mapping:
                        if isinstance(item, dict):
                            single_mapping.update(item)
                    mapping = single_mapping
                    print(f"Converted mapping: {mapping}")

                # Validate the mapping thoroughly
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

                    # Add to valid mapping only if both source and target exist
                    valid_mapping[source_idx] = target_idx

                # If valid mapping is empty, retry
                if not valid_mapping:
                    raise ValueError("No valid mappings found in LLM response")

                # Success! Return the valid mapping
                print(f"Successfully created valid mapping with {len(valid_mapping)} entries")
                return valid_mapping

            except json.JSONDecodeError as json_err:
                print(f"Error parsing JSON (attempt {attempt+1}/{max_retries+1}): {json_err}")
                print(f"Response text: {response_text}")

                # If this is the last retry, return empty mapping
                if attempt == max_retries:
                    print("Maximum retries reached. Returning empty mapping.")
                    return {}
            except ValueError as val_err:
                print(f"Value error in mapping (attempt {attempt+1}/{max_retries+1}): {val_err}")

                # If this is the last retry, return empty mapping
                if attempt == max_retries:
                    print("Maximum retries reached. Returning empty mapping.")
                    return {}
            except Exception as e:
                print(f"Unexpected error in mapping (attempt {attempt+1}/{max_retries+1}): {e}")
                traceback.print_exc()

                # If this is the last retry, return empty mapping
                if attempt == max_retries:
                    print("Maximum retries reached. Returning empty mapping.")
                    return {}

        # If we get here, all retries failed
        return {}
