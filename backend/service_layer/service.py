from domain import model
from service_layer import uow
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Set
import os
import re
import time
from sec_api import MappingApi
from sqlalchemy import BigInteger
import csv
import os
from typing import Dict, List, Tuple


def get_price_time_series(ticker: str, days: int = 30, uow_instance: uow.AbstractUnitOfWork = None) -> model.PriceTimeSeries:
    from datetime import date, timedelta
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    with uow_instance as uow:
        price_points = uow.market_data.fetch_prices(ticker, start_date, end_date)
        return model.PriceTimeSeries(ticker, price_points)


def get_all_tickers(uow_instance: uow.AbstractUnitOfWork) -> list[str]:
    with uow_instance as uow:
        return uow.stmts.get_all_tickers()

def update_shares_outstanding(ticker: str, uow_instance: uow.AbstractUnitOfWork):
    with uow_instance as uow:
        try:
            db_company = uow.companies.get_by_ticker(ticker)

            if not db_company:
                try:
                    supplement_company_data(ticker, uow)
                    db_company = uow.companies.get_by_ticker(ticker)
                except (ValueError, RuntimeError) as e:
                    print(f"Could not supplement data for {ticker}: {e}")
                    return

            if not db_company:
                return

            cik = uow.sec_filings.get_cik_by_ticker(ticker)
            if not cik:
                return

            raw_filings = uow.sec_filings.get_filings(cik)
            db_company.filings = raw_filings

            if db_company.filings:
                latest_filing = db_company.get_filings_by_type('10-K')
                if latest_filing:
                    filing_to_load = latest_filing[0]
                    loaded_filing = load_data(filing_to_load, uow)
                    if loaded_filing and loaded_filing.cover_page:
                        shares_outstanding = loaded_filing.cover_page.entity_common_stock_shares_outstanding
                        if shares_outstanding:
                            db_company.shares_outstanding = shares_outstanding
                            uow.companies.update(db_company)
            uow.commit()
        except Exception as e:
            print(f"Could not update shares for {ticker}: {e}")
            uow.rollback()


def supplement_company_data(ticker: str, uow: uow.AbstractUnitOfWork) -> model.Company:
    """
    Fetches supplemental company data from the SEC API and persists it to the database.
    """
    with uow:
        # Check if the company already exists
        company = uow.companies.get_by_ticker(ticker)
        if company and company.sector:  # Assuming sector is one of the supplemented fields
            return company

        # Fetch supplemental data from SEC API
        mapping_api = MappingApi(os.getenv("SEC_API_KEY"))
        try:
            supplemental_data = mapping_api.resolve("ticker", ticker)[0]
        except Exception as e:
            raise RuntimeError(f"Failed to fetch supplemental data for {ticker}: {str(e)}")

        if not supplemental_data:
            raise ValueError(f"No supplemental data found for ticker: {ticker}")

        # Create or update the company object
        if company:
            # Update existing company
            company.name = supplemental_data.get('name', company.name)
            company.cik = supplemental_data.get('cik', company.cik)
            company.cusip = supplemental_data.get('cusip')
            company.exchange = supplemental_data.get('exchange')
            company.is_delisted = supplemental_data.get('isDelisted')
            company.category = supplemental_data.get('category')
            company.sector = supplemental_data.get('sector')
            company.industry = supplemental_data.get('industry')
            company.sic = supplemental_data.get('sic')
            company.sic_sector = supplemental_data.get('sicSector')
            company.sic_industry = supplemental_data.get('sicIndustry')
            company.fama_sector = supplemental_data.get('famaSector')
            company.fama_industry = supplemental_data.get('famaIndustry')
            company.currency = supplemental_data.get('currency')
            company.location = supplemental_data.get('location')
            company.sec_api_id = supplemental_data.get('id')
        else:
            # Create new company
            company = model.Company(
                name=supplemental_data.get('name'),
                ticker=supplemental_data.get('ticker'),
                cik=supplemental_data.get('cik'),
                shares_outstanding=None,
                cusip=supplemental_data.get('cusip'),
                exchange=supplemental_data.get('exchange'),
                is_delisted=supplemental_data.get('isDelisted'),
                category=supplemental_data.get('category'),
                sector=supplemental_data.get('sector'),
                industry=supplemental_data.get('industry'),
                sic=supplemental_data.get('sic'),
                sic_sector=supplemental_data.get('sicSector'),
                sic_industry=supplemental_data.get('sicIndustry'),
                fama_sector=supplemental_data.get('famaSector'),
                fama_industry=supplemental_data.get('famaIndustry'),
                currency=supplemental_data.get('currency'),
                location=supplemental_data.get('location'),
                sec_api_id=supplemental_data.get('id')
            )
            uow.companies.add(company)

        uow.commit()
        return company


