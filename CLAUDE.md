# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This repository contains TEI-XML schema files and example data for the **histdem** (Historical Demography in Southeastern Europe) project. The project aims to create the largest European database of historical census data for Southeastern Europe, making it available as open access for international research.

The repository consists of:
- **histdem.rng**: RelaxNG schema defining the TEI structure for demographic datasets
- **147_tei.xml**: Example TEI-XML file demonstrating a Serbian census dataset from 1863
- **convert_csv_to_tei.py**: Python script to convert CSV metadata to TEI-XML files
- **validate_csv_data.py**: Validation script for CSV data format and file references
- **compress_images.py**: Image compression tool to reduce images to max 1MB

## Schema Architecture

### RelaxNG Schema Structure (histdem.rng)

The schema defines a TEI document structure with the following main components:

**TEI Header (`teiHeader`):**
- **fileDesc**: Core bibliographic information
  - `titleStmt`: Dataset title, editors, funding information
  - `publicationStmt`: Publisher, authority, distributor, license, PID
  - `seriesStmt`: Series title(s) and project director
  - `sourceDesc`: Multiple `bibl` elements with types:
    - `type="citation"`: How to cite the dataset
    - `type="data"`: CSV data files (codes and labels)
    - `type="additional"`: Supporting materials (PDFs, images, maps)

- **encodingDesc**: Project description and prefix definitions
  - `projectDesc`: Research questions and methodology (in English)
  - `listPrefixDef`: Namespace prefixes (marcrelator, dcterms, Wikidata)

- **profileDesc**: Language and classification
  - `langUsage`: ISO 639-1 language codes
  - `textClass`: Keywords/tags for filtering

**TEI Text (`text`):**
- `body`: Contains dataset description
  - `head`: Summary of dataset (e.g., person/household counts)
  - `p`: Descriptive paragraphs about data provenance and methodology
  - `note`: Additional notes about data peculiarities

### Key Schema Patterns

**Reusable Elements (defined patterns):**
- `title`: Multilingual titles with optional `@level`, `@ref`, `@xml:lang`
- `persName`: Structured personal names (forename + surname)
- `orgName`: Organizations with optional `@corresp` or `@ref` URIs
- `respStmt`: Responsibility statements with MARC relator codes
- `date`: Temporal information with `@when`, `@from`, `@to`, or `@ana`
- `publisher`: Publishing organizations
- `p`: Simple paragraph text

**Source Description Structure:**
The `sourceDesc` element contains multiple `bibl` elements that serve different purposes:
- Geographic provenance: `country` and optional `region` with Wikidata references
- Citation information: Authors, titles, publishers, dates
- Resource references: `rs` elements with types (citation_recommendation, codes, labels, sample, literature, scan, map)
- Media references: `graphic` (images) and `media` (CSV, PDF) elements with `@url` and `@mimeType`

### Controlled Vocabularies

**MARC Relator Codes** (via `@ana` attribute):
- `marcrelator:edt` - Editor
- `marcrelator:mrk` - Markup editor
- `marcrelator:fnd` - Funder
- `marcrelator:his` - Host institution
- `marcrelator:rps` - Repository
- `marcrelator:pdr` - Project director
- `marcrelator:rth` - Research team head
- `marcrelator:prp` - Production place (for geographic entities)
- `marcrelator:pup` - Publication place

**DCTerms** (for dates):
- `dcterms:created` - Date of source creation
- `dcterms:issued` - Date of publication

**Wikidata** (geographic references):
- Use `wd:Q[ID]` pattern for `@ref` attributes on geographic entities
- Example: `wd:Q403` for Serbia

## Validation

The example file [147_tei.xml](147_tei.xml) validates against [histdem.rng](histdem.rng) using the processing instruction:
```xml
<?xml-model href="histdem.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>
```

To validate XML files against the RelaxNG schema, use an XML validator that supports RelaxNG (e.g., jing, xmllint, oXygen XML Editor).

## Data Types and Attributes

**Common data types:**
- Geographic identifiers: Wikidata QIDs (NMTOKEN format)
- Language codes: ISO 639-1 (language datatype)
- URIs: Full URLs for external references (anyURI)
- Dates: Integer years or NMTOKEN for formatted dates

**Required vs. Optional:**
- `teiHeader/@xml:lang` is required
- Most nested elements have specific cardinality (oneOrMore, optional, zeroOrMore)
- PID in `publicationStmt` must have `type="PID"` and format `o:histdem.[number]`

## CSV to TEI Conversion Workflow

This section describes the complete workflow for converting histdem dataset metadata from Google Sheets/CSV to TEI-XML format.

### Workflow Overview

