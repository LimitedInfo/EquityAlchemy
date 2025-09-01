#!/usr/bin/env python3
"""
Script to supplement tickers with insufficient balance sheet information.

This script:
1. Gets tickers with balance sheet data having less than 4 indexes from the database
2. For each ticker, loads the most recent filing
3. Extracts balance sheet data from the filing
4. Stores the balance sheet data in the database using add_or_update_balance_sheet
"""

import sys
import os
sys.path.append('/Users/andrew/EquityAlchemy/backend')

from domain import model
from service_layer import uow, service
import time
from typing import List, Dict, Optional
import traceback


def get_all_tickers_from_db(uow_instance: uow.AbstractUnitOfWork) -> List[str]:
    """Get all unique tickers from the database."""
    with uow_instance as uow_ctx:
        return uow_ctx.stmts.get_all_tickers()


def get_tickers_with_insufficient_balance_sheet_data(uow_instance: uow.AbstractUnitOfWork) -> List[str]:
    """Get tickers where balance_sheet_data has less than 4 indexes."""
    with uow_instance as uow_ctx:
        return uow_ctx.stmts.get_tickers_with_insufficient_balance_sheet_data()


def process_balance_sheet_for_ticker(ticker: str, uow_instance: uow.AbstractUnitOfWork) -> Dict[str, any]:
    """
    Process balance sheet data for a single ticker.
    
    Returns:
        Dict with processing results including success status and details
    """
    result = {
        'ticker': ticker,
        'success': False,
        'message': '',
        'balance_sheet_periods': 0,
        'form_type': None
    }
    
    try:
        print(f"Processing {ticker}...")
        
        # Get company and filings
        try:
            company = service.get_company_by_ticker(ticker, uow_instance)
        except ValueError as e:
            result['message'] = f"Company not found: {str(e)}"
            return result
        
        # Try to get the most recent filing (any type) - this approach worked in balance_sheet.ipynb
        try:
            most_recent_filing = company.get_most_recent_filing()
            form_type = most_recent_filing.form if most_recent_filing else None
        except Exception:
            result['message'] = "No filings found for ticker"
            return result
        
        if not most_recent_filing:
            result['message'] = "No recent filing found"
            return result
        
        result['form_type'] = form_type
        
        # Load filing data if not already loaded
        if not most_recent_filing.data:
            service.load_data(most_recent_filing, uow_instance)
        
        if not most_recent_filing.data:
            result['message'] = "Failed to load filing data"
            return result
        
        # Extract balance sheet
        balance_sheet = most_recent_filing.balance_sheet
        if not balance_sheet:
            result['message'] = "No balance sheet found in filing"
            return result
        
        if balance_sheet.table.empty:
            result['message'] = "Balance sheet table is empty"
            return result
        
        result['balance_sheet_periods'] = len(balance_sheet.table.columns)
        
        # Debug: print balance sheet info
        print(f"   Balance sheet shape: {balance_sheet.table.shape}")
        print(f"   Balance sheet index (first 10): {list(balance_sheet.table.index[:10])}")
        print(f"   Balance sheet columns: {list(balance_sheet.table.columns)}")
        
        # Create combined statements object for balance sheet (following balance_sheet.ipynb approach)
        # Pass the balance sheet as a single statement, not the filing itself
        combined_statements = model.CombinedFinancialStatements(
            [balance_sheet], 
            [most_recent_filing], 
            ticker, 
            company.name, 
            form_type
        )
        
        # Set the balance sheet DataFrame directly from the balance sheet table
        combined_statements.balance_sheet_df = balance_sheet.table
        
        # Store in database
        with uow_instance as uow_ctx:
            uow_ctx.stmts.add_or_update_balance_sheet(combined_statements)
        
        result['success'] = True
        result['message'] = f"Successfully processed balance sheet with {result['balance_sheet_periods']} periods"
        
        print(f"✓ {ticker}: {result['message']}")
        
    except Exception as e:
        result['message'] = f"Error: {str(e)}"
        print(f"✗ {ticker}: {result['message']}")
        # Print full traceback for debugging
        print(f"   Traceback: {traceback.format_exc()}")
    
    return result


