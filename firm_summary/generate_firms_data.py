#!/usr/bin/env python3
"""
Convert the CSV data to JavaScript format for the firms viewer webpage.
This script generates a firms_data.js file with geocoded coordinates.

Uses geopy with Nominatim for geocoding Korean addresses.
Results are cached to avoid repeated API calls.
"""

import csv
import json
import os
import random
import sys
import time

try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False
    print("Warning: geopy not installed. Using fallback coordinates only.")
    print("Install with: pip install geopy")

# Get the parent directory (project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
WEBAPP_DIR = os.path.join(PROJECT_ROOT, "webapp")

# Approximate coordinates for major cities/regions in Korea
# These are representative coordinates for each area
REGION_COORDS = {
    # Seoul Districts (구)
    '서울특별시 강남구': (37.5172, 127.0473),
    '서울특별시 강동구': (37.5301, 127.1237),
    '서울특별시 강서구': (37.5509, 126.8495),
    '서울특별시 관악구': (37.4784, 126.9516),
    '서울특별시 광진구': (37.5384, 127.0823),
    '서울특별시 구로구': (37.4954, 126.8874),
    '서울특별시 금천구': (37.4600, 126.9000),
    '서울특별시 노원구': (37.6542, 127.0568),
    '서울특별시 도봉구': (37.6688, 127.0471),
    '서울특별시 동대문구': (37.5744, 127.0395),
    '서울특별시 동작구': (37.5124, 126.9393),
    '서울특별시 마포구': (37.5663, 126.9014),
    '서울특별시 서대문구': (37.5791, 126.9368),
    '서울특별시 서초구': (37.4837, 127.0324),
    '서울특별시 성동구': (37.5633, 127.0371),
    '서울특별시 성북구': (37.5894, 127.0167),
    '서울특별시 송파구': (37.5145, 127.1059),
    '서울특별시 양천구': (37.5170, 126.8665),
    '서울특별시 영등포구': (37.5263, 126.8962),
    '서울특별시 용산구': (37.5324, 126.9906),
    '서울특별시 은평구': (37.6176, 126.9227),
    '서울특별시 종로구': (37.5730, 126.9794),
    '서울특별시 중구': (37.5636, 126.9976),
    
    # Major Cities
    '부산광역시': (35.1796, 129.0756),
    '대구광역시': (35.8714, 128.6014),
    '인천광역시': (37.4563, 126.7052),
    '광주광역시': (35.1595, 126.8526),
    '대전광역시': (36.3504, 127.3845),
    '울산광역시': (35.5384, 129.3114),
    '세종특별자치시': (36.4800, 127.2890),
    
    # Gyeonggi-do
    '경기도 수원시': (37.2636, 127.0286),
    '경기도 성남시': (37.4201, 127.1265),
    '경기도 용인시': (37.2411, 127.1775),
    '경기도 고양시': (37.6584, 126.8320),
    '경기도 안양시': (37.3943, 126.9568),
    '경기도 부천시': (37.5034, 126.7660),
    '경기도 화성시': (37.1996, 126.8317),
    '경기도 안산시': (37.3219, 126.8309),
    '경기도 평택시': (36.9921, 127.0857),
    '경기도 시흥시': (37.3800, 126.8030),
    '경기도 파주시': (37.7126, 126.7612),
    '경기도 김포시': (37.6152, 126.7156),
    '경기도 의정부시': (37.7381, 127.0337),
    '경기도 광명시': (37.4785, 126.8646),
    '경기도 군포시': (37.3614, 126.9352),
    '경기도 하남시': (37.5391, 127.2147),
    '경기도 오산시': (37.1497, 127.0697),
    '경기도 이천시': (37.2720, 127.4350),
    '경기도 포천시': (37.8949, 127.2003),
    '경기도 의왕시': (37.3447, 126.9685),
    
    # Provinces
    '강원특별자치도 춘천시': (37.8813, 127.7298),
    '강원특별자치도 원주시': (37.3422, 127.9202),
    '강원특별자치도 강릉시': (37.7519, 128.8760),
    '충청북도 청주시': (36.6424, 127.4890),
    '충청북도 충주시': (36.9910, 127.9259),
    '충청북도 진천군': (36.8553, 127.4357),
    '충청북도 음성군': (36.9400, 127.6900),
    '충청남도 천안시': (36.8151, 127.1139),
    '충청남도 아산시': (36.7899, 127.0018),
    '충청남도 공주시': (36.4465, 127.1190),
    '충청남도 서산시': (36.7849, 126.4502),
    '충청남도 예산군': (36.6803, 126.8479),
    '전북특별자치도 전주시': (35.8242, 127.1480),
    '전북특별자치도 익산시': (35.9482, 126.9576),
    '전북특별자치도 군산시': (35.9676, 126.7369),
    '전북특별자치도 정읍시': (35.5699, 126.8558),
    '전라남도 순천시': (34.9506, 127.4872),
    '전라남도 광양시': (34.9407, 127.6959),
    '전라남도 나주시': (34.8794, 126.7107),
    '전라남도 장흥군': (34.6815, 126.9070),
    '전라남도 강진군': (34.6421, 126.7673),
    '경상북도 포항시': (36.0190, 129.3435),
    '경상북도 경산시': (35.8251, 128.7414),
    '경상북도 구미시': (36.1195, 128.3446),
    '경상북도 안동시': (36.5684, 128.7294),
    '경상남도 창원시': (35.2284, 128.6811),
    '경상남도 진주시': (35.1798, 128.1076),
    '경상남도 양산시': (35.3350, 129.0378),
    '경상남도 김해시': (35.2285, 128.8894),
    '경상남도 창녕군': (35.5441, 128.4918),
    '제주특별자치도 제주시': (33.4996, 126.5312),
    
    # Default for each province
    '경기도': (37.4138, 127.5183),
    '강원특별자치도': (37.8228, 128.1555),
    '충청북도': (36.6357, 127.4917),
    '충청남도': (36.5184, 126.8000),
    '전북특별자치도': (35.8200, 127.1089),
    '전라남도': (34.8679, 126.9910),
    '경상북도': (36.4919, 128.8889),
    '경상남도': (35.4606, 128.2132),
    '제주특별자치도': (33.4890, 126.4983),
}

