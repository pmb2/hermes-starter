# OSINT Data Sources Catalog — FOSS Only

## Property Intelligence

| Source | Data | Access | API Key | Coverage |
|--------|------|--------|---------|----------|
| **Regrid API** | Parcels, APN, ownership, valuation | REST | Free tier | US (partial) |
| **ArcGIS REST** | County assessor, parcels | REST | None | US counties |
| **Census TIGER** | Geocoding, boundaries | REST | None | US |
| **FEMA NFHL** | Flood zones, risk | REST | None | US |
| **County websites** | Tax records, deeds | Scrape | None | Per county |

## Person Enrichment

| Source | Data | Access | API Key | Coverage |
|--------|------|--------|---------|----------|
| **OpenCorporates** | Business affiliations, officers | REST | Free (optional) | Global |
| **CourtListener** | Civil/criminal cases | REST | Free | US Federal |
| **FEC API** | Political donations | REST | Free | US Federal |
| **OpenCage** | Geocoding + reverse | REST | Free tier | Global |
| **Census Bureau** | Demographics, income, age | REST | Free | US |
| **HIBP (HaveIBeenPwned)** | Breach data | REST | Free tier | Global |

## Social Media Recon

| Source | Data | Access | API Key | Coverage |
|--------|------|--------|---------|----------|
| **GitHub** | Public profile, repos | REST | None (rate limited) | Global |
| **Reddit** | Public profile, posts | REST | None (rate limited) | Global |
| **HackerNews** | Public profile, comments | REST | None | Global |
| **Gravatar** | Email → avatar/profile | REST | None | Global |
| **Google Dorks** | Search results | Manual | None | Global |

## Threat Intelligence

| Source | Data | Access | API Key | Coverage |
|--------|------|--------|---------|----------|
| **Shodan** | IP/port/service/CVE | REST | API key required | Global |
| **VirusTotal** | URL/file hash reputation | REST | API key required | Global |
| **SpiderFoot** | OSINT automation | Python pkg | Free | Global |
| **Ahmia.fi** | .onion search index | REST | None | Dark web |
| **Pastebin** | Paste search | REST/Scrape | None | Public pastes |
| **Telegram** | Public channel monitor | Bot API | Free | Global |

## Business Intelligence

| Source | Data | Access | API Key | Coverage |
|--------|------|--------|---------|----------|
| **SEC EDGAR** | Financial filings, ownership | REST | None | US public |
| **SAM.gov** | Government contracts | REST | Free | US Federal |
| **USPTO** | Trademarks, patents | REST | Free | US |
| **LittleSis** | Corporate relationships | Scrape | None | US |
| **OpenCorporates** | Entity registry, officers | REST | Free tier | Global |

## Email & Identity OSINT

| Source | Data | Access | API Key | Coverage |
|--------|------|--------|---------|----------|
| **Epieos** | Email → Google services, profile photos, names | Web | None (rate limited) | Global |
| **IntelTechniques** | Aggregated username/email/phone lookup | Web | None | Global |
| **Holehe** | Email registration on 100+ platforms | CLI (pip) | None | Global |
| **Sherlock** | Username search across 400+ sites | CLI (pip) | None | Global |

## Evidence Capture

| Source | Data | Access | API Key | Coverage |
|--------|------|--------|---------|----------|
| **Hunchly** | Browser capture, timestamps, HTML source | Chrome ext | Paid ($139/yr) | Global |
| **Wayback Machine** | Archived web pages | REST (CDX API) | None | Global |

## Geospatial Intelligence

| Source | Data | Access | API Key | Coverage |
|--------|------|--------|---------|----------|
| **Overpass Turbo** | OSM geographic feature queries | Web + API | None | Global |
| **OpenStreetMap** | Maps, POIs, addresses | REST | None | Global |
| **Nominatim** | Geocoding (OSM-based) | REST | None (rate limited) | Global
| **Census Geocoder** | Address → coordinates | REST | None | US |
| **USGS** | Earthquakes, topography | REST | None | US |
| **NRCan** | Geospatial (Canada) | REST | None | Canada |

## Facial Recognition (FOSS Models)

| Model | Type | Size | Accuracy | Library |
|-------|------|------|----------|---------|
| **Facenet** | Embedding | ~100MB | 99.6% LFW | DeepFace |
| **ArcFace** | Embedding | ~250MB | 99.8% LFW | DeepFace, InsightFace |
| **VGG-Face** | Embedding | ~550MB | 98.9% LFW | DeepFace |
| **SFace** | Embedding | ~40MB | 99.5% LFW | DeepFace |
| **OpenFace** | Embedding | ~100MB | 93.8% LFW | OpenFace |
| **RetinaFace** | Detection | ~20MB | 99.5% WIDER | InsightFace |
| **Haar Cascade** | Detection | ~1MB | Basic | OpenCV |
| **FAISS** | Vector search | — | — | FAISS (Meta) |
