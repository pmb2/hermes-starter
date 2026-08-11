# Data Broker Source Aggregation

> How to download, normalize, and deduplicate multiple open-source data broker datasets into a single master list.

## Available Datasets

| Source | URL | Records | License |
|--------|-----|---------|---------|
| Optery | `https://raw.githubusercontent.com/optery/optery-data-brokers-directory/master/data/data-brokers.csv` | ~960 | Open |
| PersProtect | `https://raw.githubusercontent.com/Persprotect/data-broker-opt-out-list/main/data-brokers.csv` | ~500 | CC BY 4.0 |
| OptOutRights Foundation | `https://raw.githubusercontent.com/OptOutRights/brokerdirectory/refs/heads/main/data/brokers.csv` | ~1,000 | Open |

## Download Command

```bash
curl -sL "https://raw.githubusercontent.com/optery/optery-data-brokers-directory/master/data/data-brokers.csv" -o optery.csv
curl -sL "https://raw.githubusercontent.com/Persprotect/data-broker-opt-out-list/main/data-brokers.csv" -o persprotect.csv
curl -sL "https://raw.githubusercontent.com/OptOutRights/brokerdirectory/refs/heads/main/data/brokers.csv" -o optout.csv
```

## Merge & Deduplicate Script

This Python script reads all three CSVs, normalizes names and domains, deduplicates, and produces a merged CSV.

```python
import csv, re

def load_csv(path):
    """Load a CSV and return list of dicts with standardised keys."""
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(dict(row))
    return records

# Source mapping — each source uses different column names
SOURCES = {
    'optery': {
        'path': 'optery.csv',
        'fields': {'name': 'title', 'site': 'website', 'type': 'type',
                   'optout': 'opt_out_url', 'email': 'email', 'desc': 'description'}
    },
    'persprotect': {
        'path': 'persprotect.csv',
        'fields': {'name': 'Name', 'site': 'Website', 'type': 'Category',
                   'optout': 'Opt-Out Link', 'email': 'Privacy Email', 'desc': 'Notes'}
    },
    'optoutrights': {
        'path': 'optout.csv',
        'fields': {'name': 'Name', 'site': 'Website', 'type': 'Category',
                   'optout': 'Opt-Out URL', 'email': 'Privacy Support Email', 'desc': 'About'}
    }
}

def normalize(name):
    """Normalize company name for dedup matching."""
    n = name.lower().strip().rstrip(',.')
    n = re.sub(r'\b(inc|llc|ltd|corp|corporation|company|co|group|services|solutions|technologies|technology|media|data|analytics|intelligence|information)\b\.?', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    n = re.sub(r'[^a-z0-9 ]', '', n).strip()
    return n

def domain_key(site):
    """Extract root domain for dedup matching."""
    if not site:
        return ''
    m = re.search(r'https?://(?:www\.)?([^/]+)', site)
    return (m.group(1).lower().replace('www.', '') if m else site.lower().replace('www.', ''))

# Load all records with standardised fields
all_records = []
for source_key, source in SOURCES.items():
    records = load_csv(source['path'])
    f = source['fields']
    for r in records:
        all_records.append({
            'name': r.get(f['name'], '').strip(),
            'site': r.get(f['site'], '').strip(),
            'type': r.get(f['type'], '').strip(),
            'optout': r.get(f['optout'], '').strip(),
            'email': r.get(f['email'], '').strip(),
            'desc': r.get(f['desc'], '').strip()[:200],
            'source': source_key
        })

# Deduplicate using domain + normalized name
seen_names = {}
seen_domains = {}
merged = []

for record in all_records:
    key_name = normalize(record['name'])
    key_domain = domain_key(record['site'])
    
    matched = False
    if key_domain and key_domain in seen_domains:
        idx = seen_domains[key_domain]
        matched = True
    elif key_name and key_name in seen_names:
        idx = seen_names[key_name]
        matched = True
    
    if matched:
        existing = merged[idx]
        # Merge — prefer non-empty fields
        if not existing['optout'] and record['optout']:
            existing['optout'] = record['optout']
        if not existing['email'] and record['email']:
            existing['email'] = record['email']
        if not existing['desc'] and record['desc']:
            existing['desc'] = record['desc']
        existing['sources'] = list(set(existing.get('sources', [existing.get('source', '')]) + [record['source']]))
        continue
    
    record['sources'] = [record['source']]
    merged.append(record)
    if key_name:
        seen_names[key_name] = len(merged) - 1
    if key_domain:
        seen_domains[key_domain] = len(merged) - 1

# Write merged CSV
with open('merged_brokers.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Name', 'Type', 'Website', 'OptOut URL', 'Privacy Email', 'Description', 'Sources'])
    for b in merged:
        w.writerow([b['name'], b['type'], b['site'], b['optout'], b['email'],
                    b['desc'], ';'.join(b.get('sources', []))])

print(f"Merged {len(all_records)} records from {len(SOURCES)} sources into {len(merged)} unique brokers")
```

## Fields in Merged CSV

| Column | Description |
|--------|-------------|
| `Name` | Company/broker name (preferring longest available) |
| `Type` | Category: People Search, Marketing, B2B Lead Gen, Credit, etc. |
| `Website` | Company homepage |
| `OptOut URL` | Direct link to opt-out / privacy request form |
| `Privacy Email` | Dedicated privacy contact email |
| `Description` | Short description of what they do / data they hold |
| `Sources` | Semicolon-separated list of source datasets (optery;persprotect;optoutrights) |

## Typical Merge Results

- Optery: ~960 records
- PersProtect: ~500 records  
- OptOutRights: ~1,000 records
- Total unique after dedup: ~1,800-1,900

## Keeping Current

The broker landscape changes constantly:
- New brokers register with state databases quarterly
- Existing brokers get acquired (e.g., Publicis acquired Lotame in 2025)
- Some go out of business

Run the merge script at least once per year to refresh the master list.