# Jurisdiction to region mapping
JURISDICTION_COORDS = {
    '서울': (37.5665, 126.9780),
    '부산.울산': (35.3, 129.1),
    '대구.경북': (35.87, 128.60),
    '인천': (37.4563, 126.7052),
    '광주.전남': (35.16, 126.85),
    '대전.충남': (36.3504, 127.3845),
    '경기': (37.4138, 127.5183),
    '경인': (37.4563, 126.7052),  # Gyeonggi-Incheon area
    '경기북부': (37.7381, 127.0337),  # Northern Gyeonggi (around Uijeongbu)
    '강원': (37.8228, 128.1555),
    '강원.제주': (37.8228, 128.1555),
    '강원영동': (37.7519, 128.8760),  # Eastern Gangwon (around Gangneung)
    '충북': (36.6357, 127.4917),
    '전북': (35.8200, 127.1089),
    '경남': (35.4606, 128.2132),
    '제주': (33.4890, 126.4983),
}

# Cache for geocoding results
GEOCODE_CACHE = {}
GEOCODE_CACHE_FILE = None  # Will be set in main()
GEOLOCATOR = None  # Reusable geolocator instance

def load_geocode_cache():
    """Load geocoding cache from file."""
    global GEOCODE_CACHE
    if GEOCODE_CACHE_FILE and os.path.exists(GEOCODE_CACHE_FILE):
        try:
            with open(GEOCODE_CACHE_FILE, 'r', encoding='utf-8') as f:
                GEOCODE_CACHE = json.load(f)
            print(f"Loaded {len(GEOCODE_CACHE)} cached geocoding results")
        except Exception as e:
            print(f"Warning: Could not load geocode cache: {e}")
            GEOCODE_CACHE = {}
    else:
        GEOCODE_CACHE = {}

