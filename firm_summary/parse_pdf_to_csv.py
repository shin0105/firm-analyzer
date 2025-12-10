#!/usr/bin/env python3
"""
Parse the 2025_전문연구요원_인원배정.pdf file and convert it to CSV format.

This script extracts table data from the PDF and creates a CSV file with the same
structure as the existing 2025_전문연구요원_인원배정.csv file.

Usage:
    python3 firm_summary/parse_pdf_to_csv.py

Output:
    Creates: data/2025_전문연구요원_인원배정_parsed.csv
    
The CSV will have the following columns:
    - 연번 (Number)
    - 업종구분 (Industry Type)
    - 업체명 (Company Name)
    - 소재지 (Location)
    - 25년 배정인원 (2025 Allocation)
    - 관할청 (Jurisdiction)
"""

import os
import csv
import pdfplumber


def parse_pdf_to_csv(pdf_path, output_csv_path):
    """
    Parse a PDF file containing research personnel allocation data and convert to CSV.
    
    Args:
        pdf_path: Path to the input PDF file
        output_csv_path: Path to the output CSV file
        
    Returns:
        Number of data rows extracted (excluding header)
    """
    all_rows = []
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Processing PDF with {len(pdf.pages)} pages...")
        
        for page_num, page in enumerate(pdf.pages, 1):
            # Extract tables from the page
            tables = page.extract_tables()
            
            for table in tables:
                if not table:
                    continue
                
                # Process each row in the table
                for row_idx, row in enumerate(table):
                    # Skip empty rows
                    if not row or all(not cell or not str(cell).strip() for cell in row):
                        continue
                    
                    # Check if this is a header row (contains "연번" or similar)
                    row_text = ' '.join(str(cell or '') for cell in row)
                    if '연번' in row_text and '업종구분' in row_text:
                        # Skip header rows (we'll add our own header)
                        continue
                    
                    # Clean up each cell
                    cleaned_row = []
                    for cell in row:
                        if cell is None:
                            cleaned_row.append('')
                        else:
                            # Clean up the cell text - remove newlines and extra spaces
                            cell_text = str(cell).strip().replace('\n', ' ')
                            cleaned_row.append(cell_text)
                    
                    # Only add rows that have at least 6 columns and start with a number
                    if len(cleaned_row) >= 6 and cleaned_row[0].strip().isdigit():
                        all_rows.append(cleaned_row[:6])  # Take only first 6 columns
            
            print(f"  Page {page_num}/{len(pdf.pages)}: {len([r for r in all_rows])} total rows so far")
    
    # Write to CSV
    with open(output_csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['연번', '업종구분', '업체명', '소재지', '25년 배정인원', '관할청'])
        
        # Write all data rows
        for row in all_rows:
            writer.writerow(row)
    
    print(f"\nSuccessfully wrote {len(all_rows)} rows to {output_csv_path}")
    return len(all_rows)


def main():
    """Main function to run the PDF to CSV conversion."""
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "data")
    
    # Define paths
    pdf_path = os.path.join(data_dir, "2025_전문연구요원_인원배정.pdf")
    output_csv_path = os.path.join(data_dir, "2025_전문연구요원_인원배정_parsed.csv")
    
    # Check if PDF exists
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        return
    
    # Parse PDF and create CSV
    num_rows = parse_pdf_to_csv(pdf_path, output_csv_path)
    
    print(f"\n✓ Conversion complete!")
    print(f"  Input:  {pdf_path}")
    print(f"  Output: {output_csv_path}")
    print(f"  Rows:   {num_rows}")


if __name__ == '__main__':
    main()
