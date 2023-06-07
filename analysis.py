import json
from collections import defaultdict

# Load the JSON data
with open('airbyte_connectors.json') as f:
    data = json.load(f)

# Initialize dictionaries to hold the counts
counts = defaultdict(lambda: {"greater_than_one": 0, "one_or_less": 0, "not_scraped": 0})

# Iterate over the data
for item in data:
    # Get the airbyte_status
    airbyte_status = item['airbyte_status']

    # Check if the scraped_page_count key is present
    if 'scraped_page_count' in item:
        # Check if the scraped_page_count is > 1
        if item['scraped_page_count'] > 1:
            counts[airbyte_status]['greater_than_one'] += 1
        else:
            counts[airbyte_status]['one_or_less'] += 1
    else:
        counts[airbyte_status]['not_scraped'] += 1

# Print the counts
print(f"{'Airbyte Status':<30} {'>1 Count':<10} {'>1 %':<10} {'<=1 Count':<10} {'<=1 %':<10} {'Not Scraped Count':<15} {'Not Scraped %':<15}")
for airbyte_status, info in counts.items():
    total = sum(info.values())
    print(f"{airbyte_status:<30} {info['greater_than_one']:<10} {(info['greater_than_one'] / total) * 100:<10.2f} "
          f"{info['one_or_less']:<10} {(info['one_or_less'] / total) * 100:<10.2f} "
          f"{info['not_scraped']:<15} {(info['not_scraped'] / total) * 100:<15.2f}")