The workflow consists of three main steps:

1. **Export** - Export dataset metadata from Google Sheets to CSV
2. **Convert** - Run Python conversion script to generate TEI-XML files
3. **Review & Refine** - Manually review and complete the generated TEI files

### Step 1: Export from Google Sheets

**Source Spreadsheet:**
- URL: https://docs.google.com/spreadsheets/d/1F_InXXWhiLX8rpeJdVhA9EF9mGA1800UFh0BnQtaArM

**CSV Structure:**
- **Column 1**: Field name (German)
- **Column 2**: Field description (German)
- **Columns 3+**: One column per dataset

Each dataset column contains values for all the fields defined in column 1.

**Export Instructions:**
1. Open the Google Sheets document
2. Go to `File > Download > Comma Separated Values (.csv)`
3. Save as `histdem-data.csv` in the schema directory

### Step 2: Convert CSV to TEI-XML

**Requirements:**
- Python 3.7+
- Standard library only (no additional packages needed)

**Running the Conversion Script:**

```bash
python convert_csv_to_tei.py histdem-data.csv [output_dir]
```

**Parameters:**
- `histdem-data.csv` - Input CSV file with dataset metadata
- `output_dir` - (Optional) Output directory for generated TEI files (default: `output`)

**Example:**
```bash
python convert_csv_to_tei.py histdem-data.csv output
```

**What the Script Does:**

The script processes each dataset column in the CSV and generates a complete TEI-XML file that conforms to [histdem.rng](histdem.rng). For each dataset, it:

1. **Loads template metadata** from [147_tei.xml](147_tei.xml):
   - Standard publication information (publisher, authority, distributor)
   - Funder details
   - Series titles and project leadership
   - Project description paragraphs
   - Prefix definitions

2. **Extracts metadata** from CSV fields:
   - Basic dataset information (ID, title, country, region, year)
   - Person/household counts
   - PID (Persistent Identifier)
   - Data files (CSV codes and labels)
   - Additional files (PDFs, images)
   - Citation information
   - Keywords and language codes
   - Descriptions and notes

3. **Intelligently processes data**:
   - **Parses authors** from citation text automatically
   - **Converts markdown** formatting (`*italic*` → `<hi rend="italic">`)
   - **Looks up Wikidata QIDs** for countries and regions automatically
   - Determines file MIME types from extensions
   - Classifies resource types (sample, literature, scan, map)

4. **Maps CSV fields to TEI elements**:
   - `Datensatz ID` → `<idno type="PID">`
   - `Datensatz Titel` → `<title>` elements
   - `Land`, `Region` → `<country>`, `<region>` with Wikidata refs
   - `Jahr`, `Datum Von`, `Datum Bis` → `<date>` with appropriate attributes
   - `CSV Codes`, `CSV Labels` → `<media>` elements in data bibl
   - `Zusatzdatei N` → `<media>` elements (PDFs) in additional bibl
   - `Bild N` → `<graphic>` or `<media>` elements (images/maps)
   - `Zitierempfehlung` → Citation recommendation in `<rs type="citation_recommendation">`
   - `Schlagwörter` → Keywords in `<term>` elements
   - `Sprachcodes` → `<language>` elements with ISO 639-1 codes
   - `Überschrift` → `<head>` in body
   - `Beschreibung` → `<p>` in body
   - `Anmerkungen` → `<note>` in body

5. **Generates structured TEI-XML**:
   - Adds XML processing instruction with schema reference
   - Creates proper TEI namespace declarations
   - Structures all elements according to histdem.rng schema
   - Formats with proper indentation for readability

6. **Outputs individual TEI files**:
   - Named as `{dataset_id}_tei.xml` (e.g., `147_tei.xml`)
   - Ready for validation and further editing

**Output:**

The script creates one TEI-XML file per dataset in the output directory:
- `147_tei.xml` - Serbia 1863 Census
- `21_tei.xml` - Albania 1918 Census
- `262_tei.xml` - Montenegro 1879 Census
- `266_tei.xml` - Istanbul Armenians 1907 Register

Each file includes:
- Complete TEI header with all metadata
- Standard project description (from template)
- Dataset-specific body text
- Processing instruction for schema validation

### Step 3: Review & Refine Generated TEI Files

The generated TEI files are nearly complete and production-ready! Only minimal manual review is recommended.

**Automatically Handled (No Editing Needed!):**

The script automatically sets all of these:

