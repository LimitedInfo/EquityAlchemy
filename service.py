import model
import repository
import pandas as pd

def get_dataframe_from_ticker(ticker: str, repository) -> pd.DataFrame:
    company = model.Company(ticker, ticker, repository)
    filing = company.filings[0]
    return filing.income_statement.table

def get_consolidated_financials(ticker: str, sec_repository, llm_repository=None, form_type=None, statement_type='income_statement'):
    """
    Get consolidated financial data for a ticker by filtering filings and joining their statements

    Args:
        ticker (str): Company ticker symbol
        sec_repository: Repository for SEC filing data
        llm_repository: Repository for LLM operations (optional)
        form_type (str, optional): Filter by filing form type (e.g., '10-K', '10-Q')
        statement_type (str): The type of statement to filter on ('income_statement', 'balance_sheet', 'cash_flow')

    Returns:
        pd.DataFrame: Consolidated financial statements with all available periods
    """
    company = model.Company(ticker, ticker, sec_repository)

    # Get the minimal set of filings that cover all years
    filtered_filings = company.filter_filings(form_type=form_type, statement_type=statement_type)

    if not filtered_filings:
        return pd.DataFrame()

    if len(filtered_filings) == 1:
        statement = getattr(filtered_filings[0], statement_type)
        return statement.table

    # Extract the financial statement tables from each filing
    print(getattr(filtered_filings[0], statement_type))
    financial_statements = [getattr(filing, statement_type).table for filing in filtered_filings]

    # Join financial statements using LLM to map between different naming conventions
    return company.join_financial_statements(financial_statements, llm_repository=llm_repository)


if __name__ == "__main__":
    df = get_consolidated_financials("AAPL", repository.SECFilingRepository(), llm_repository=repository.LLMRepository(), form_type='10-K')
