#!/usr/bin/env python
"""
Manual check for Kakao Maps API geocoding (network + API key required).

This script tests the geocoding functionality with sample Korean addresses
to verify that the Kakao Maps API integration works correctly.

Usage:
    export KAKAO_REST_API_KEY=your_api_key
    python test_kakao_geocoding.py
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Get API key from environment
KAKAO_API_KEY = os.environ.get('KAKAO_REST_API_KEY', '')

def geocode_address(address):
    """Test geocoding a single address using Kakao Maps API."""
    if not KAKAO_API_KEY:
        print("❌ KAKAO_REST_API_KEY not set in environment")
        print("   Get a free API key at: https://developers.kakao.com/")
        return None
    
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    
    try:
        response = requests.get(url, headers=headers, params={"query": address}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('documents'):
                result = data['documents'][0]
                
                # Get coordinates from road address or jibun address
                if result.get('road_address'):
                    lat = float(result['road_address']['y'])
                    lng = float(result['road_address']['x'])
                    address_type = "도로명주소"
                    address_name = result['road_address'].get('address_name', '')
                elif result.get('address'):
                    lat = float(result['address']['y'])
                    lng = float(result['address']['x'])
                    address_type = "지번주소"
                    address_name = result['address'].get('address_name', '')
                else:
                    return None
                
                return {
                    'lat': lat,
                    'lng': lng,
                    'type': address_type,
                    'full_address': address_name
                }
            else:
                print(f"   No results found for: {address}")
                return None
        
        elif response.status_code == 401:
            print(f"❌ Authentication failed - check your KAKAO_REST_API_KEY")
            return None
        else:
            print(f"❌ API error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    """Test with sample Korean addresses from the CSV."""
    
    print("=" * 70)
    print("Testing Kakao Maps API Geocoding")
    print("=" * 70)
    print()
    
    if not KAKAO_API_KEY:
        print("⚠️  KAKAO_REST_API_KEY environment variable not set!")
        print()
        print("To test this functionality:")
        print("1. Get a free API key at https://developers.kakao.com/")
        print("2. Set the environment variable:")
        print("   export KAKAO_REST_API_KEY=your_api_key")
        print()
        sys.exit(1)
    
    # Sample addresses from the CSV
    test_addresses = [
        "광주광역시 북구 첨단과기로",
        "서울특별시 강남구 테헤란로",
        "대전광역시 유성구 대학로",
        "부산광역시 해운대구 센텀중앙로",
        "경기도 성남시 분당구 판교역로",
    ]
    
    print(f"Testing {len(test_addresses)} sample addresses...\n")
    
    success_count = 0
    for i, address in enumerate(test_addresses, 1):
        print(f"{i}. Testing: {address}")
        result = geocode_address(address)
        
        if result:
            print(f"   ✓ Geocoded successfully!")
            print(f"   Type: {result['type']}")
            print(f"   Full Address: {result['full_address']}")
            print(f"   Coordinates: ({result['lat']:.6f}, {result['lng']:.6f})")
            success_count += 1
        else:
            print(f"   ✗ Geocoding failed")
        
        print()
    
    print("=" * 70)
    print(f"Results: {success_count}/{len(test_addresses)} addresses geocoded successfully")
    print("=" * 70)
    
    if success_count == len(test_addresses):
        print("✓ All tests passed! Kakao Maps API is working correctly.")
        return 0
    elif success_count > 0:
        print("⚠ Some addresses were geocoded successfully, but not all.")
        return 0
    else:
        print("✗ No addresses were geocoded. Check your API key.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