def save_geocode_cache():
    """Save geocoding cache to file."""
    if GEOCODE_CACHE_FILE:
        try:
            with open(GEOCODE_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(GEOCODE_CACHE, f, ensure_ascii=False, indent=2)
            print(f"Saved {len(GEOCODE_CACHE)} geocoding results to cache")
        except Exception as e:
            print(f"Warning: Could not save geocode cache: {e}")

def geocode_with_nominatim(address, max_retries=3):
    """
    Geocode an address using Nominatim with retry logic.
    
    Uses the global GEOLOCATOR instance which is initialized once in main().
    
    Args:
        address: Address string to geocode
        max_retries: Maximum number of retries on timeout
    
    Returns:
        Tuple of (lat, lng) or (None, None) if geocoding fails
    """
    global GEOLOCATOR
    
    if not GEOLOCATOR:
        return None, None
    
    for attempt in range(max_retries):
        try:
            # Add small delay to respect Nominatim usage policy
            time.sleep(1.1)
            location = GEOLOCATOR.geocode(address, timeout=10)
            if location:
                return location.latitude, location.longitude
            return None, None
        except GeocoderTimedOut:
            if attempt < max_retries - 1:
                print(f"  Timeout, retrying ({attempt + 1}/{max_retries})...")
                time.sleep(2)
                continue
            print(f"  Failed after {max_retries} retries")
            return None, None
        except GeocoderServiceError as e:
            print(f"  Geocoder service error: {e}")
            return None, None
        except Exception as e:
            print(f"  Unexpected error: {e}")
            return None, None
    return None, None

def get_coordinates_from_fallback(address, jurisdiction=None):
    """Get approximate coordinates using hardcoded fallback data.
    
    Args:
        address: The address string to geocode
        jurisdiction: The jurisdiction/region name as fallback (e.g., "대전.충남")
    
    Returns:
        Tuple of (lat, lng) or (None, None) if no match found
    """
    if not address:
        # If address is empty but we have jurisdiction, use that
        if jurisdiction and jurisdiction in JURISDICTION_COORDS:
            coords = JURISDICTION_COORDS[jurisdiction]
            lat_offset = (random.random() - 0.5) * 0.02
            lng_offset = (random.random() - 0.5) * 0.02
            return coords[0] + lat_offset, coords[1] + lng_offset
        return None, None

    # Try to match specific district first
    for region, coords in REGION_COORDS.items():
        if address.startswith(region):
            # Add small random offset to prevent overlapping markers
            lat_offset = (random.random() - 0.5) * 0.008
            lng_offset = (random.random() - 0.5) * 0.008
            return coords[0] + lat_offset, coords[1] + lng_offset

    # Try partial match
    for region, coords in REGION_COORDS.items():
        if region in address or any(part in address for part in region.split()):
            lat_offset = (random.random() - 0.5) * 0.01
            lng_offset = (random.random() - 0.5) * 0.01
            return coords[0] + lat_offset, coords[1] + lng_offset

    # Extract city/province from address and try to match
    parts = address.split()
    if parts:
        for region, coords in REGION_COORDS.items():
            if parts[0] in region:
                lat_offset = (random.random() - 0.5) * 0.02
                lng_offset = (random.random() - 0.5) * 0.02
                return coords[0] + lat_offset, coords[1] + lng_offset

    # Final fallback: use jurisdiction if available
    if jurisdiction and jurisdiction in JURISDICTION_COORDS:
        coords = JURISDICTION_COORDS[jurisdiction]
        lat_offset = (random.random() - 0.5) * 0.02
        lng_offset = (random.random() - 0.5) * 0.02
        return coords[0] + lat_offset, coords[1] + lng_offset

    return None, None

def get_coordinates(address, jurisdiction=None, use_api=True):
    """Get coordinates for an address using geopy with fallback.
    
    This function tries multiple strategies to geocode an address:
    1. Check cache for previously geocoded addresses
    2. Try geocoding with Nominatim API (if use_api=True and geopy is available)
    3. Fall back to hardcoded regional coordinates
    
    Args:
        address: The address string to geocode
        jurisdiction: The jurisdiction/region name as fallback (e.g., "대전.충남")
        use_api: Whether to use external geocoding API (default: True)
    
    Returns:
        Tuple of (lat, lng) or (None, None) if no match found
    """
    # Check cache first
    cache_key = f"{address}|{jurisdiction}"
    if cache_key in GEOCODE_CACHE:
        cached = GEOCODE_CACHE[cache_key]
        return cached.get('lat'), cached.get('lng')
    
    lat, lng = None, None
    
    # Try API geocoding if enabled and available
    if use_api and GEOPY_AVAILABLE and address:
        try:
            lat, lng = geocode_with_nominatim(address)
            
            if lat and lng:
                print(f"  ✓ Geocoded via API: {address[:50]}")
                # Add small random offset to prevent overlapping markers
                lat_offset = (random.random() - 0.5) * 0.001
                lng_offset = (random.random() - 0.5) * 0.001
                lat += lat_offset
                lng += lng_offset
        except Exception as e:
            print(f"  Error during API geocoding: {e}")
    
    # Fall back to hardcoded coordinates if API didn't work
    if lat is None or lng is None:
        lat, lng = get_coordinates_from_fallback(address, jurisdiction)
        if lat and lng:
            print(f"  → Using fallback: {address[:50]}")
    
    # Cache the result
    GEOCODE_CACHE[cache_key] = {'lat': lat, 'lng': lng}
    
    return lat, lng


def main():
    global GEOCODE_CACHE_FILE, GEOLOCATOR
    
    # Set up cache file path
    GEOCODE_CACHE_FILE = os.path.join(DATA_DIR, "geocode_cache.json")
    
    # Load existing cache
    load_geocode_cache()
    
    # Check if user wants to use API geocoding
    # Support command-line argument: --use-api or --no-api
    # Support environment variable: USE_GEOCODING_API=1 or 0
    use_api = False
    
    if len(sys.argv) > 1:
        if '--use-api' in sys.argv:
            use_api = True
        elif '--no-api' in sys.argv:
            use_api = False
    elif os.environ.get('USE_GEOCODING_API', '').lower() in ('1', 'true', 'yes'):
        use_api = True
    else:
        # Interactive prompt as fallback
        try:
            use_api = input("Use geopy API for geocoding? (y/n, default=n): ").strip().lower() == 'y'
        except (EOFError, KeyboardInterrupt):
            print("\nDefaulting to fallback coordinates only.")
            use_api = False
    
    if use_api and not GEOPY_AVAILABLE:
        print("\nWarning: geopy is not installed. Install with:")
        print("  pip install geopy")
        print("\nFalling back to hardcoded coordinates only.\n")
        use_api = False
    elif use_api:
        # Initialize geolocator once for reuse
        GEOLOCATOR = Nominatim(user_agent="firm_websearch_geocoder")
        print("\nUsing geopy with Nominatim for geocoding.")
        print("Note: This will be slow due to API rate limits (1 request per second).")
        print("Results will be cached in geocode_cache.json for future runs.\n")
    else:
        print("\nUsing hardcoded fallback coordinates only.\n")
    
    firms = []

    # Read CSV file
    input_file = os.path.join(DATA_DIR, "2025_전문연구요원_인원배정.csv")
    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header

        for i, row in enumerate(reader, 1):
            if len(row) >= 6:
                firm = {
                    "id": row[0].strip() if row[0] else "",
                    "type": row[1].strip() if row[1] else "",
                    "name": row[2].strip() if row[2] else "",
                    "address": row[3].strip() if row[3] else "",
                    "allocation": row[4].strip() if row[4] else "",
                    "jurisdiction": row[5].strip() if row[5] else "",
                }

                # Get coordinates (pass jurisdiction as fallback)
                if i % 100 == 0:
                    print(f"Processing firm {i}...")
                lat, lng = get_coordinates(firm["address"], firm["jurisdiction"], use_api=use_api)
                firm["lat"] = lat
                firm["lng"] = lng

                firms.append(firm)

    # Save updated cache
    if use_api:
        save_geocode_cache()

    # Write JavaScript file
    output_file = os.path.join(WEBAPP_DIR, "static", "js", "firms_data.js")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("// Auto-generated firms data from CSV\n")
        f.write("// Generated for 2025 전문연구요원 인원배정 업체 현황\n")
        if use_api:
            f.write("// Geocoded using geopy with Nominatim API\n")
        else:
            f.write("// Geocoded using fallback coordinates\n")
        f.write("\n")
        f.write("const firmsData = ")
        f.write(json.dumps(firms, ensure_ascii=False, indent=2))
        f.write(";\n")

    print(f"\nGenerated {output_file} with {len(firms)} firms")

    # Print statistics
    regions = {}
    geocoded_count = 0
    for firm in firms:
        region = firm["jurisdiction"]
        if region not in regions:
            regions[region] = 0
        regions[region] += 1
        if firm["lat"] and firm["lng"]:
            geocoded_count += 1

    print(f"\nSuccessfully geocoded: {geocoded_count}/{len(firms)} firms")
    print("\nFirms by region:")
    for region, count in sorted(regions.items(), key=lambda x: -x[1]):
        print(f"  {region}: {count}")

if __name__ == '__main__':
    main()
