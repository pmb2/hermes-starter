# Credential Pattern Reference

Regex patterns for scanning repos during sanitization. Organized by severity.

## 🔴 HIGH — Real Credentials

### API Keys
```
sk-[a-zA-Z0-9]{20,}           # OpenAI-style keys
gh[pousr]_[a-zA-Z0-9]{36}     # GitHub tokens (all prefixes)
hf_[a-zA-Z0-9]{20,}           # Hugging Face tokens
glpat-[a-zA-Z0-9_-]{20,}      # GitLab tokens
xox[bpars]-[a-zA-Z0-9]{10,}   # Slack tokens (all prefixes)
pk-[a-zA-Z0-9]{40,}           # Starkware/Solana keys
Bearer\s+[a-zA-Z0-9_-]{20,}   # Bearer tokens
token:\s*['\"]?[a-zA-Z0-9_-]{20,}  # Generic token: prefix
api_key:\s*['\"]?[a-zA-Z0-9_-]{20,}  # Generic api_key: prefix
```

### Gmail App Passwords
```
GMAIL_SENDER_PASSWORD:\s*\S+        # YAML config
ACCOUNT\d_PASSWORD\s*=\s*['\"]?[^'\"]+['\"]?  # Python scripts
[a-z]{4}\s[a-z]{4}\s[a-z]{4}\s[a-z]{4}  # Spaced format (gmail 16-char)
```

### Email Addresses (personal)
```
[a-z0-9._%+-]+@gmail\.com
[a-z0-9._%+-]+@[a-z0-9.-]+\.(com|org|net|io|gov)
```

### Nostr Private Keys
```
"secret_key":\s*"[a-f0-9]{64}"        # Hex format
nsec[a-z0-9]{50,}                      # Bech32 format (nsec1...)
```

### Phone Numbers
```
\+1?\d{10,11}                          # US numbers with +1
\d{3}[-.]?\d{3}[-.]?\d{4}             # Various formats
```

## 🟡 MEDIUM — Personal Identifiers

### Windows Absolute Paths
```
C:\\Users\\[^\\]+                     # Backslash format
C:/Users/[^/]+                        # Forward slash format
/c/Users/[^/]+                        # MSYS format
```

### Discord IDs
```
[0-9]{17,19}                          # 17-19 digit snowflake IDs
```

### Personal File Servers / IPs
```
192\.168\.\d{1,3}\.\d{1,3}           # Internal IPs
10\.\d{1,3}\.\d{1,3}\.\d{1,3}       # Private IPs
home\.local|localhost:\d+             # Local references
```

## 🟢 LOW — Contextual Info

### Personal Names
```
the operator|the operator\s|UserRealName            # Common replacements
```

### Company/Org Names
```
youraccount|youraccount2       # Specific to user
```

### Directory Names (for full path prefixes)
```
\\Documents\\github\\                 # Repo structure
\\AppData\\Local\\hermes\\            # Hermes paths
```

## Usage

```python
import re

CREDENTIAL_PATTERNS = [
    (re.compile(r'sk-[a-zA-Z0-9]{20,}'), 'OpenAI API key'),
    (re.compile(r'gh[pousr]_[a-zA-Z0-9]{36}'), 'GitHub token'),
    (re.compile(r'GMAIL_SENDER_PASSWORD:\s*\S+'), 'Gmail app password'),
    (re.compile(r'ACCOUNT\d_PASSWORD\s*='), 'Gmail password in script'),
    (re.compile(r'[0-9]{17,19}'), 'Discord ID'),
    (re.compile(r'C:\\\\Users\\\\\w+|C:/Users/\w+'), 'Windows path'),
]

def scan_file(filepath):
    content = open(filepath, encoding='utf-8', errors='ignore').read()
    findings = []
    for pat, label in CREDENTIAL_PATTERNS:
        for m in pat.finditer(content):
            findings.append((m.start(), label, m.group()[:40]))
    return findings
```
