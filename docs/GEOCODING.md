# Geocoding Korean Addresses

`firm-geocode` (`src/firm_analyzer/core/geocoding.py`) turns the addresses
(도로명주소 and 지번주소) in the active 인원배정 list into map coordinates for
the map page (`/map`). To get the Kakao REST key it uses, see
[KOREAN_MAPS_SETUP.md](KOREAN_MAPS_SETUP.md).

## Input and output

- **Input:** the active 인원배정 list, the one `uv run firm-roster list` marks
  with `*` (`data.roster` in `config.yml`, or else the newest
  `data/<year>_전문연구요원_인원배정.csv`). There is no `--input` option, and the
  filter's output (`data/filtered_firms.csv`) is not used. To map another CSV,
  save it in `data/` and activate it with `uv run firm-roster activate <file>.csv`.
- **Output:** `src/firm_analyzer/web/static/js/firms_data.js`, rewritten on
  every run. Each firm gets `id` (연번), `type` (업종구분), `name`, `address`,
  `allocation` (배정인원), `jurisdiction` (관할청), `lat` and `lng`.
  `firm-export-site` publishes this same file, so run `firm-geocode` before
  exporting after you switch lists.
- **Cache:** `data/geocode_cache.json` (see [Cache](#cache)).

## Usage

```bash
uv run --env-file .env firm-geocode            # Kakao if KAKAO_REST_API_KEY is set
uv run --env-file .env firm-geocode --use-api  # always use the APIs
uv run firm-geocode --no-api                   # no network: cache + regional coordinates
```

`uv run python scripts/run_geocoding.py` works the same way.

> [!NOTE]
> `firm-geocode` reads `KAKAO_REST_API_KEY` from the process environment and
> does not load `.env` by itself. Pass the file with `uv run --env-file .env`, or
> `export KAKAO_REST_API_KEY=...` in the shell first. A key that is only in
> `.env` is otherwise ignored, and Kakao is never called.

### When the APIs are used

| How you run it | APIs used |
|----------------|-----------|
| `--use-api` | Kakao (if the key is set), then Nominatim |
| `--no-api` | None |
| Any other argument, even `--help` | None (there is no help text; the command runs) |
| No argument, `USE_GEOCODING_API` is `1`, `true` or `yes` | Same as `--use-api` |
| No argument, `KAKAO_REST_API_KEY` set | Same as `--use-api` |
| No argument, no key | Asks `Use geocoding API? (y/n, default=n)`. `y` uses Nominatim only; anything else, or no terminal to answer, uses no API. |

`USE_GEOCODING_API` is only read when no argument is given, and only its
"on" values do anything: `USE_GEOCODING_API=0` does not turn the APIs off (with a
Kakao key set they are still used). Use `--no-api` instead.

## Geocoding methods

Each address goes through these steps until one returns coordinates:

1. **Cache.** A previous result for the same address and 관할청 is reused.
   This happens even with `--no-api`.
2. **Kakao Local API** (only when the APIs are on and `KAKAO_REST_API_KEY` is
   set). The most accurate for Korean addresses. Uses the road-address result
   when there is one, else the lot-number result. Requests are spaced about
   0.15 s apart, and a 429 (rate limit) is retried.
3. **Nominatim (OpenStreetMap, via `geopy`)** (only when the APIs are on and
   Kakao found nothing). Free, but limited to one request per second, and less
   reliable for Korean addresses.
4. **Regional fallback.** Hardcoded centre coordinates plus a small offset so
   markers don't stack exactly. In order:
   1. the address starts with a known district or city
      (`REGION_COORDS`, e.g. `서울특별시 강남구`, `경기도 수원시`, `부산광역시`);
   2. the address contains a region name or one of its words;
   3. the address's first word is part of a region name;
   4. the 관할청 (`JURISDICTION_COORDS`, e.g. `서울`, `대전.충남`).

   An address that matches none of these gets no coordinates, so the firm has
   no marker.

The run ends with a count per method (Kakao, Nominatim, Fallback) and per 관할청.

## Cache

- File: `data/geocode_cache.json`. It is git-ignored, so it stays on your
  machine.
- Key: `{address}|{jurisdiction}`. Value: `lat`, `lng` and `method`
  (`Kakao`, `Nominatim` or `Fallback`).

  ```json
  {
    "서울특별시 강남구 테헤란로 152|서울": {
      "lat": 37.5042,
      "lng": 127.0475,
      "method": "Kakao"
    }
  }
  ```

- Read on every run. Written only when the APIs were on.
- Fallback results are cached too. If you ran with the APIs on but without a
  working Kakao key, those addresses keep their regional coordinates until you
  delete the cache (or their entries) and run again.

## Troubleshooting

### The Kakao key is ignored
The key is only in `.env`. Run `uv run --env-file .env firm-geocode`, or export
the variable. With the key picked up, the run prints
`Using Kakao Maps API for accurate Korean address geocoding` before it starts.

### `Kakao API error: 401` (or 403)
Kakao rejected the key. Use the **REST API** key (not the JavaScript or Admin
key), with no quotes or spaces, and check that the app is active in Kakao
Developers. Each failed address falls through to Nominatim or the regional
fallback.

### Coordinates are still approximate
- The cache holds fallback results from an earlier run: delete
  `data/geocode_cache.json` and run again.
- The address is incomplete (no road or building number). Kakao may then find
  only an approximate match or nothing, and in the second case the firm falls
  back to regional coordinates.
- The page still shows the old `firms_data.js`: hard-refresh the browser
  (Ctrl+Shift+R or Cmd+Shift+R).

### Slow geocoding
Nominatim allows one request per second, so a run without a Kakao key takes
about a second per address. Results are cached, so later runs only geocode new
addresses.

### The map shows a different list than the pipeline
The map data is only regenerated when you run `firm-geocode`. After importing
or activating another list, run it again.

### The map itself does not load
That is a different key: the map page needs `KAKAO_JS_API_KEY`. See
[KOREAN_MAPS_SETUP.md](KOREAN_MAPS_SETUP.md#map-display-javascript-key).

## Contributing

When adding new hardcoded coordinates to `REGION_COORDS` or `JURISDICTION_COORDS`, please:
1. Use reliable sources for coordinates
2. Add comments explaining the location
3. Test with actual addresses from that region

To try another geocoding service, add a function next to
`geocode_with_kakao()` and `geocode_with_nominatim()` and call it from
`get_coordinates()`.
