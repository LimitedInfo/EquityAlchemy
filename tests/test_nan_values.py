import pytest
from backend.service_layer import uow, service
from backend.domain import model
import pandas as pd

def test_no_nan_values_in_revenue_and_cogs():
    """
    Tests that after consolidation, the 'Revenue' and 'COGS' rows
    in the final DataFrame for CMG do not contain any NaN values.
    """
    uow_instance = uow.SqlAlchemyUnitOfWork()

    # Using CMG as a test case, fetching 10-K
    result = service.get_consolidated_income_statements("CMG", uow_instance, "10-K", use_database=False)

    assert result is not None
    assert isinstance(result, model.CombinedFinancialStatements)

    df = result.df

    assert isinstance(df, pd.DataFrame)
    assert not df.empty

    # 1. Check if 'Revenue' and 'COGS' rows exist
    assert 'Revenue' in df.index, "The 'Revenue' row is missing from the final DataFrame."
    assert 'COGS' in df.index, "The 'COGS' row is missing from the final DataFrame."

    # 2. Check for NaN values in these specific rows
    revenue_has_nan = df.loc['Revenue'].isna().any()
    cogs_has_nan = df.loc['COGS'].isna().any()

    assert not revenue_has_nan, "The 'Revenue' row contains NaN values."
    assert not cogs_has_nan, "The 'COGS' row contains NaN values."