✅ **XML Encoder**: Set to Christian Steiner
✅ **Template metadata**: Publisher, authority, distributor, funder, series titles, project director
✅ **Editor names**: Parsed from citation text and added to `<editor>` elements
✅ **Authors**: Extracted from citation and added to `<author>` elements
✅ **Wikidata QIDs**: Read from CSV fields "Land Wikidata" and "Region Wikidata", with fallback to built-in mapping
  - CSV-based: QIDs are stored directly in the CSV file for each dataset
  - Fallback mappings: Serbia (Q403), Albania (Q222), Montenegro (Q236), Turkey (Q43), Bulgaria (Q219), Romania (Q218), Croatia (Q224), Hungary (Q28), Slovakia (Q214), Istanbul (Q406), Rhodope mountains (Q6489), Wallachia (Q171393), Dubrovnik (Q1722)
✅ **Markdown to TEI**: `*italic*` automatically converted to `<hi rend="italic">`
✅ **Project description**: 5 standard paragraphs from template
✅ **Namespace prefixes**: marcrelator, dcterms, Wikidata

**Recommended Manual Review:**

Only review these items for accuracy:

**1. Author Name Parsing**

The script parses author names from citation text by splitting on periods and commas. This works well for most cases, but complex names may need adjustment.

Example of potential issue:
- Citation: "Joel M. Halpern and others..."
- Parsed as: "Joel M" (forename), "Halpern" (surname) ← Missing the period after "M"

Action: Review the `<editor>` and `<author>` elements. If names are incorrectly split, edit them manually.

**2. Unknown Geographic Locations**

If a location isn't in the Wikidata mapping, it will be marked as `wd:QXXX`.

Action: Search for `wd:QXXX` in the file. Look up the correct Wikidata QID at https://www.wikidata.org and replace it.

**Optional Enhancements:**

**Add Multiple Language Titles:**
If the dataset has titles in multiple languages, add them with `xml:lang` attributes:

```xml
<title xml:lang="de">Serbische Volkszählung von 1863</title>
<title xml:lang="en">1863 Census of Serbia</title>
```

**Refine Resource Type Classification:**
Review the `type` attribute on `<rs>` elements in additional files:
- `sample` - Sample/overview documents
- `literature` - Academic publications, papers
- `scan` - Manuscript scans, source images
- `map` - Geographic maps

**Split Long Descriptions into Multiple Paragraphs:**
If the description is very long, split it into multiple `<p>` elements for better readability.

### Validation

After completing manual edits, validate the TEI files against the RelaxNG schema:

**Using xmllint (command line):**
```bash
xmllint --noout --relaxng histdem.rng output/147_tei.xml
```

**Using oXygen XML Editor:**
1. Open the TEI file
2. The schema is automatically detected via processing instruction
3. Check validation panel for errors

**Using jing:**
```bash
jing histdem.rng output/147_tei.xml
```

### Adding New Datasets

To add new datasets to the workflow:

1. **Update Google Sheets**: Add a new column for the dataset with all required fields filled in
2. **Export to CSV**: Download updated CSV file
3. **Run conversion**: Execute the Python script again
4. **Review**: Complete manual edits as described above
5. **Validate**: Ensure the new file conforms to the schema

### Field Mapping Reference

| CSV Field | TEI Location | Notes |
|-----------|--------------|-------|
| Datensatz ID | `idno[@type="PID"]` | Format: `o:histdem.{ID}` |
| Datensatz Titel | `title` (multiple locations) | Main title of dataset |
| Land | `country` | Country name |
| Land Wikidata | `country/@ref` | Wikidata QID (e.g., Q403) |
| Region | `region` | Region name (optional) |
| Region Wikidata | `region/@ref` | Wikidata QID for region |
| Jahr | `date[@when]` | Census year |
| Datum Von | `date[@from]` | Start date if range |
| Datum Bis | `date[@to]` | End date if range |
| Anzahl Personen | `head` | Included in head text |
| Anzahl Haushalte | `head` | Included in head text |
| PID | `idno[@type="PID"]` | Persistent identifier |
| CSV Codes | `bibl[@type="data"]/rs[@type="codes"]/media` | Data file with codes |
| CSV Labels | `bibl[@type="data"]/rs[@type="labels"]/media` | Data file with labels |
| Zusatzdatei N | `bibl[@type="additional"]/rs/media` | PDF files |
| Bild N | `bibl[@type="additional"]/rs/graphic` or `media` | Images or maps |
| Zitierempfehlung | `bibl[@type="citation"]/rs[@type="citation_recommendation"]` | How to cite |
| Literatur N | `bibl[@type="additional"]/rs[@type="literature"]/title` | References without PDFs |
| Schlagwörter | `textClass/keywords/list/item/term` | Comma-separated keywords |
| Sprachcodes | `langUsage/language[@ident]` | ISO 639-1 codes |
| Überschrift | `text/body/head` | Summary line |
| Beschreibung | `text/body/p` | Full description |
| Anmerkungen | `text/body/note` | Additional notes |

