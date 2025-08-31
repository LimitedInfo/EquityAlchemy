#!/usr/bin/env python3

import os
import sys
from dotenv import load_dotenv
import adapters.repository as repo
from service_layer import uow as uow_mod
from service_layer import service as svc
from service_layer import forecasting
import time

print("Testing forecasting module...")
print("=" * 60)

print("1. Testing imports...")
print(f"   - forecasting module imported: {forecasting is not None}")
print(f"   - Default methods available: {hasattr(forecasting, 'DEFAULT_FORECASTING_METHODS')}")
print(f"   - Functions available:")
print(f"     - forecast_prophet: {hasattr(forecasting, 'forecast_prophet')}")
print(f"     - forecast_ratio: {hasattr(forecasting, 'forecast_ratio')}")
print(f"     - forecast_growth_rate: {hasattr(forecasting, 'forecast_growth_rate')}")
print(f"     - create_forecast_columns: {hasattr(forecasting, 'create_forecast_columns')}")
print(f"     - plot_forecast: {hasattr(forecasting, 'plot_forecast')}")
print(f"     - display_forecast_sample: {hasattr(forecasting, 'display_forecast_sample')}")

print("\n2. Testing with actual data...")
try:
    uow = uow_mod.SqlAlchemyUnitOfWork()
    print("   - UoW created successfully")
    
    cfs = svc.get_consolidated_income_statements(
        ticker="AAPL", 
        uow_instance=uow, 
        form_type="10-K", 
        retrieve_from_database=True, 
        overwrite_database=False
    )
    print("   - Financial statements retrieved successfully")
    
    forecasted_df = forecasting.create_forecast_columns(
        cfs.df, 
        forecasting.DEFAULT_FORECASTING_METHODS,
        forecasting.DEFAULT_CALCULATED_METHODS,
        periods=5,
        verbose=True
    )
    
    print(f"\n   - Forecast created successfully!")
    print(f"   - Original columns: {len(cfs.df.columns)}")
    print(f"   - New columns with forecast: {len(forecasted_df.columns)}")
    print(f"   - Forecast columns: {[col for col in forecasted_df.columns if 'Forecast' in col]}")
    
    print("\n3. Testing display function...")
    display_df = forecasting.display_forecast_sample(forecasted_df)
    
    print("\n✅ All tests passed successfully!")
    
except Exception as e:
    print(f"\n❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Testing complete!")