def supplement_all_balance_sheets(batch_size: int = 10, delay_seconds: float = 1.0) -> Dict[str, any]:
    """
    Supplement tickers with insufficient balance sheet information (less than 4 indexes).
    
    Args:
        batch_size: Number of tickers to process before taking a break
        delay_seconds: Delay between batches to avoid overwhelming the system
    
    Returns:
        Summary statistics of the processing
    """
    print("=== Starting Balance Sheet Supplementation ===")
    
    uow_instance = uow.SqlAlchemyUnitOfWork()
    
    # Get tickers with insufficient balance sheet data
    print("Fetching tickers with insufficient balance sheet data from database...")
    all_tickers = get_tickers_with_insufficient_balance_sheet_data(uow_instance)
    
    print(f"Found {len(all_tickers)} tickers to process")
    
    # Process results tracking
    results = {
        'total_tickers': len(all_tickers),
        'successful': 0,
        'failed': 0,
        'details': [],
        'errors': []
    }
    
    # Process tickers in batches
    for i, ticker in enumerate(all_tickers):
        try:
            result = process_balance_sheet_for_ticker(ticker, uow_instance)
            results['details'].append(result)
            
            if result['success']:
                results['successful'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'ticker': ticker,
                    'error': result['message']
                })
            
            # Take a break every batch_size tickers
            if (i + 1) % batch_size == 0:
                print(f"Processed {i + 1}/{len(all_tickers)} tickers. Taking a {delay_seconds}s break...")
                time.sleep(delay_seconds)
                
        except KeyboardInterrupt:
            print(f"\nProcessing interrupted by user at ticker {i + 1}/{len(all_tickers)}")
            break
        except Exception as e:
            print(f"Unexpected error processing {ticker}: {str(e)}")
            results['failed'] += 1
            results['errors'].append({
                'ticker': ticker,
                'error': f"Unexpected error: {str(e)}"
            })
    
    # Print summary
    print("\n=== Processing Summary ===")
    print(f"Total tickers processed: {results['successful'] + results['failed']}/{results['total_tickers']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    
    if results['errors']:
        print(f"\nFirst 10 errors:")
        for error in results['errors'][:10]:
            print(f"  {error['ticker']}: {error['error']}")
    
    # Show success rate by form type
    form_type_stats = {}
    for detail in results['details']:
        if detail['success']:
            form_type = detail['form_type'] or 'Unknown'
            form_type_stats[form_type] = form_type_stats.get(form_type, 0) + 1
    
    if form_type_stats:
        print(f"\nSuccessful by form type:")
        for form_type, count in sorted(form_type_stats.items()):
            print(f"  {form_type}: {count}")
    
    return results


def test_single_ticker(ticker: str) -> None:
    """Test processing for a single ticker (useful for debugging)."""
    print(f"=== Testing single ticker: {ticker} ===")
    
    uow_instance = uow.SqlAlchemyUnitOfWork()
    result = process_balance_sheet_for_ticker(ticker, uow_instance)
    
    print(f"Result: {result}")
    
    # Try to retrieve the balance sheet data
    try:
        with uow_instance as uow_ctx:
            stmt = uow_ctx.stmts.get_balance_sheet(ticker, result.get('form_type', '10-K'))
            if stmt and stmt.balance_sheet_df is not None:
                print(f"Balance sheet retrieved successfully!")
                print(f"Shape: {stmt.balance_sheet_df.shape}")
                print(f"Columns: {list(stmt.balance_sheet_df.columns)}")
                print(f"Index (first 10): {list(stmt.balance_sheet_df.index[:10])}")
            else:
                print("Failed to retrieve balance sheet from database")
    except Exception as e:
        print(f"Error retrieving balance sheet: {str(e)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Supplement tickers with balance sheet data')
    parser.add_argument('--test-ticker', type=str, help='Test processing for a single ticker')
    parser.add_argument('--batch-size', type=int, default=10, help='Number of tickers to process per batch')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay in seconds between batches')
    
    args = parser.parse_args()
    
    if args.test_ticker:
        test_single_ticker(args.test_ticker)
    else:
        results = supplement_all_balance_sheets(batch_size=args.batch_size, delay_seconds=args.delay)