### Troubleshooting

**Script fails with encoding error:**
- Ensure CSV file is saved as UTF-8 encoding
- Check for special characters in the CSV

**Generated XML doesn't validate:**
- Check that all required fields are present in CSV
- Verify namespace declarations are correct
- Ensure all MARC relator codes are valid

**Missing data in output:**
- Verify CSV column headers match expected format
- Check that field names in column 1 exactly match the script's expectations
- Ensure there are no extra spaces or special characters in field names

### Alternative: Manual TEI Creation

If you need to create TEI files manually without using the conversion script:

1. Start with the example file [147_tei.xml](147_tei.xml) as a template
2. Update the PID number in both `<idno type="PID">` and the title
3. Fill in geographic provenance with Wikidata references
4. Include all media files (CSV data, PDFs, images) in `sourceDesc/bibl[@type="additional"]`
5. Write or update the project description in English in `encodingDesc/projectDesc`
6. Add descriptive text about the dataset in the `text/body` section
7. Include any data peculiarities or methodological notes in the `note` element

## Project Context

**Research Focus:** Historical demography in Southeastern Europe up to World War 1

**Key Research Questions:**
- Regional differences in fertility and nuptiality
- Household structures and cohabitation patterns
- Family patriarchal structures
- Occupational group differences in marriage patterns and household formation

**Data Coding:** Microdata coded based on IPUMS, NAPP, Mosaic, and HISCO systems for international comparability

**Analysis Methods:** Child-woman ratio, SMAM (Singulate Mean Age at Marriage), age gap between spouses, patriarchy index, dyadic relationship measures

## Image Compression

The `compress_images.py` script reduces image file sizes to a maximum of 1MB for repository ingestion.

### Requirements

```bash
pip install Pillow
```

### Usage

```bash
# Preview what would be compressed (no changes made)
python compress_images.py all --dry-run

# Compress all images in all dataset folders
python compress_images.py all

# Compress images for a specific dataset
python compress_images.py 147
```

### How It Works

1. Scans dataset folders for image files (JPG, PNG, TIF)
2. Skips images already under 1MB
3. For oversized images:
   - Progressively reduces JPEG quality (95% → 60%)
   - If still too large, resizes to 90% dimensions
4. Creates `.backup` files before modifying originals
5. Reports space saved and quality settings used

### Supported Formats

- JPEG (.jpg, .jpeg, .JPG, .JPEG)
- PNG (.png, .PNG)
- TIFF (.tif, .tiff, .TIF, .TIFF)

## CSV Data Validation

The `validate_csv_data.py` script validates the CSV metadata file before conversion.

### Usage

```bash
python validate_csv_data.py histdem-data.csv
```

### What It Validates

1. **Required fields**: Checks all mandatory CSV fields are present
2. **File existence**: Verifies all referenced files exist in dataset folders:
   - CSV Codes and Labels
   - Zusatzdateien 1-10 (additional PDF files)
   - Bilder 1-5 (images)
3. **Data format**: Validates field formats (IDs, dates, language codes)

### Dataset Folder Mapping

The dataset folders (`datafile_*`) are synchronized from a shared Google Drive folder and are not tracked in git. Each folder contains CSV data files, PDFs, and images for one dataset.

The scripts use a mapping to locate files for each dataset:

| Dataset ID | Folder Name |
|------------|-------------|
| 147 | datafile_147_Serbia_1863 |
| 21 | datafile_21_Albania_1918 |
| 152 | datafile_152_Hungary_1869 |
| 153 | datafile_153_Rhodope_mountains_around_1900 |
| 154 | datafile_154_Dalmatia_1674 |
| 164 | datafile_164_Istanbul_1907 |
| 165 | datafile_165_Istanbul_1885 |
| 234 | datafile_234_Wallachia_1838 |
| 262 | datafile_262_Montenegro_1879 |
| 266 | datafile_266_Armenians_in_Istanbul_1907 |

## XML ID Sanitization

The conversion script automatically sanitizes filenames to create valid XML IDs:

- Removes file extensions (.csv, .pdf, .jpg, etc.)
- Replaces spaces and special characters with underscores
- Prepends underscore if ID starts with a digit (XML requirement)

Example: `1863 sample3.jpg` → `_1863_sample3`

## File Path Handling

Since TEI files are generated in the `output/` subdirectory, all file references use relative paths with `../` prefix:

```xml
<media url="../datafile_147_Serbia_1863/file.csv" />
```