def search_tickers(term: str, uow_instance: uow.AbstractUnitOfWork) -> list[str]:
    with uow_instance as uow:
        return uow.stmts.search_tickers(term)


def find_unique_companies_with_recent_10q_filings(api_key: str = None) -> List[Dict[str, str]]:
    if not api_key:
        api_key = os.getenv('SEC_API_KEY')
        if not api_key:
            raise ValueError("SEC_API_KEY environment variable is required or pass api_key parameter")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    unique_companies: Set[str] = set()
    companies_list: List[Dict[str, str]] = []

    from_index = 0
    size = 200

    while True:
        query_payload = {
            "query": f"formType:\"10-Q\" AND filedAt:[{start_date_str} TO {end_date_str}]",
            "from": str(from_index),
            "size": str(size),
            "sort": [{"filedAt": {"order": "desc"}}]
        }

        try:
            response = requests.post(
                "https://api.sec-api.io",
                json=query_payload,
                headers={"Authorization": api_key},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            filings = data.get("filings", [])

            if not filings:
                break

            for filing in filings:
                cik = filing.get("cik", "")
                ticker = filing.get("ticker", "")
                company_name = filing.get("companyName", "")

                company_key = f"{cik}:{ticker}:{company_name}"

                if company_key not in unique_companies:
                    unique_companies.add(company_key)
                    companies_list.append({
                        "cik": cik,
                        "ticker": ticker,
                        "company_name": company_name,
                        "filing_date": filing.get("filedAt", "")
                    })

            if len(filings) < size:
                break

            from_index += size

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to fetch SEC filings: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Error processing SEC API response: {str(e)}")

    return sorted(companies_list, key=lambda x: x["company_name"])


def get_company_by_ticker(ticker: str, uow_instance: uow.AbstractUnitOfWork) -> model.Company:
    with uow_instance as uow:
        company = uow.companies.get_by_ticker(ticker)
        if not company:
            raise ValueError(f"No company found for ticker: {ticker}")

        cik = uow.sec_filings.get_cik_by_ticker(ticker)
        if not cik:
            raise ValueError(f"No CIK found for ticker: {ticker}")

        raw_filings = uow.sec_filings.get_filings(cik)
        company.filings = raw_filings
        return company


def get_dataframe_from_ticker(ticker: str, repository_or_uow):
    if hasattr(repository_or_uow, 'sec_filings'):
        uow_instance = repository_or_uow
    else:
        with uow.UnitOfWork() as uow_instance:
            uow_instance.sec_filings = repository_or_uow
            company = get_company_by_ticker(ticker, uow_instance)
            if not company.filings:
                return pd.DataFrame()

            filing = company.filings[0]
            if filing.income_statement:
                return filing.income_statement.table
            return pd.DataFrame()

    company = get_company_by_ticker(ticker, uow_instance)
    if not company.filings:
        return pd.DataFrame()

    filing = company.filings[0]
    if filing.income_statement:
        return filing.income_statement.table
    return pd.DataFrame()


def format_dataframe_indexes(dataframe: pd.DataFrame, uow_instance: uow.AbstractUnitOfWork) -> pd.DataFrame:
    if dataframe.empty or not uow_instance.llm:
        return dataframe

    df = dataframe.copy()
    index_mapping = uow_instance.llm.make_index_readable(df.index.tolist())
    df.index = [index_mapping.get(idx, idx) for idx in df.index]

    return df


def join_financial_statements_with_mapping(financial_statements: list[pd.DataFrame], uow_instance: uow.AbstractUnitOfWork) -> pd.DataFrame:
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

    mapping_cache = {}

    for i, statement in enumerate(financial_statements[1:], 1):
        if not isinstance(statement, pd.DataFrame):
            raise TypeError("Expected a DataFrame object at index {0}, but got {1}".format(i, type(statement)))

        current_df = statement

        if current_df.empty:
            continue

        if uow_instance.llm:
            base_indices = tuple(sorted(financial_statements[0].index.tolist()))
            current_indices = tuple(sorted(current_df.index.tolist()))
            cache_key = (base_indices, current_indices)

            if cache_key in mapping_cache:
                print(f"Reusing cached mapping for dataframes with {len(base_indices)} and {len(current_indices)} indices")
                index_mapping = mapping_cache[cache_key]
            else:
                index_mapping = uow_instance.llm.map_dataframes(financial_statements[0], current_df)
                mapping_cache[cache_key] = index_mapping

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
                            if hasattr(mapped_df.loc[idx, col], '__len__') and len(mapped_df.loc[idx, col]) > 1:
                                print('indexer found more than one value for the same index, skipping...')
                                continue
                            result_df.loc[idx, col] = mapped_df.loc[idx, col]

    return result_df


def load_data(filing: model.Filing, uow_instance: uow.AbstractUnitOfWork) -> model.Filing:
    filing_data, cover_page = uow_instance.sec_filings.get_filing_data(
        filing.cik,
        filing.accession_number,
        filing.primary_document
    )
    if not filing_data:
        return None
    filing.data = filing_data
    filing.cover_page = cover_page
    return filing

def get_sec_filings_url(ticker: str = None, cik: str = None, form_type: str = '10-K', uow_instance: uow.AbstractUnitOfWork = None) -> str:
    if not cik:
        cik = uow_instance.sec_filings.get_cik_by_ticker(ticker)
    return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form_type}&dateb=&owner=include&count=40"

