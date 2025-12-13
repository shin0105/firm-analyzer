#!/usr/bin/env python3
"""
Extended PDF to CSV parser with flexible column mapping.

This script can parse various PDF formats and extract table data to CSV,
with customizable column names and mappings. It's particularly useful for
parsing Korean company lists with different formats.

Usage:
    # Use default settings (original format)
    python3 firm_summary/parse_pdf_to_csv_extended.py
    
    # Parse with custom column mapping
    python3 firm_summary/parse_pdf_to_csv_extended.py \
        --pdf data/company_list.pdf \
        --output data/company_list.csv \
        --columns "번호:Number" "회사명:Company Name" "상세주소:Detail Location" "도시:City"
    
    # Parse Korean company list
    python3 firm_summary/parse_pdf_to_csv_extended.py \
        --pdf data/korean_companies.pdf \
        --output data/korean_companies.csv \
        --extract-city-from-location

Output:
    Creates a CSV file with the specified column mappings
"""

import os
import csv
import re
import argparse
import pdfplumber
from typing import List, Dict, Tuple, Optional


def extract_city_from_location(location: str) -> str:
    """
    Extract city name from a Korean location string.
    
    Examples:
        "서울특별시 강남구 테헤란로 123" -> "서울특별시"
        "경기도 수원시 영통구 삼성로 129" -> "수원시"
        "부산광역시 해운대구 센텀중앙로 79" -> "부산광역시"
        "제주특별자치도 제주시 첨단로 242" -> "제주특별자치도"
    
    Args:
        location: Full address string in Korean
        
    Returns:
        Extracted city name
    """
    if not location:
        return ""
    
    # Pattern for Korean administrative divisions
    # Order matters: match more specific patterns first
    patterns = [
        r'^([가-힣]+특별자치시)',        # 세종특별자치시 (must come before 특별시)
        r'^([가-힣]+특별자치도)',        # 제주특별자치도
        r'^([가-힣]+특별시)',            # 서울특별시
        r'^([가-힣]+광역시)',            # 부산광역시, 대구광역시, etc.
        r'^([가-힣]+도)\s+([가-힣]+시)', # 경기도 수원시 -> 수원시 (requires spacing)
        r'^([가-힣]+시)',                # 서울시, 수원시 (without 도)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, location)
        if match:
            # For patterns with 도 + 시, return the 시 (group 2)
            if len(match.groups()) > 1 and match.group(2):
                return match.group(2)
            # Otherwise return the first group
            return match.group(1)
    
    # If no pattern matches, try to extract first word
    parts = location.split()
    if parts:
        return parts[0]
    
    return ""


def parse_column_mapping(column_args: List[str]) -> Tuple[List[str], List[str]]:
    """
    Parse column mapping arguments into source and target column names.
    
    Args:
        column_args: List of strings in format "source:target" or just "source"
        
    Returns:
        Tuple of (source_columns, target_columns)
    """
    source_cols = []
    target_cols = []
    
    for arg in column_args:
        if ':' in arg:
            source, target = arg.split(':', 1)
            source_cols.append(source.strip())
            target_cols.append(target.strip())
        else:
            # If no mapping provided, use same name for both
            col = arg.strip()
            source_cols.append(col)
            target_cols.append(col)
    
    return source_cols, target_cols


def find_header_row(table: List[List]) -> Tuple[Optional[int], Optional[List[str]]]:
    """
    Find the header row in a table by looking for expected column names.
    
    Args:
        table: 2D list representing table data
        
    Returns:
        Tuple of (row_index, header_columns) or (None, None) if not found
    """
    if not table:
        return None, None
    
    # Common header keywords in Korean company lists
    header_keywords = ['번호', '회사', '업체', '기업', '소재지', '주소', '위치', '도시', 
                       '연번', '업종', '구분', 'No', 'Number', 'Company', 'Location']
    
    for idx, row in enumerate(table[:5]):  # Check first 5 rows only
        if not row:
            continue
        
        row_text = ' '.join(str(cell or '').strip() for cell in row).lower()
        
        # If row contains multiple header keywords, it's likely a header
        keyword_count = sum(1 for keyword in header_keywords if keyword.lower() in row_text)
        if keyword_count >= 2:
            return idx, [str(cell or '').strip() for cell in row]
    
    return None, None


def match_columns(header_row: List[str], expected_columns: List[str]) -> Dict[int, str]:
    """
    Match header columns to expected column names using fuzzy matching.
    
    Args:
        header_row: List of column names from PDF header
        expected_columns: List of expected column names
        
    Returns:
        Dictionary mapping column index to expected column name
    """
    column_mapping = {}
    
    for idx, col_name in enumerate(header_row):
        col_name_clean = col_name.strip().lower()
        
        # Try exact match first
        for expected in expected_columns:
            if col_name_clean == expected.lower():
                column_mapping[idx] = expected
                break
        
        # Try partial match
        if idx not in column_mapping:
            for expected in expected_columns:
                expected_lower = expected.lower()
                # Check if expected is substring of column or vice versa
                if expected_lower in col_name_clean or col_name_clean in expected_lower:
                    column_mapping[idx] = expected
                    break
    
    return column_mapping


def parse_pdf_to_csv_extended(
    pdf_path: str, 
    output_csv_path: str,
    expected_columns: Optional[List[str]] = None,
    output_columns: Optional[List[str]] = None,
    extract_city: bool = False,
    min_columns: int = 3
) -> int:
    """
    Parse a PDF file and convert to CSV with flexible column mapping.
    
    Args:
        pdf_path: Path to the input PDF file
        output_csv_path: Path to the output CSV file
        expected_columns: List of expected column names in PDF (for matching)
        output_columns: List of column names to use in output CSV
        extract_city: Whether to extract city from location column
        min_columns: Minimum number of columns required for a valid row
        
    Returns:
        Number of data rows extracted (excluding header)
    """
    all_rows = []
    
    # Default columns if none provided
    if expected_columns is None:
        expected_columns = ['연번', '업종구분', '업체명', '소재지', '25년 배정인원', '관할청']
    
    if output_columns is None:
        output_columns = expected_columns.copy()
    
    # Add city column if extracting
    if extract_city and 'City' not in output_columns and '도시' not in output_columns:
        output_columns.append('도시')
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Processing PDF with {len(pdf.pages)} pages...")
        
        for page_num, page in enumerate(pdf.pages, 1):
            # Extract tables from the page
            tables = page.extract_tables()
            
            for table in tables:
                if not table or len(table) < 2:
                    continue
                
                # Try to find header row
                header_idx, header_row = find_header_row(table)
                
                # Determine which columns to extract
                column_mapping = {}
                if header_row:
                    column_mapping = match_columns(header_row, expected_columns)
                    start_idx = header_idx + 1 if header_idx is not None else 0
                else:
                    # If no header found, assume columns are in order
                    start_idx = 0
                    for idx in range(len(expected_columns)):
                        column_mapping[idx] = expected_columns[idx]
                
                # Process each data row in the table
                for row_idx in range(start_idx, len(table)):
                    row = table[row_idx]
                    
                    # Skip empty rows
                    if not row or all(not cell or not str(cell).strip() for cell in row):
                        continue
                    
                    # Check if this is another header row
                    row_text = ' '.join(str(cell or '') for cell in row)
                    if any(keyword in row_text for keyword in ['연번', '업종구분', '회사명']):
                        if row_idx > start_idx:  # Skip if it's a repeated header
                            continue
                    
                    # Clean up each cell
                    cleaned_row = []
                    for cell in row:
                        if cell is None:
                            cleaned_row.append('')
                        else:
                            # Clean up the cell text
                            cell_text = ' '.join(str(cell).split())
                            cleaned_row.append(cell_text)
                    
                    # Extract mapped columns or use all columns
                    if column_mapping:
                        extracted_data = {}
                        for idx, col_name in column_mapping.items():
                            if idx < len(cleaned_row):
                                extracted_data[col_name] = cleaned_row[idx]
                            else:
                                extracted_data[col_name] = ''
                        
                        # Build output row in correct order
                        output_row = []
                        for col in expected_columns:
                            output_row.append(extracted_data.get(col, ''))
                        
                        # Extract city if needed
                        if extract_city:
                            location_idx = None
                            for i, col in enumerate(expected_columns):
                                if '소재지' in col or '주소' in col or 'location' in col.lower():
                                    location_idx = i
                                    break
                            
                            if location_idx is not None and location_idx < len(output_row):
                                city = extract_city_from_location(output_row[location_idx])
                                output_row.append(city)
                            else:
                                output_row.append('')
                        
                        # Only add rows that have enough valid data
                        non_empty = sum(1 for cell in output_row if str(cell).strip())
                        if non_empty >= min_columns:
                            all_rows.append(output_row)
                    elif len(cleaned_row) >= min_columns:
                        # Use row as-is if no mapping
                        all_rows.append(cleaned_row[:len(output_columns)])
            
            print(f"  Page {page_num}/{len(pdf.pages)}: {len(all_rows)} total rows so far")
    
    # Write to CSV
    with open(output_csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(output_columns)
        
        # Write all data rows
        for row in all_rows:
            # Ensure row has correct number of columns
            while len(row) < len(output_columns):
                row.append('')
            writer.writerow(row[:len(output_columns)])
    
    print(f"\nSuccessfully wrote {len(all_rows)} rows to {output_csv_path}")
    return len(all_rows)


def main():
    """Main function to run the extended PDF to CSV conversion."""
    parser = argparse.ArgumentParser(
        description='Parse PDF tables to CSV with flexible column mapping',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse with default settings
  %(prog)s
  
  # Parse custom PDF with column mapping
  %(prog)s --pdf data/companies.pdf --output data/companies.csv \\
    --columns "번호" "회사명" "상세주소" "도시"
  
  # Extract city from location automatically
  %(prog)s --pdf data/firms.pdf --output data/firms.csv \\
    --extract-city-from-location
        """
    )
    
    parser.add_argument(
        '--pdf', '-p',
        default='data/2025_전문연구요원_인원배정.pdf',
        help='Path to input PDF file'
    )
    parser.add_argument(
        '--output', '-o',
        default='data/2025_전문연구요원_인원배정_parsed_extended.csv',
        help='Path to output CSV file'
    )
    parser.add_argument(
        '--columns', '-c',
        nargs='+',
        help='Expected column names (can use "source:target" format for renaming)'
    )
    parser.add_argument(
        '--extract-city-from-location',
        action='store_true',
        help='Automatically extract city name from location column'
    )
    parser.add_argument(
        '--min-columns',
        type=int,
        default=3,
        help='Minimum number of non-empty columns required for a valid row (default: 3)'
    )
    
    args = parser.parse_args()
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Resolve paths
    if not os.path.isabs(args.pdf):
        pdf_path = os.path.join(project_root, args.pdf)
    else:
        pdf_path = args.pdf
    
    if not os.path.isabs(args.output):
        output_csv_path = os.path.join(project_root, args.output)
    else:
        output_csv_path = args.output
    
    # Check if PDF exists
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at {pdf_path}")
    
    # Parse column mappings if provided
    expected_columns = None
    output_columns = None
    if args.columns:
        expected_columns, output_columns = parse_column_mapping(args.columns)
    
    # Parse PDF and create CSV
    num_rows = parse_pdf_to_csv_extended(
        pdf_path,
        output_csv_path,
        expected_columns=expected_columns,
        output_columns=output_columns,
        extract_city=args.extract_city_from_location,
        min_columns=args.min_columns
    )
    
    print(f"\n✓ Conversion complete!")
    print(f"  Input:  {pdf_path}")
    print(f"  Output: {output_csv_path}")
    print(f"  Rows:   {num_rows}")
    print(f"  Columns: {', '.join(output_columns) if output_columns else 'default'}")


if __name__ == '__main__':
    main()
