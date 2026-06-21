# Korean Maps Setup Guide

This guide explains how to set up accurate geocoding for Korean addresses in the firm viewer map.

## Problem

The CSV data contains incomplete Korean addresses (e.g., "광주광역시 북구 첨단과기로") without specific street numbers. This causes the map to show only approximate locations using regional coordinates instead of exact building locations.

## Solution

Use Kakao Maps API for accurate geocoding of Korean addresses. Kakao Maps is optimized for Korean address formats and can handle both:

- **도로명주소 (Road Name Address)**: Modern system (e.g., "서울특별시 강남구 테헤란로 123")
- **지번주소 (Lot Number Address)**: Traditional system (e.g., "서울특별시 강남구 역삼동 123-45")

## Setup Instructions

### Step 1: Get a Kakao REST API Key (Free)

1. Visit [Kakao Developers](https://developers.kakao.com/)
2. Sign up or log in
3. Go to "내 애플리케이션" (My Applications)
4. Click "애플리케이션 추가하기" (Add Application)
5. Fill in the application details:
   - App Name: "Firm WebSearch" (or any name you prefer)
   - Company: Your organization name
6. After creating the app, go to the app settings
7. Under "앱 키" (App Keys) section, copy the **REST API 키** (REST API Key)

### Step 2: Set the Environment Variable

#### Option A: Using .env file (Recommended)

Add to your `.env` file in the project root:

```bash
KAKAO_REST_API_KEY=your_rest_api_key_here
```

#### Option B: Using export command

```bash
export KAKAO_REST_API_KEY=your_rest_api_key_here
```

Add this to your `~/.bashrc` or `~/.zshrc` to make it permanent.

### Step 3: Test the API Connection

Run the test script to verify your API key works:

```bash
cd firm_summary
python test_kakao_geocoding.py
```

Expected output:
```
======================================================================
Testing Kakao Maps API Geocoding
======================================================================

Testing 5 sample addresses...

1. Testing: 광주광역시 북구 첨단과기로
   ✓ Geocoded successfully!
   Type: 도로명주소
   Full Address: 광주광역시 북구 첨단과기로
   Coordinates: (35.228xxx, 126.843xxx)

...

======================================================================
Results: 5/5 addresses geocoded successfully
======================================================================
✓ All tests passed! Kakao Maps API is working correctly.
```

### Step 4: Regenerate Map Data

Run the geocoding script to process all addresses:

```bash
cd firm_summary
python generate_firms_data.py
```

The script will:
1. Read addresses from the CSV file
2. Use Kakao Maps API to get exact coordinates
3. Cache results in `data/geocode_cache.json`
4. Generate `webapp/static/js/firms_data.js` with accurate coordinates

This process takes time as it geocodes ~1,900 addresses. Results are cached, so subsequent runs will be much faster.

### Step 5: View the Updated Map

Start the web application:

```bash
cd webapp
python app.py
```

Open http://localhost:5000/firm-viewer to see the map with accurate locations.

## Understanding the Geocoding Process

### Geocoding Priority

The script tries multiple methods in order:

1. **Check Cache**: If address was geocoded before, use cached result
2. **Kakao Maps API**: Best for Korean addresses (requires API key)
3. **Nominatim (OSM)**: Fallback for international addresses
4. **Regional Coordinates**: Final fallback using hardcoded city/district centers

### Address Formats

#### Complete Address (Best)
```
서울특별시 강남구 테헤란로 152 (역삼동)
```
- City: 서울특별시
- District: 강남구
- Road: 테헤란로
- Building number: 152
- Dong (administrative): 역삼동

#### Incomplete Address (Common in dataset)
```
서울특별시 강남구 테헤란로
```
- Missing building number
- Kakao API will return the road location or best match

#### Jibun Address
```
서울특별시 강남구 역삼동 737
```
- City: 서울특별시
- District: 강남구
- Dong: 역삼동
- Lot number: 737

### Cache Management

Geocoding results are cached in `data/geocode_cache.json`:

```json
{
  "광주광역시 북구 첨단과기로|광주.전남": {
    "lat": 35.228xxx,
    "lng": 126.843xxx,
    "method": "Kakao"
  }
}
```

To force re-geocoding (e.g., to use a different API or update coordinates):
```bash
rm data/geocode_cache.json
python firm_summary/generate_firms_data.py
```

## Troubleshooting

### API Key Not Working

**Error**: "Authentication failed - check your KAKAO_REST_API_KEY"

**Solutions**:
- Verify you're using the REST API key (not JavaScript key or Admin key)
- Check there are no extra spaces or quotes in the key
- Ensure the key is active in Kakao Developers console

### Rate Limiting

**Error**: API returns 429 status code

**Solution**: 
- Kakao Maps API has rate limits on the free tier
- The script automatically retries with delays
- If persistent, consider adding longer delays in the code or splitting the geocoding into batches

### No Results for Address

**Warning**: "No results found for: [address]"

**Causes**:
- Address is too incomplete or incorrect
- Script will fall back to regional coordinates

**Solutions**:
- Check if the address exists in reality
- Some research institutes have internal roads not in public databases
- Consider manually correcting addresses in the CSV

### Coordinates Still Approximate

**Possible causes**:
1. API key not set - script falls back to regional coordinates
2. Cache contains old data - delete `geocode_cache.json` and regenerate
3. `firms_data.js` not updated - make sure to regenerate after geocoding
4. Browser cache - do a hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

## API Usage Limits

Kakao Maps API free tier limits:
- **Search**: 300,000 requests/day
- **Rate**: Reasonable usage (no specific limit documented)

For this project (~1,900 addresses):
- Initial geocoding: ~1,900 API calls (one-time)
- Subsequent runs: 0 calls (uses cache)
- Well within free tier limits

## Privacy and Security

- Store API key in `.env` file (already in `.gitignore`)
- Never commit API keys to version control
- Kakao API keys can be restricted by domain/IP in the developer console
- Cache file can be committed (contains only public address coordinates)

## Alternative: Without API Key

If you don't want to use Kakao API, the system will:
- Use regional coordinates for approximate locations
- Add random offsets to prevent marker overlap
- Still functional but less accurate

To use fallback only:
```bash
python generate_firms_data.py --no-api
```

## Support

For issues with:
- **Kakao API**: Visit [Kakao Developers](https://developers.kakao.com/)
- **This tool**: Open an issue on GitHub
- **Address data**: Check the source CSV file format

## References

- [Kakao Local API Documentation (Korean)](https://developers.kakao.com/docs/latest/ko/local/dev-guide)
- [Korean Address System Guide](https://www.juso.go.kr/)
- [Road Name Address vs Lot Number Address](https://www.juso.go.kr/addrlink/addressBuildDevNew.do?menu=roadName)