def get_consolidated_income_statements(ticker: str, uow_instance: uow.AbstractUnitOfWork, form_type: str = None, retrieve_from_database: bool = True, overwrite_database: bool = False) -> model.CombinedFinancialStatements:
    if retrieve_from_database:
        with uow_instance as uow:
            saved_statements = uow.stmts.get(ticker, form_type)

        if saved_statements:
            return saved_statements
        print('no statements found in database')

    company = get_company_by_ticker(ticker, uow_instance)

    if form_type == '10-Q':
        quarterly_filings_to_load = company.get_filings_by_type('10-Q')

        if not quarterly_filings_to_load:
            print('no 10-Q filings found')
            return None

        # get data for the first filing so we can get the number of years covered.
        load_data(quarterly_filings_to_load[0], uow_instance)
        quarterly_filings_to_load = company.select_filings_with_processing_pattern(quarterly_filings_to_load, '10-Q')

        # get all the data for the quarterly filings
        for filing in quarterly_filings_to_load:
            load_data(filing, uow_instance)
        # remove filings with no data
        quarterly_filings_to_load = [filing for filing in quarterly_filings_to_load if filing.data]

        years_covered_by_quarterly_filings = []
        for filing in quarterly_filings_to_load:
            years_covered_by_quarterly_filings.append(filing.cover_page.document_fiscal_year_focus)

        annual_filings_to_load = company.get_filings_by_type('10-K')
        # get all the data for the annual filings
        for filing in annual_filings_to_load:
            load_data(filing, uow_instance)
        # remove filings with no data
        annual_filings_to_load = [filing for filing in annual_filings_to_load if filing.data and len(filing.data) > 3]

        filtered_annual_filings = []
        for filing in annual_filings_to_load:
            if filing.cover_page.document_fiscal_year_focus in years_covered_by_quarterly_filings:
                filtered_annual_filings.append(filing)
        annual_filings_to_load = filtered_annual_filings

    elif form_type == '10-K':
        annual_filings_to_load = company.get_filings_by_type('10-K')

        if not annual_filings_to_load:
            print('no 10-K filings found')
            return None

        data_found = False
        for filing in annual_filings_to_load:
            load_data(filing, uow_instance)
            if filing.data:
                data_found = True
                break

        if not data_found:
            return None

        annual_filings_to_load = company.select_filings_with_processing_pattern(annual_filings_to_load, '10-K')

        for filing in annual_filings_to_load:
            load_data(filing, uow_instance)

            filing_url = uow_instance.sec_filings.get_filing_url(
                filing.cik,
                filing.accession_number,
                filing.primary_document
            )
            filing.filing_url = filing_url

        annual_filings_to_load = [filing for filing in annual_filings_to_load if filing.data and len(filing.data) > 3]

    else:
        raise ValueError(f"Invalid form type: {form_type}")


    if form_type == '10-Q':
        print('loading filings for {0}'.format(annual_filings_to_load + quarterly_filings_to_load))
        filings_to_load = annual_filings_to_load + quarterly_filings_to_load
    else:
        print('loading filings for {0}'.format(annual_filings_to_load))
        filings_to_load = annual_filings_to_load

    for filing in filings_to_load:
        try:
            print('loading filings for {0} {1}'.format(filing.cover_page.document_period_end_date, filing.form))
        except:
            print('no cover page for {0} {1}'.format(filing.accession_number, filing.form))


    if not filings_to_load:
        return model.CombinedFinancialStatements([], ticker, form_type)

    income_statements = [filing.income_statement for filing in filings_to_load if filing.income_statement]
    combined_statements = model.CombinedFinancialStatements(income_statements, filings_to_load, ticker, company.name, form_type)

    if uow_instance.llm and len(income_statements) > 1:
        tables = [stmt.table for stmt in income_statements if not stmt.table.empty]
        if len(tables) > 1:
            enhanced_df = join_financial_statements_with_mapping(tables, uow_instance)
            enhanced_df = format_dataframe_indexes(enhanced_df, uow_instance)
            combined_statements.df = enhanced_df
    elif uow_instance.llm:
        combined_statements.df = format_dataframe_indexes(combined_statements.df, uow_instance)

    if form_type == '10-Q':
        combined_statements.create_implied_missing_quarters()

    combined_statements.clean_dataframe()

    combined_statements.df = combined_statements.df[sorted(combined_statements.df.columns, key=lambda x: x.split(':')[0])]

    combined_statements.sec_filings_url = get_sec_filings_url(ticker=ticker, form_type=form_type, uow_instance=uow_instance)

    # update shares outstanding
    update_shares_outstanding(ticker, uow_instance)

    if overwrite_database:
        with uow_instance as uow:
            uow.stmts.delete(ticker, form_type)
            uow.stmts.add(combined_statements)
            uow.commit()
    elif retrieve_from_database:
        with uow_instance as uow:
            uow.stmts.add(combined_statements)
            uow.commit()

    return combined_statements


