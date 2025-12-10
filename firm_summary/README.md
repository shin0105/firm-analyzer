# Firm Summary Tools

This directory contains tools for processing and analyzing research personnel allocation data.

## PDF to CSV Parser

### parse_pdf_to_csv.py

A utility to parse the `2025_전문연구요원_인원배정.pdf` file and convert it to CSV format.

#### Features

- Extracts table data from all 53 pages of the PDF
- Outputs CSV with the same structure as the original data file
- Normalizes whitespace and handles embedded newlines
- Validates data integrity during extraction

#### Usage

```bash
python3 firm_summary/parse_pdf_to_csv.py
```

#### Output

Creates: `data/2025_전문연구요원_인원배정_parsed.csv`

The CSV contains the following columns:
- **연번** (Number): Sequential ID number
- **업종구분** (Industry Type): Type of research institution
- **업체명** (Company Name): Name of the institution
- **소재지** (Location): Address
- **25년 배정인원** (2025 Allocation): Number of personnel allocated for 2025
- **관할청** (Jurisdiction): Supervising authority

#### Dependencies

Requires `pdfplumber` library (included in requirements.txt):

```bash
pip install pdfplumber
```

#### Validation

The parser has been validated to extract all 1895 data rows correctly from the PDF, matching the structure of the existing CSV file.

## Other Tools

### generate_firms_data.py

Converts CSV data to JavaScript format for the web viewer with geocoded coordinates.

### filter_seoul_firms.py

Filters firms located in Seoul from the dataset.
