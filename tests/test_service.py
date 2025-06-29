import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import backend.domain.model as model
import backend.service_layer.service as service
import backend.service_layer.uow as uow

class TestFinancialServices:
    def test_get_consolidated_income_statements(self):
        with uow.FakeUnitOfWork() as uow_instance:
            result = service.get_consolidated_income_statements(
                'aapl',
                uow_instance,
                form_type='10-K'
            )

            assert isinstance(result, model.CombinedFinancialStatements)
            assert result.ticker == 'aapl'
            assert result.form_type == '10-K'
            assert not result.df.empty

    def test_get_company_by_ticker(self):
        with uow.FakeUnitOfWork() as uow_instance:
            company = service.get_company_by_ticker('aapl', uow_instance)

            assert company.name == 'aapl'
            assert company.ticker == 'aapl'
            assert company.cik == '0000320193'
            assert len(company.filings) > 0

    def test_get_dataframe_from_ticker(self):
        with uow.FakeUnitOfWork() as uow_instance:
            df = service.get_dataframe_from_ticker('aapl', uow_instance)

            assert isinstance(df, pd.DataFrame)
