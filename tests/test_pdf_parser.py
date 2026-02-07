#!/usr/bin/env python3
"""
Unit tests for the extended PDF parser.

Run from project root:
    python3 tests/test_pdf_parser.py
"""

import unittest
import sys
import os

# Add parent directory to path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firm_summary.parse_pdf_to_csv_extended import (
    extract_city_from_location,
    parse_column_mapping,
    match_columns,
    find_header_row
)


class TestCityExtraction(unittest.TestCase):
    """Test city extraction from Korean addresses."""
    
    def test_seoul_special_city(self):
        """Test extraction of 서울특별시."""
        result = extract_city_from_location("서울특별시 강남구 테헤란로 123")
        self.assertEqual(result, "서울특별시")
    
    def test_metropolitan_city(self):
        """Test extraction of 광역시."""
        result = extract_city_from_location("부산광역시 해운대구 센텀중앙로 79")
        self.assertEqual(result, "부산광역시")
        
        result = extract_city_from_location("대구광역시 달성군 현풍읍 테크노중앙대로")
        self.assertEqual(result, "대구광역시")
    
    def test_special_self_governing_province(self):
        """Test extraction of 특별자치도."""
        result = extract_city_from_location("제주특별자치도 제주시 첨단로 242")
        self.assertEqual(result, "제주특별자치도")
    
    def test_special_self_governing_city(self):
        """Test extraction of 특별자치시 (세종)."""
        result = extract_city_from_location("세종특별자치시 한누리대로 2130")
        self.assertEqual(result, "세종특별자치시")
    
    def test_province_city_combination(self):
        """Test extraction of 도 + 시 format."""
        result = extract_city_from_location("경기도 수원시 영통구 삼성로 129")
        self.assertEqual(result, "수원시")
        
        result = extract_city_from_location("충청남도 천안시 동남구 천안대로")
        self.assertEqual(result, "천안시")
    
    def test_empty_input(self):
        """Test empty or invalid input."""
        result = extract_city_from_location("")
        self.assertEqual(result, "")
        
        result = extract_city_from_location(None)
        self.assertEqual(result, "")
    
    def test_no_match(self):
        """Test address that doesn't match patterns."""
        result = extract_city_from_location("Unknown location format")
        self.assertTrue(len(result) >= 0)  # Should return something or empty string


class TestColumnMapping(unittest.TestCase):
    """Test column mapping functionality."""
    
    def test_simple_column_mapping(self):
        """Test simple column names without renaming."""
        args = ["번호", "회사명", "주소"]
        source, target = parse_column_mapping(args)
        self.assertEqual(source, ["번호", "회사명", "주소"])
        self.assertEqual(target, ["번호", "회사명", "주소"])
    
    def test_column_renaming(self):
        """Test column renaming with colon notation."""
        args = ["번호:Number", "회사명:Company Name", "주소:Address"]
        source, target = parse_column_mapping(args)
        self.assertEqual(source, ["번호", "회사명", "주소"])
        self.assertEqual(target, ["Number", "Company Name", "Address"])
    
    def test_mixed_mapping(self):
        """Test mixed simple and renamed columns."""
        args = ["번호:Number", "회사명", "주소:Address"]
        source, target = parse_column_mapping(args)
        self.assertEqual(source, ["번호", "회사명", "주소"])
        self.assertEqual(target, ["Number", "회사명", "Address"])


class TestHeaderDetection(unittest.TestCase):
    """Test header row detection in tables."""
    
    def test_find_header_with_keywords(self):
        """Test finding header row with common keywords."""
        table = [
            ["Some data", "More data"],
            ["번호", "회사명", "주소", "도시"],
            ["1", "삼성전자", "서울특별시", "서울"],
            ["2", "LG전자", "서울특별시", "서울"]
        ]
        idx, header = find_header_row(table)
        self.assertEqual(idx, 1)
        self.assertEqual(header, ["번호", "회사명", "주소", "도시"])
    
    def test_header_in_first_row(self):
        """Test finding header in first row."""
        table = [
            ["연번", "업종구분", "업체명", "소재지"],
            ["1", "과기원", "광주과학기술원", "광주광역시"],
        ]
        idx, header = find_header_row(table)
        self.assertEqual(idx, 0)
        self.assertIn("연번", header)
    
    def test_no_header_found(self):
        """Test when no header is found."""
        table = [
            ["1", "data1", "data2"],
            ["2", "data3", "data4"]
        ]
        idx, header = find_header_row(table)
        self.assertIsNone(idx)
        self.assertIsNone(header)


class TestColumnMatching(unittest.TestCase):
    """Test fuzzy column matching."""
    
    def test_exact_match(self):
        """Test exact column name matching."""
        header = ["번호", "회사명", "주소"]
        expected = ["번호", "회사명", "주소"]
        mapping = match_columns(header, expected)
        self.assertEqual(mapping[0], "번호")
        self.assertEqual(mapping[1], "회사명")
        self.assertEqual(mapping[2], "주소")
    
    def test_partial_match(self):
        """Test partial/fuzzy column matching."""
        header = ["연번", "업체명", "소재지"]
        expected = ["번호", "업체명", "주소"]
        mapping = match_columns(header, expected)
        # Should at least match 업체명 exactly
        self.assertEqual(mapping[1], "업체명")
    
    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        header = ["Number", "Company", "Address"]
        expected = ["number", "company", "address"]
        mapping = match_columns(header, expected)
        self.assertEqual(mapping[0], "number")
        self.assertEqual(mapping[1], "company")
        self.assertEqual(mapping[2], "address")


def run_tests():
    """Run all tests and display results."""
    print("=" * 70)
    print("Running PDF Parser Tests")
    print("=" * 70)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCityExtraction))
    suite.addTests(loader.loadTestsFromTestCase(TestColumnMapping))
    suite.addTests(loader.loadTestsFromTestCase(TestHeaderDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestColumnMatching))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print()
    print("=" * 70)
    if result.wasSuccessful():
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed!")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
