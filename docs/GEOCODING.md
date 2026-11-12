# Geocoding Korean Addresses

This document explains how the geocoding system works for converting Korean addresses (도로명주소 and 지번주소) into map coordinates.

## Overview

The `firm-geocode` command (`src/firm_analyzer/core/geocoding.py`) converts firm addresses from the CSV into latitude/longitude coordinates for map display. It supports two modes:

1. **API-based geocoding** using geopy with Nominatim (OpenStreetMap)
2. **Fallback coordinates** using hardcoded regional coordinates

## Installation

Install the required package:

```bash
pip install geopy
```

Or install all requirements:

```bash
pip install -r ../requirements.txt
```

## Usage

Run the script from the `firm_summary` directory:

```bash
cd firm_summary
uv run firm-geocode
```

### Interactive Mode (Default)

When prompted, choose:
- **y** - Use geopy API for accurate geocoding (slow but accurate)
- **n** - Use fallback coordinates only (fast but less accurate)

### Command-Line Arguments

For automated/batch processing, use command-line arguments:

```bash
# Use API geocoding
uv run firm-geocode --use-api

# Use fallback only
uv run firm-geocode --no-api
```

### Environment Variable

Alternatively, set an environment variable:

```bash
# Use API geocoding
USE_GEOCODING_API=1 uv run firm-geocode

# Use fallback only
USE_GEOCODING_API=0 uv run firm-geocode
```

## Geocoding Methods

### 1. API-based Geocoding (Recommended)

Uses geopy with Nominatim (OpenStreetMap) to geocode addresses:

**Pros:**
- More accurate coordinates
- Works with full Korean addresses (도로명주소 and 지번주소)
- Results are cached for subsequent runs

**Cons:**
- Slower (rate limited to 1 request per second)
- Requires internet connection
- May not work well for incomplete addresses

**Example:**
```python
from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="firm_websearch_geocoder")
location = geolocator.geocode("서울특별시 강남구 테헤란로 152")
print(location.latitude, location.longitude)
```

### 2. Fallback Coordinates

Uses hardcoded coordinates for major regions when API is unavailable:

**Pros:**
- Fast (no API calls)
- Works offline
- Reliable fallback for incomplete addresses

**Cons:**
- Less accurate (uses regional center coordinates)
- Requires maintenance of coordinate database

**Hierarchy:**
1. Exact district match (e.g., "서울특별시 강남구")
2. Partial match (e.g., "서울", "강남")
3. Jurisdiction fallback (e.g., "서울", "대전.충남")

## Caching System

Geocoding results are cached in `data/geocode_cache.json` to avoid repeated API calls:

```json
{
  "서울특별시 강남구 테헤란로 152|서울": {
    "lat": 37.5042,
    "lng": 127.0475
  }
}
```

The cache key format is: `{address}|{jurisdiction}`

## Alternative Korean Geocoding Services

For production use, consider these specialized Korean address geocoding services:

### geocoder-kr
- **Best for:** Offline geocoding with local database
- **Pros:** Fast, accurate for Korean addresses
- **Cons:** Requires downloading 12GB data package

```bash
pip install geocoder-kr
```

### korean-geocoding (Naver API)
- **Best for:** Production with API quota management
- **Pros:** Optimized for Korean addresses, supports batch requests
- **Cons:** Requires Naver API key

```bash
pip install korean-geocoding
```

### Kakao Maps API
- **Best for:** Free tier with reasonable quotas
- **Pros:** Excellent Korean address support, free tier available
- **Cons:** Requires API key, rate limits apply

```python
import requests
headers = {"Authorization": "KakaoAK YOUR_API_KEY"}
response = requests.get(
    "https://dapi.kakao.com/v2/local/search/address.json",
    params={"query": "서울특별시 강남구 테헤란로 152"},
    headers=headers
)
```

### VWorld API (Government)
- **Best for:** Public sector, academic use
- **Pros:** Government-supported, accurate
- **Cons:** Requires API key registration

## Switching to a Different Geocoding Service

To use a different geocoding service, modify the `geocode_with_nominatim()` function in `src/firm_analyzer/core/geocoding.py`:

```python
def geocode_with_api(address, api_service, max_retries=3):
    """
    Replace Nominatim with your preferred geocoding service.
    """
    # Example: Kakao API
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    response = requests.get(
        "https://dapi.kakao.com/v2/local/search/address.json",
        params={"query": address},
        headers=headers
    )
    data = response.json()
    if data['documents']:
        return float(data['documents'][0]['y']), float(data['documents'][0]['x'])
    return None, None
```

## Troubleshooting

### "geopy not installed" warning
Install geopy: `pip install geopy`

### Slow geocoding
- Normal - Nominatim limits requests to 1 per second
- Results are cached, so subsequent runs are much faster
- Consider using geocoder-kr with local database for faster results

### Inaccurate coordinates
- Check if the address in CSV is complete
- Incomplete addresses fall back to regional coordinates
- Consider using Kakao or Naver API for better Korean address support

### Cache is too large
- The cache file grows with each unique address
- Safe to delete `data/geocode_cache.json` to start fresh
- Cache helps avoid re-geocoding on subsequent runs

## Contributing

When adding new hardcoded coordinates to `REGION_COORDS` or `JURISDICTION_COORDS`, please:
1. Use reliable sources for coordinates
2. Add comments explaining the location
3. Test with actual addresses from that region
