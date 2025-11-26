# histdem schema files

TEI-XML schema and conversion tools for the **Historical Demography in Southeastern Europe** project.

## Contents

- **[histdem.rng](histdem.rng)** - RelaxNG schema defining the TEI structure for demographic datasets
- **[147_tei.xml](147_tei.xml)** - Example TEI-XML file (Serbian 1863 Census)
- **[convert_csv_to_tei.py](convert_csv_to_tei.py)** - Python script to convert CSV metadata to TEI-XML
- **[validate_csv_data.py](validate_csv_data.py)** - Validation script for CSV data and file references
- **[compress_images.py](compress_images.py)** - Image compression tool (max 1MB per image)
- **[CLAUDE.md](CLAUDE.md)** - Complete documentation: schema architecture, conversion workflow, and developer guidance

## Quick Start

### 1. Validate CSV Data

```bash
python validate_csv_data.py histdem-data.csv
```

Validates:
- Required fields present
- File references exist in dataset folders
- Data format correctness

### 2. Convert CSV to TEI-XML

```bash
python convert_csv_to_tei.py histdem-data.csv output
```

Generates TEI-XML files for all datasets defined in the CSV.

### 3. Compress Images (if needed)

```bash
# Preview what would be compressed
python compress_images.py all --dry-run

# Compress all images over 1MB
python compress_images.py all
```

Requires: `pip install Pillow`

### 4. Validate TEI Files

```bash
xmllint --noout --relaxng histdem.rng output/147_tei.xml
```

## Data Folder Structure

Each dataset has its own folder containing CSV data files, PDFs, and images. These folders are synchronized from a shared Google Drive folder and are not tracked in git:

```
datafile_147_Serbia_1863/
datafile_21_Albania_1918/
datafile_152_Hungary_1869/
datafile_153_Rhodope_mountains_around_1900/
datafile_154_Dalmatia_1674/
datafile_164_Istanbul_1907/
datafile_165_Istanbul_1885/
datafile_234_Wallachia_1838/
datafile_262_Montenegro_1879/
datafile_266_Armenians_in_Istanbul_1907/
```

## Documentation

See [CLAUDE.md](CLAUDE.md) for complete documentation on:
- CSV to TEI conversion workflow
- Schema architecture and structure
- Validation procedures
- Image compression
- Developer guidance

## Project

Part of the research project "Demography and Society in Historical Southeastern Europe" funded by the Austrian Science Fund (FWF, project no. P 38285-G).

**Host Institutions:**
- Digital Humanities Craft OG
- Institut für Digitale Geisteswissenschaften, Universität Graz
