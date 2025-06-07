import pytest
import pandas as pd
from backend.service_layer import uow, service
from backend.domain import model

def test_revenue_and_cogs_are_standardized_and_ordered():
    """
    Tests that for a real company (CMG), we get a DataFrame that has
    'Revenue' and 'COGS' as the first two metrics in the index.
    """
    uow_instance = uow.SqlAlchemyUnitOfWork()

    # Using CMG as a test case, fetching 10-K
    result_df = service.get_consolidated_income_statements("CMG", uow_instance, "10-K", use_database=False)

    assert result_df is not None
    assert isinstance(result_df, model.CombinedFinancialStatements)

    df = result_df.df

    assert isinstance(df, pd.DataFrame)
    assert not df.empty

    # 1. Check if 'Revenue' and 'COGS' are in the index
    assert 'Revenue' in df.index
    assert 'COGS' in df.index

    # 2. Check if they are the first two items in the index
    assert df.index[0] == 'Revenue'
    assert df.index[1] == 'COGS'
