import json
from collections import defaultdict

# Load the JSON data
with open('airbyte_connectors.json') as f:
    data = json.load(f)

# Initialize dictionaries to hold the counts
counts = defaultdict(lambda: {"successful_scraped": 0, "fail_scraped": 0, "not_scraped": 0})

# Iterate over the data
for item in data:
    # Get the airbyte_status
    airbyte_status = item['airbyte_status']

    # Check if the scraped_page_count key is present
    if 'scraped_page_count' in item:
        # Check if the scrape_fail_reason key is present
        if 'scrape_fail_reason' in item:
            if item['scrape_fail_reason'] == "All the content of the Documentation is on single page":
                counts[airbyte_status]['successful_scraped'] += 1
            else:
                counts[airbyte_status]['fail_scraped'] += 1
        else:
            counts[airbyte_status]['successful_scraped'] += 1
    else:
        counts[airbyte_status]['not_scraped'] += 1

# Print the counts
print(f"{'Airbyte Status':<30} {'Successful Scraped Count':<25} {'Successful Scraped %':<25} {'Fail Scraped Count':<25} {'Fail Scraped %':<25} {'Not Scraped Count':<25} {'Not Scraped %':<25} {'Total Connectors Count':<25}")
for airbyte_status, info in counts.items():
    total = sum(info.values())
    print(f"{airbyte_status:<30} {info['successful_scraped']:<25} {(info['successful_scraped'] / total) * 100:<25.2f} "
          f"{info['fail_scraped']:<25} {(info['fail_scraped'] / total) * 100:<25.2f} "
          f"{info['not_scraped']:<25} {(info['not_scraped'] / total) * 100:<25.2f}"
          f"{total:<25}")