def process_new_filings_from_csv(csv_path: str = "filing_urls.csv", uow_instance: uow.AbstractUnitOfWork = None) -> Dict[str, any]:
    if uow_instance is None:
        uow_instance = uow.SqlAlchemyUnitOfWork()

    results = {
        "processed": 0,
        "updated": 0,
        "errors": 0,
        "details": []
    }

    if not os.path.exists(csv_path):
        results["details"].append(f"CSV file not found: {csv_path}")
        return results

    with open(csv_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        time.sleep(1)
        try:
            cik, accession_number, primary_document = _parse_sec_url(url)
            if not cik:
                results["details"].append(f"Could not parse CIK from URL: {url}")
                continue

            with uow_instance as uow:
                ticker = uow.sec_filings.get_ticker_by_cik(cik)
                print(ticker)
                if not ticker:
                    results["details"].append(f"Could not find ticker for CIK: {cik}")
                    continue

                existing_statements = uow.stmts.get(ticker, "10-K")

                filing = model.Filing(cik, "10-K", "", accession_number, primary_document, True)
                filing_data, cover_page = uow.sec_filings.get_filing_data(cik, accession_number, primary_document)

                if not filing_data:
                    results["details"].append(f"Could not fetch filing data for {ticker} ({cik})")
                    results["errors"] += 1
                    continue

                filing.data = filing_data
                filing.cover_page = cover_page

                if existing_statements:
                    new_filing_df = filing.income_statement.table if filing.income_statement else pd.DataFrame()

                    if not new_filing_df.empty:
                        existing_years = _extract_years_from_columns(existing_statements.df.columns)
                        new_years = _extract_years_from_columns(new_filing_df.columns)

                        if new_years and (not existing_years or max(new_years) > max(existing_years)):
                            combined_df = _merge_dataframes(existing_statements.df, new_filing_df, uow)
                            existing_statements.df = combined_df
                            existing_statements.source_filings.append(filing)
                            existing_statements.clean_dataframe()
                            existing_statements.df = _apply_display_formatting(existing_statements.df)

                            uow.stmts.delete(ticker, "10-K")
                            uow.stmts.add(existing_statements)
                            uow.commit()

                            results["updated"] += 1
                            results["details"].append(f"Updated {ticker} with newer data (years: {sorted(new_years)})")
                        else:
                            results["details"].append(f"No newer data found for {ticker} (existing: {sorted(existing_years) if existing_years else []}, new: {sorted(new_years) if new_years else []})")
                    else:
                        results["details"].append(f"No income statement data found for {ticker}")
                else:
                    new_statements = model.CombinedFinancialStatements(
                        [filing.income_statement] if filing.income_statement else [],
                        [filing],
                        ticker,
                        "10-K"
                    )

                    if not new_statements.df.empty:
                        new_statements.clean_dataframe()
                        new_statements.df = _apply_display_formatting(new_statements.df)

                        uow.stmts.add(new_statements)
                        uow.commit()

                        results["updated"] += 1
                        new_years = _extract_years_from_columns(new_statements.df.columns)
                        results["details"].append(f"Created new statements for {ticker} (years: {sorted(new_years) if new_years else []})")
                    else:
                        results["details"].append(f"No data to create statements for {ticker}")

                results["processed"] += 1

        except Exception as e:
            results["errors"] += 1
            results["details"].append(f"Error processing URL {url}: {str(e)}")

    return results


def _parse_sec_url(url: str) -> tuple[str, str, str]:
    pattern = r'https://www\.sec\.gov/Archives/edgar/data/(\d+)/(\d+)/([^/]+\.htm?)$'
    match = re.match(pattern, url)

    if match:
        cik = match.group(1).zfill(10)
        accession_number = match.group(2)
        primary_document = match.group(3)
        return cik, accession_number, primary_document

    return None, None, None


def _extract_years_from_columns(columns) -> List[int]:
    years = []
    for col in columns:
        try:
            if ':' in col:
                year_str = col.split(':')[0].split('-')[0]
                year = int(year_str)
                if 1900 <= year <= 2100:
                    years.append(year)
        except (ValueError, IndexError):
            continue
    return list(set(years))


def _get_ticker_from_cik(cik: str, sec_repo) -> str:
    ticker_url = "https://www.sec.gov/files/company_tickers.json"
    headers = {"User-Agent": os.getenv("USER_AGENT", "EquityAlchemyAI/1.0 (marottaandrew1@gmail.com)")}

    try:
        response = requests.get(ticker_url, headers=headers)
        response.raise_for_status()
        data = response.json()

        for item in data.values():
            if str(item['cik_str']).zfill(10) == cik:
                return item['ticker'].upper()
    except Exception as e:
        print(f"Error fetching ticker for CIK {cik}: {e}")

    return None


def _merge_dataframes(existing_df: pd.DataFrame, new_df: pd.DataFrame, uow) -> pd.DataFrame:
    if existing_df.empty:
        formatted_df = new_df.copy()
        return _apply_formatting(formatted_df)
    if new_df.empty:
        return existing_df.copy()

    result_df = existing_df.copy()

    if uow.llm:
        index_mapping = uow.llm.map_dataframes(existing_df, new_df)

        mapped_df = new_df.copy()
        new_index = []

        for idx in new_df.index:
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
    else:
        new_columns = [col for col in new_df.columns if col not in result_df.columns]
        if new_columns:
            for col in new_columns:
                for idx in result_df.index:
                    if idx in new_df.index:
                        result_df.loc[idx, col] = new_df.loc[idx, col]

    return _apply_formatting(result_df)


def _apply_formatting(df: pd.DataFrame) -> pd.DataFrame:
    return _apply_display_formatting(df)


def _apply_display_formatting(df: pd.DataFrame) -> pd.DataFrame:
    formatted_df = df.copy()

    for col in formatted_df.columns:
        formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) and abs(x) >= 1000 else x)

    return formatted_df


