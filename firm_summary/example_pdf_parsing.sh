#!/bin/bash
# Example script demonstrating PDF to CSV parsing features
# This script shows various ways to use the extended PDF parser

echo "========================================"
echo "PDF to CSV Parser - Usage Examples"
echo "========================================"
echo ""

# Example 1: Basic parsing with default settings
echo "Example 1: Basic parsing"
echo "-------------------------"
echo "Command: python3 firm_summary/parse_pdf_to_csv_extended.py"
echo ""
echo "This will parse the default PDF with standard columns:"
echo "  - 연번 (Number)"
echo "  - 업종구분 (Industry Type)"
echo "  - 업체명 (Company Name)"
echo "  - 소재지 (Location)"
echo "  - 25년 배정인원 (2025 Allocation)"
echo "  - 관할청 (Jurisdiction)"
echo ""

# Example 2: Extract city from location
echo "Example 2: Extract city from location"
echo "--------------------------------------"
echo "Command: python3 firm_summary/parse_pdf_to_csv_extended.py --extract-city-from-location"
echo ""
echo "This adds an additional '도시' (City) column with extracted city names:"
echo "  서울특별시 강남구 테헤란로 123 → 서울특별시"
echo "  경기도 수원시 영통구 삼성로 129 → 수원시"
echo "  부산광역시 해운대구 센텀중앙로 79 → 부산광역시"
echo ""

# Example 3: Custom column mapping
echo "Example 3: Custom column mapping"
echo "---------------------------------"
echo "Command: python3 firm_summary/parse_pdf_to_csv_extended.py \\"
echo "  --pdf data/korean_companies.pdf \\"
echo "  --output data/korean_companies.csv \\"
echo "  --columns \"번호\" \"회사명\" \"상세주소\" \"도시\""
echo ""
echo "This parses a PDF with custom columns: 번호, 회사명, 상세주소, 도시"
echo ""

# Example 4: Rename columns
echo "Example 4: Rename columns while parsing"
echo "----------------------------------------"
echo "Command: python3 firm_summary/parse_pdf_to_csv_extended.py \\"
echo "  --columns \"번호:Number\" \"회사명:Company Name\" \"소재지:Location\" \\"
echo "  --extract-city-from-location"
echo ""
echo "This renames columns to English while parsing:"
echo "  번호 → Number"
echo "  회사명 → Company Name"
echo "  소재지 → Location"
echo ""

# Example 5: Combining features
echo "Example 5: All features combined"
echo "---------------------------------"
echo "Command: python3 firm_summary/parse_pdf_to_csv_extended.py \\"
echo "  --pdf data/company_directory.pdf \\"
echo "  --output data/parsed_directory.csv \\"
echo "  --columns \"기업명:Company\" \"주소:Address\" \"전화번호:Phone\" \\"
echo "  --extract-city-from-location \\"
echo "  --min-columns 2"
echo ""
echo "This combines column mapping, renaming, city extraction, and custom filtering."
echo ""

echo "========================================"
echo "For more details, see:"
echo "  firm_summary/README_PDF_PARSER.md"
echo "========================================"
