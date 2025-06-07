from typing import Dict, Any, Optional
from backend.domain.model import CoverPage, Filing


class FilingMapper:
    @staticmethod
    def map_cover_page_from_api(api_data: Dict[str, Any]) -> CoverPage:
        if not api_data:
            return None

        cover_page_data = api_data.get('CoverPage', {})
        if not cover_page_data:
            return None

        shares_outstanding = None
        shares_data = cover_page_data.get('EntityCommonStockSharesOutstanding')
        if shares_data and isinstance(shares_data, dict):
            shares_outstanding = int(shares_data.get('value', 0))

        return CoverPage(
            document_type=cover_page_data.get('DocumentType'),
            document_quarterly_report=cover_page_data.get('DocumentQuarterlyReport') == 'true',
            document_period_end_date=cover_page_data.get('DocumentPeriodEndDate'),
            document_transition_report=cover_page_data.get('DocumentTransitionReport') == 'true',
            entity_file_number=cover_page_data.get('EntityFileNumber'),
            entity_incorporation_state_country_code=cover_page_data.get('EntityIncorporationStateCountryCode'),
            entity_tax_identification_number=cover_page_data.get('EntityTaxIdentificationNumber'),
            entity_address_line1=cover_page_data.get('EntityAddressAddressLine1'),
            entity_address_city=cover_page_data.get('EntityAddressCityOrTown'),
            entity_address_country=cover_page_data.get('EntityAddressCountry'),
            entity_address_postal_code=cover_page_data.get('EntityAddressPostalZipCode'),
            city_area_code=cover_page_data.get('CityAreaCode'),
            local_phone_number=cover_page_data.get('LocalPhoneNumber'),
            security_12b_title=cover_page_data.get('Security12bTitle'),
            trading_symbol=cover_page_data.get('TradingSymbol'),
            security_exchange_name=cover_page_data.get('SecurityExchangeName'),
            entity_current_reporting_status=cover_page_data.get('EntityCurrentReportingStatus'),
            entity_interactive_data_current=cover_page_data.get('EntityInteractiveDataCurrent'),
            entity_filer_category=cover_page_data.get('EntityFilerCategory'),
            entity_small_business=cover_page_data.get('EntitySmallBusiness') == 'true',
            entity_emerging_growth_company=cover_page_data.get('EntityEmergingGrowthCompany') == 'true',
            entity_shell_company=cover_page_data.get('EntityShellCompany') == 'true',
            entity_registrant_name=cover_page_data.get('EntityRegistrantName'),
            entity_central_index_key=cover_page_data.get('EntityCentralIndexKey'),
            amendment_flag=cover_page_data.get('AmendmentFlag') == 'true',
            document_fiscal_year_focus=cover_page_data.get('DocumentFiscalYearFocus'),
            document_fiscal_period_focus=cover_page_data.get('DocumentFiscalPeriodFocus'),
            current_fiscal_year_end_date=cover_page_data.get('CurrentFiscalYearEndDate'),
            entity_common_stock_shares_outstanding=int(cover_page_data.get('EntityCommonStockSharesOutstanding', {}).get('value', 0)) if cover_page_data.get('EntityCommonStockSharesOutstanding') else None
        )

    @staticmethod
    def create_filing_with_cover_page(
        cik: str,
        form: str,
        filing_date: str,
        accession_number: str,
        primary_document: str,
        data: dict = None,
        filing_url: str = None,
        api_response: dict = None
    ) -> Filing:
        cover_page = None
        if api_response:
            cover_page = FilingMapper.map_cover_page_from_api(api_response)

        return Filing(
            cik=cik,
            form=form,
            filing_date=filing_date,
            accession_number=accession_number,
            primary_document=primary_document,
            data=data,
            filing_url=filing_url,
            cover_page=cover_page
        )