def _convert_to_millions(val):
    try:
        num = float(val)
        if abs(num) >= 10_000:
            return round(num / 1_000_000, 2)
        else:
            return num
    except (ValueError, TypeError):
        return val


def search_companies_from_csv(term: str) -> List[Dict[str, str]]:
    """
    Search companies by name or ticker from CSV file.
    Returns list of dicts with 'name' and 'ticker' keys.
    """
    if not term or len(term) < 2:
        return []

    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'all_companies_available.csv')

    if not os.path.exists(csv_path):
        print(f"CSV file not found at: {csv_path}")
        return []

    results = []
    term_lower = term.lower()

    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = row.get('name', '').strip()
                ticker = row.get('ticker', '').strip()

                # Search in both name and ticker (case insensitive)
                if (term_lower in name.lower() or
                    term_lower in ticker.lower()):
                    results.append({
                        'name': name,
                        'ticker': ticker
                    })

                # Limit results to prevent overwhelming the UI
                if len(results) >= 10:
                    break

    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []

    return results


def validate_company_exists(ticker_or_name: str) -> bool:
    """
    Validate that a company exists in the CSV by ticker or name.
    Returns True if found, False otherwise.
    """
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'all_companies_available.csv')

    if not os.path.exists(csv_path):
        return False

    search_term = ticker_or_name.strip().upper()

    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = row.get('name', '').strip().upper()
                ticker = row.get('ticker', '').strip().upper()

                if search_term == ticker or search_term == name:
                    return True

    except Exception as e:
        print(f"Error validating company: {e}")
        return False

    return False


def get_ticker_from_name_or_ticker(input_value: str) -> str:
    """
    Given a company name or ticker, return the ticker.
    Returns the input if it's already a ticker, or finds the ticker for a company name.
    """
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'all_companies_available.csv')

    if not os.path.exists(csv_path):
        return input_value.upper()

    search_term = input_value.strip()

    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = row.get('name', '').strip()
                ticker = row.get('ticker', '').strip()

                # If input matches ticker exactly (case insensitive), return the ticker
                if search_term.upper() == ticker.upper():
                    return ticker.upper()

                # If input matches name exactly (case insensitive), return the ticker
                if search_term.upper() == name.upper():
                    return ticker.upper()

    except Exception as e:
        print(f"Error getting ticker: {e}")
        return input_value.upper()

    return input_value.upper()
