
from brel import Filing
from brel.utils import open_edgar

# Loads Apples 10-Q filing from Q4 2023
filing = open_edgar(cik="320193", date="2023-12-30", filing_type="10-Q")

# Get all the facts in the filing. Take the first 3 facts.
facts = filing.get_all_facts()
first_3_facts = facts[:3]

# Print the facts.
print(first_3_facts)
