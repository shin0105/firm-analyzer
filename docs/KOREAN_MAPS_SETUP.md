# Korean Maps Setup Guide

This guide explains how to set up accurate geocoding for Korean addresses in the firm viewer map, and the Kakao keys the map needs. There are two, both from the same Kakao app:

| Variable | Kakao key | Used by | Public? |
|----------|-----------|---------|---------|
| `KAKAO_REST_API_KEY` | REST API 키 | `firm-geocode`, to turn addresses into coordinates | No, keep it secret |
| `KAKAO_JS_API_KEY` | JavaScript 키 | The map page (`/map`), to draw the map in the browser | Yes, sent to every visitor |

## Problem

Without a geocoding API, `firm-geocode` places each firm at hardcoded regional coordinates (the centre of its district or city), not at its building. Many addresses in the list are also incomplete (e.g., "광주광역시 북구 첨단과기로", with no building number).

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
7. In the app's key list ("앱 키", shown as "플랫폼 키" in newer versions of the console), copy the **REST API 키** (REST API Key)

### Step 2: Set the Environment Variable

#### Option A: Using .env file (Recommended)

Add to your `.env` file in the project root:

```bash
KAKAO_REST_API_KEY=your_rest_api_key_here
```

`firm-geocode` does not load `.env` by itself, so run it with
`uv run --env-file .env firm-geocode` (Step 4). Without `--env-file`, a key
that is only in `.env` is ignored.

#### Option B: Using export command

```bash
export KAKAO_REST_API_KEY=your_rest_api_key_here
```

Add this to your `~/.bashrc` or `~/.zshrc` to make it permanent.

### Step 3: Test the API Connection

Run the test script to verify your API key works (it loads `.env` itself):

```bash
uv run python tests/test_kakao_geocoding.py
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

Run the geocoding command to process all addresses:

```bash
uv run --env-file .env firm-geocode
```

The command will:
1. Read addresses from the active 인원배정 list (the one `uv run firm-roster list` marks with `*`)
2. Use Kakao Maps API to get exact coordinates
3. Cache results in `data/geocode_cache.json`
4. Generate `src/firm_analyzer/web/static/js/firms_data.js` with accurate coordinates

The first run makes one Kakao request per address in the list, about 0.15 seconds each. Results are cached, so subsequent runs only geocode new addresses.

If you ran `firm-geocode` earlier without a working key, delete `data/geocode_cache.json` first: regional fallback results are cached too, and would otherwise be reused.

### Step 5: View the Updated Map

Start the web application:

```bash
uv run firm-app
```

Open http://localhost:8001/map to see the map with accurate locations. Drawing the map needs the JavaScript key, set up in the next section.

## Map display (JavaScript key)

The map page loads the Kakao Maps JavaScript SDK in the browser, with its own key:

1. In the same Kakao app, copy the **JavaScript 키** and add it to `.env`:

   ```bash
   KAKAO_JS_API_KEY=your_javascript_key_here
   ```

   `firm-app` loads `.env` itself. Restart it after changing the key.
2. Register the address you open the map from. In Kakao Developers, go to
   **앱 → 플랫폼 키 → JavaScript 키 → JavaScript SDK 도메인** (formerly
   "사이트 도메인") and add `http://localhost:8001`, plus
   `http://localhost:5173` if you use `npm run dev`. For a deployed copy, add
   its URL too (see [VERCEL_DEPLOY.md](VERCEL_DEPLOY.md)).

Without the key, or from an address that is not registered, the map page still
lists the firms but shows a message instead of the map. To turn the map off
entirely, set `app.enable_kakao_map: false` in `config.yml`.

This key is sent to every visitor's browser, so it is public by design; the
domain list is what limits its use. Never use the REST key here.

## Understanding the Geocoding Process

### Geocoding Priority

The command tries multiple methods in order:

1. **Check Cache**: If address was geocoded before, use cached result
2. **Kakao Maps API**: Best for Korean addresses (requires API key)
3. **Nominatim (OSM)**: Fallback when Kakao finds nothing or no key is set
4. **Regional Coordinates**: Final fallback using hardcoded city/district centers

Steps 2 and 3 only run when the APIs are on. See [GEOCODING.md](GEOCODING.md) for when that is, and for the `--use-api` / `--no-api` flags.

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
- Kakao API may return the road location or another best match

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
uv run --env-file .env firm-geocode
```

## Troubleshooting

### Key Set in .env but Not Used

**Symptom**: `firm-geocode` asks `Use geocoding API? (y/n, default=n)`, or never prints `Using Kakao Maps API`.

**Solution**: The key is not in the process environment. Run `uv run --env-file .env firm-geocode`, or export the variable first.

### API Key Not Working

**Error**: `firm-geocode` prints `Kakao API error: 401` (or 403) for each address and falls back to Nominatim or regional coordinates. For a 401, the test script prints "Authentication failed - check your KAKAO_REST_API_KEY".

**Solutions**:
- Verify you're using the REST API key (not JavaScript key or Admin key)
- Check there are no extra spaces or quotes in the key
- Ensure the key is active in Kakao Developers console

### Rate Limiting

**Error**: API returns 429 status code (`firm-geocode` prints `Rate limit hit, retrying`)

**Solution**: 
- Kakao Maps API has rate limits on the free tier
- `firm-geocode` automatically retries with delays
- If persistent, consider adding longer delays in the code, or run again later: addresses already geocoded are cached

### No Results for Address

**Symptom**: `firm-geocode` prints `→ Using fallback: [address]` (the test script prints "No results found for: [address]")

**Causes**:
- Address is too incomplete or incorrect
- The command falls back to Nominatim, then to regional coordinates

**Solutions**:
- Check if the address exists in reality
- Some research institutes have internal roads not in public databases
- Consider correcting the address in the active list CSV in `data/`

### Coordinates Still Approximate

**Possible causes**:
1. API key not set, or only in `.env` without `--env-file` - the command falls back to regional coordinates
2. Cache contains old data - delete `data/geocode_cache.json` and regenerate
3. `firms_data.js` not updated - make sure to regenerate after geocoding
4. Browser cache - do a hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

## API Usage Limits

Kakao lists the free daily quota for each API in the Kakao Developers console.

For this project:
- Initial geocoding: one API call per address in the active list (one-time)
- Subsequent runs: calls only for addresses not yet in the cache
- Well within free tier limits

## Privacy and Security

- Store API keys in `.env` file (already in `.gitignore`)
- Never commit API keys to version control
- `KAKAO_JS_API_KEY` is public by design; restrict it to your domains in the developer console. Keep `KAKAO_REST_API_KEY` on your machine.
- `data/geocode_cache.json` is git-ignored, so it is not committed. It only holds addresses from the list and their coordinates.

## Alternative: Without API Key

If you don't want to use Kakao API, the system will:
- Use regional coordinates for approximate locations
- Add random offsets to prevent marker overlap
- Still functional but less accurate

To use fallback only:
```bash
uv run firm-geocode --no-api
```

## Support

For issues with:
- **Kakao API**: Visit [Kakao Developers](https://developers.kakao.com/)
- **This tool**: Open an issue on GitHub
- **Address data**: Check the active list CSV in `data/` (`uv run firm-roster list`)

## References

- [Kakao Local API Documentation (Korean)](https://developers.kakao.com/docs/latest/ko/local/dev-guide)
- [Korean Address System Guide](https://www.juso.go.kr/)
- [Road Name Address vs Lot Number Address](https://www.juso.go.kr/addrlink/addressBuildDevNew.do?menu=roadName)
