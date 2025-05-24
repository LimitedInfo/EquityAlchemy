import backend.domain.model as model
import backend.adapters.repository as repository
import pandas as pd


def get_dataframe_from_ticker(ticker: str, repository) -> pd.DataFrame:
    company = model.Company(ticker, ticker, repository)
    filing = company.filings[0]
    return filing.income_statement.table


def format_dataframe_indexes(dataframe: pd.DataFrame, llm_repository) -> pd.DataFrame:
    if dataframe.empty:
        return dataframe

    df = dataframe.copy()
    index_mapping = llm_repository.make_index_readable(df.index.tolist())
    df.index = [index_mapping.get(idx, idx) for idx in df.index]

    return df

def get_consolidated_income_statements(ticker: str, sec_repository, llm_repository=None, form_type=None):
    company = model.Company(ticker, ticker, sec_repository)

    # Get the minimal set of filings that cover all years
    filtered_filings = company.filter_filings(form_type=form_type)

    if not filtered_filings:
        return pd.DataFrame()

    income_statements = [filing.income_statement for filing in filtered_filings]
    combined_statements = model.CombinedIncomeStatements(income_statements, ticker, form_type)

    if llm_repository and len(income_statements) > 1:
        tables = [stmt.table for stmt in income_statements if not stmt.table.empty]
        if len(tables) > 1:
            enhanced_df = company.join_financial_statements(tables, llm_repository)
            if llm_repository:
                enhanced_df = format_dataframe_indexes(enhanced_df, llm_repository)
            combined_statements.df = enhanced_df
    elif llm_repository:
        combined_statements.df = format_dataframe_indexes(combined_statements.df, llm_repository)

    return combined_statements
