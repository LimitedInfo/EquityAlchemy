import backend.domain.model as model
import backend.service_layer.uow as uow
import pandas as pd


def  get_company_by_ticker(ticker: str, uow_instance: uow.AbstractUnitOfWork) -> model.Company:
    cik = uow_instance.sec_filings.get_cik_by_ticker(ticker)
    if not cik:
        raise ValueError(f"No CIK found for ticker: {ticker}")

    raw_filings = uow_instance.sec_filings.get_filings(cik)

    return model.Company(name=ticker, ticker=ticker, cik=cik, filings=raw_filings)


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

    for i, statement in enumerate(financial_statements[1:], 1):
        if not isinstance(statement, pd.DataFrame):
            raise TypeError("Expected a DataFrame object at index {0}, but got {1}".format(i, type(statement)))

        current_df = statement

        if current_df.empty:
            continue

        if uow_instance.llm:
            index_mapping = uow_instance.llm.map_dataframes(financial_statements[0], current_df)

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


def get_consolidated_income_statements(ticker: str, uow_instance: uow.AbstractUnitOfWork, form_type: str = None) -> model.CombinedFinancialStatements:
    company = get_company_by_ticker(ticker, uow_instance)

    if form_type == '10-Q':
        quarterly_filings_to_load = company.get_filings_by_type('10-Q')
        # get data for the first filing so we can get the number of years covered.
        filing_data, cover_page = uow_instance.sec_filings.get_filing_data(
            quarterly_filings_to_load[0].cik,
            quarterly_filings_to_load[0].accession_number,
            quarterly_filings_to_load[0].primary_document
        )
        quarterly_filings_to_load[0].data = filing_data
        quarterly_filings_to_load[0].cover_page = cover_page
        quarterly_filings_to_load = company.select_filings_with_processing_pattern(quarterly_filings_to_load, '10-Q')

        # get all the data for the quarterly filings
        for filing in quarterly_filings_to_load:
            filing_data, cover_page = uow_instance.sec_filings.get_filing_data(
                filing.cik,
                filing.accession_number,
                filing.primary_document
            )
            filing.data = filing_data
            filing.cover_page = cover_page
        # remove filings with no data
        quarterly_filings_to_load = [filing for filing in quarterly_filings_to_load if filing.data]

        years_covered_by_quarterly_filings = []
        for filing in quarterly_filings_to_load:
            years_covered_by_quarterly_filings.append(filing.cover_page.document_fiscal_year_focus)

        annual_filings_to_load = company.get_filings_by_type('10-K')
        # get all the data for the annual filings
        for filing in annual_filings_to_load:
            filing_data, cover_page = uow_instance.sec_filings.get_filing_data(
                filing.cik,
                filing.accession_number,
                filing.primary_document
            )
            filing.data = filing_data
            filing.cover_page = cover_page
        # remove filings with no data
        annual_filings_to_load = [filing for filing in annual_filings_to_load if filing.data]

        filtered_annual_filings = []
        for filing in annual_filings_to_load:
            if filing.cover_page.document_fiscal_year_focus in years_covered_by_quarterly_filings:
                filtered_annual_filings.append(filing)
        annual_filings_to_load = filtered_annual_filings

    elif form_type == '10-K':
            annual_filings_to_load = company.get_filings_by_type('10-K')
            filing_data, cover_page = uow_instance.sec_filings.get_filing_data(
                annual_filings_to_load[0].cik,
                annual_filings_to_load[0].accession_number,
                annual_filings_to_load[0].primary_document
            )
            annual_filings_to_load[0].data = filing_data
            annual_filings_to_load[0].cover_page = cover_page
            annual_filings_to_load = company.select_filings_with_processing_pattern(annual_filings_to_load, '10-K')

            annual_filings_to_load = [filing for filing in annual_filings_to_load if filing.data]

            for filing in annual_filings_to_load:
                filing_data, cover_page = uow_instance.sec_filings.get_filing_data(
                    filing.cik,
                    filing.accession_number,
                    filing.primary_document
                )
                filing.data = filing_data
                filing.cover_page = cover_page

                filing_url = uow_instance.sec_filings.get_filing_url(
                    filing.cik,
                    filing.accession_number,
                    filing.primary_document
                )
                filing.filing_url = filing_url

    else:
        raise ValueError(f"Invalid form type: {form_type}")


    if form_type == '10-Q':
        print('loading filings for {0}'.format(annual_filings_to_load + quarterly_filings_to_load))
        filings_to_load = annual_filings_to_load + quarterly_filings_to_load
    else:
        print('loading filings for {0}'.format(annual_filings_to_load))
        filings_to_load = annual_filings_to_load

    for filing in filings_to_load:
        print('loading filings for {0} {1}'.format(filing.cover_page.document_period_end_date, filing.form))


    if not filings_to_load:
        return model.CombinedFinancialStatements([], ticker, form_type)

    income_statements = [filing.income_statement for filing in filings_to_load if filing.income_statement]
    combined_statements = model.CombinedFinancialStatements(income_statements, filings_to_load, ticker, form_type)

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

    return combined_statements
