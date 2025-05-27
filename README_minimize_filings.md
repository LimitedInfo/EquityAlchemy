# Minimize Quarterly Filings for Maximum Data Coverage

This module provides functionality to optimize the selection of quarterly SEC filings (10-Q forms) to minimize API calls while maximizing data coverage across all available years and quarters.

## Problem Statement

Companies file quarterly reports (10-Q) that often contain Year-over-Year (YoY) metrics covering 2-3 or more years of data. Instead of fetching data from every filing, we can strategically select a minimal set of filings that covers all available quarters across all years.

## Solution

The `minimize_quarterly_filings_for_maximum_coverage()` function uses a greedy algorithm to:

1. Start with the newest filing (most likely to have the most recent data)
2. Iteratively select additional filings that provide the maximum number of new quarters not yet covered
3. Continue until all available quarters are covered or no more beneficial filings remain

## Usage

```python
from backend.domain.model import Company, Filing
from backend.domain.minimize_maximize_data_from_filings import (
    minimize_quarterly_filings_for_maximum_coverage,
    minimize_quarterly_filings_by_year_sampling,
    get_quarterly_coverage_summary
)

# Approach 1: Complete coverage (covers all quarters)
selected_filings_complete = minimize_quarterly_filings_for_maximum_coverage(company)

# Approach 2: Year sampling (covers all quarters for selected years)
selected_filings_sampling = minimize_quarterly_filings_by_year_sampling(company, year_interval=2)

# Get detailed coverage information
summary = get_quarterly_coverage_summary(company, selected_filings_sampling)
print(f"Reduced from {summary['total_filings_available']} to {summary['selected_filings_count']} filings")
print(f"Coverage: {summary['coverage_percentage']:.1f}%")
```

## Example Results

For a company with 25 quarterly filings spanning 2017-2025:

### Complete Coverage Approach:
- **Input**: 25 quarterly filings
- **Output**: 9 optimally selected filings
- **Reduction**: 64% fewer API calls needed
- **Coverage**: 100% of all available quarters

### Year Sampling Approach (every other year):
- **Input**: 25 quarterly filings
- **Output**: 5 optimally selected filings
- **Reduction**: 80% fewer API calls needed
- **Coverage**: ~56% of all quarters (but covers all 4 quarters for selected years)
- **Years covered**: 2024, 2022, 2020, 2018, 2016

### Year Sampling Approach (every third year):
- **Input**: 25 quarterly filings
- **Output**: 3 optimally selected filings
- **Reduction**: 88% fewer API calls needed
- **Coverage**: ~33% of all quarters (but covers all 4 quarters for selected years)
- **Years covered**: 2024, 2021, 2018

## Quarter Mapping Logic

The function maps filing dates to the quarters they likely contain data for:

- **April filings**: Previous year Q1, Q2, Q3, Q4
- **July filings**: Current year Q1 + Previous year Q2, Q3, Q4
- **October filings**: Current year Q1, Q2 + Previous year Q3, Q4
- **December+ filings**: Current year Q1, Q2, Q3 + Previous year Q4

## Functions

### `minimize_quarterly_filings_for_maximum_coverage(company: Company) -> List[Filing]`

Returns the minimal set of quarterly filings needed to cover all available quarters. This approach prioritizes complete coverage over filing reduction.

**Parameters:**
- `company`: Company object containing quarterly filings

**Returns:**
- List of Filing objects sorted by date (newest first)

### `minimize_quarterly_filings_by_year_sampling(company: Company, year_interval: int = 2) -> List[Filing]`

Returns filings that cover all quarters for selected years at specified intervals. This approach prioritizes filing reduction over complete coverage by sampling every Nth year.

**Parameters:**
- `company`: Company object containing quarterly filings
- `year_interval`: Sample every Nth year (default: 2 for every other year)

**Returns:**
- List of Filing objects sorted by date (newest first)

**Example:**
- `year_interval=1`: Every year (same as complete coverage)
- `year_interval=2`: Every other year (2024, 2022, 2020, etc.)
- `year_interval=3`: Every third year (2024, 2021, 2018, etc.)

### `get_quarterly_coverage_summary(company: Company, selected_filings: List[Filing] = None) -> dict`

Provides detailed analysis of the filing selection and coverage.

**Returns dictionary with:**
- `total_filings_available`: Total number of quarterly filings
- `selected_filings_count`: Number of filings in optimized selection
- `total_quarters_available`: Total quarters that can be covered
- `quarters_covered`: Number of quarters covered by selection
- `coverage_percentage`: Percentage of quarters covered
- `selected_filing_dates`: List of selected filing dates
- `covered_quarters`: List of quarters covered (e.g., ['2023-Q1', '2023-Q2'])
- `missed_quarters`: List of quarters not covered

## Testing

Run the unit tests:
```bash
python -m pytest backend/tests/test_minimize_filings.py -v
```

Run the example demonstration:
```bash
python test_minimize_filings.py
```

## Benefits

1. **Reduced API Calls**: Significantly fewer requests to SEC filing APIs
2. **Faster Processing**: Less data to download and process
3. **Complete Coverage**: Still captures all available quarterly data
4. **Cost Optimization**: Lower API usage costs for rate-limited services
