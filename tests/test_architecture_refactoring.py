import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend'))

import backend.service_layer.service as service
import backend.service_layer.uow as uow
import backend.domain.model as model


def test_get_company_by_ticker():
    print("Testing get_company_by_ticker...")

    with uow.FakeUnitOfWork() as uow_instance:
        company = service.get_company_by_ticker('aapl', uow_instance)

        assert company.name == 'aapl'
        assert company.ticker == 'aapl'
        assert company.cik == '0000320193'
        assert len(company.filings) == 3

        print(f"✓ Company created: {company.name} (CIK: {company.cik})")
        print(f"✓ Found {len(company.filings)} filings")


def test_filing_properties():
    print("\nTesting filing properties...")

    with uow.FakeUnitOfWork() as uow_instance:
        company = service.get_company_by_ticker('aapl', uow_instance)
        filing = company.filings[0]

        assert filing.cik == '0000320193'
        assert filing.form in ['10-K', '10-Q']
        assert filing.accession_number is not None

        print(f"✓ Filing: {filing.form} dated {filing.filing_date}")
        print(f"✓ Accession: {filing.accession_number}")


def test_filter_filings():
    print("\nTesting filter_filings...")

    with uow.FakeUnitOfWork() as uow_instance:
        company = service.get_company_by_ticker('aapl', uow_instance)

        ten_k_filings = company.filter_filings(form_type='10-K')
        ten_q_filings = company.filter_filings(form_type='10-Q')

        print(f"✓ Found {len(ten_k_filings)} 10-K filings")
        print(f"✓ Found {len(ten_q_filings)} 10-Q filings")

        assert len(ten_k_filings) > 0
        assert len(ten_q_filings) > 0


def test_get_dataframe_from_ticker():
    print("\nTesting get_dataframe_from_ticker...")

    with uow.FakeUnitOfWork() as uow_instance:
        df = service.get_dataframe_from_ticker('aapl', uow_instance)

        print(f"✓ DataFrame shape: {df.shape}")
        print(f"✓ DataFrame empty: {df.empty}")


def test_consolidated_income_statements():
    print("\nTesting get_consolidated_income_statements...")

    with uow.FakeUnitOfWork() as uow_instance:
        combined = service.get_consolidated_income_statements('aapl', uow_instance, form_type='10-K')

        assert isinstance(combined, model.CombinedFinancialStatements)
        assert combined.ticker == 'aapl'
        assert combined.form_type == '10-K'

        print(f"✓ Combined statements for {combined.ticker}")
        print(f"✓ Form type: {combined.form_type}")
        print(f"✓ DataFrame shape: {combined.df.shape}")


def test_domain_model_purity():
    print("\nTesting domain model purity...")

    filing = model.Filing('123', '10-K', '2024-01-01', 'acc123', 'doc.htm')
    company = model.Company('Test Corp', 'TEST', '123', [filing])

    assert filing.cik == '123'
    assert company.name == 'Test Corp'
    assert len(company.filings) == 1

    print("✓ Domain models can be created without repository dependencies")


if __name__ == "__main__":
    print("Running architecture refactoring tests...\n")

    try:
        test_domain_model_purity()
        test_get_company_by_ticker()
        test_filing_properties()
        test_filter_filings()
        test_get_dataframe_from_ticker()
        test_consolidated_income_statements()

        print("\n🎉 All tests passed! Architecture refactoring successful.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
