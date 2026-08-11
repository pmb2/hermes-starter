# PDF Generation Reference

## WeasyPrint + pydyf Version Compatibility

**The fix:** WeasyPrint 60.x requires pydyf **0.8.0** specifically.

```
pip install pydyf==0.8.0
```

### The error
```
TypeError: PDF.__init__() takes 1 positional argument but 3 were given
```

### Root cause
- pydyf 0.11.0 changed `PDF.__init__()` signature from `(self, version, identifier)` to just `(self)`
- pydyf 0.12.1 also has the `(self)`-only signature
- WeasyPrint 60.x internally calls `pydyf.PDF(version, identifier)` — two positional args
- Only pydyf 0.8.0 accepts both version and identifier parameters

### Detection
```python
import pydyf, inspect
sig = inspect.signature(pydyf.PDF.__init__)
# Should show: (self, version=b'1.7', identifier=None)
```

## Template System Architecture

### Problem
CSS uses `{` and `}` for rules (e.g., `@page { size: ... }`), which conflicts with Python's `str.format()` which interprets `{var}` as replacement fields.

### Solution
Use `__VAR__` style placeholders and `.replace()` substitution instead of `.format()`.

**Template file:** `templates/ebook_template.html`  
**Code in:** `scripts/generate_ebook.py`

```python
def _fill_template(template: str, replacements: dict) -> str:
    result = template
    for key, value in replacements.items():
        result = result.replace(f"__{key}__", str(value))
    return result
```

### Template variables naming convention
- All caps with underscores between words
- Wrapped in `__` on both sides in the HTML
- Examples: `__PAGE_SIZE__`, `__COVER_TITLE__`, `__BODY_FONT_SIZE__`

### Generated product structure
```
products/{product-slug}/
├── config.json         # Product content + style config
├── cover.png           # Generated cover image (1200×1800px default)
├── product.pdf         # Generated PDF (WeasyPrint)
└── publishing_manifest.json  # Gumroad/Etsy/Payhip metadata
```

## Fontconfig on Windows
The "Fontconfig error: Cannot load default config file" warnings are cosmetic on Windows. The PDF still generates correctly. To suppress:
```
# Create empty fontconfig conf
mkdir -p ~/AppData/Local/fontconfig
touch ~/AppData/Local/fontconfig/fonts.conf
```
Or install fontconfig via MSYS2. But neither is necessary — PDFs work fine without it.

## Known Pitfalls

1. **first generation with a new config.json**: If the template has `$` or backtick characters in content, they pass through `.replace()` correctly, but content strings from JSON may contain JSON-escaped characters that need decoding.

2. **Cover has guides overlay**: `cover_generator.py --guides` creates a _guides.png overlay for checking composition. Don't upload the guide version as the product cover.

3. **Page count estimation**: The report in publishing_manifest estimates pages from section count × 50. Actual page count depends on content density. Expect 50-80% of the estimate for standard content.

4. **Marketing content script name field**: `marketing_content.py --config` reads from config's `name` key, but `generate_ebook.py` configs use `title`. Use CLI args instead: `--product-name "Title" --niche "niche" --price XX`.
