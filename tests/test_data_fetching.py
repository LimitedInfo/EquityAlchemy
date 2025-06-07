import pytest
from backend.service_layer import uow, service
from backend.domain import model

def test_aapl_filing_data_error():
    """
    Tests that the service correctly raises a ValueError when it encounters
    an old AAPL filing (from 2009) that is missing XBRL data.
    """
    uow_instance = uow.SqlAlchemyUnitOfWork()

    # We expect this call to fail because of the filing from 2009.
    with pytest.raises(ValueError, match="No data found for filing 0001193125-09-214859"):
        service.get_consolidated_income_statements("AAPL", uow_instance, "10-K", use_database=False)
