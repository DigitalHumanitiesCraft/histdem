#!/usr/bin/env python3
"""
Convert histdem CSV data to TEI-XML files conforming to histdem.rng schema.
Uses 147_tei.xml as a template to extract standard metadata.

Usage:
    python convert_csv_to_tei_v2.py histdem-data.csv [output_dir]
"""

import csv
import sys
import os
import re
from pathlib import Path
from xml.dom import minidom
import xml.etree.ElementTree as ET

# TEI namespace
TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"

# Register namespaces
ET.register_namespace('', TEI_NS)

# Folder name mapping for each dataset
# Maps dataset ID to folder name containing the files
DATASET_FOLDERS = {
    '147': 'datafile_147_Serbia_1863',
    '21': 'datafile_21_Albania_1918',
    '262': 'datafile_262_Montenegro_1879',
    '266': 'datafile_266_Armenians_in_Istanbul_1907',
    '153': 'datafile_153_Rhodope_mountains_around_1900',
    '234': 'datafile_234_Wallachia_1838',
    '154': 'datafile_154_Dalmatia_1674',
    '164': 'datafile_164_Istanbul_1907',
    '165': 'datafile_165_Istanbul_1885',
    '152': 'datafile_152_Hungary_1869',
}

# List to collect conversion warnings/errors
conversion_warnings = []


def extract_template_data(template_file):
    """Extract reusable metadata from template TEI file."""
    template_data = {}

    if not Path(template_file).exists():
        print(f"Warning: Template file {template_file} not found")
        return template_data

    try:
        tree = ET.parse(template_file)
        root = tree.getroot()

        # Helper to find elements with namespace
        def find_elem(parent, tag):
            return parent.find(f'{{{TEI_NS}}}{tag}')

        def findall_elem(parent, tag):
            return parent.findall(f'.//{{{TEI_NS}}}{tag}')

        # Extract publicationStmt structure
        pub_stmt = findall_elem(root, 'publicationStmt')
        if pub_stmt:
            pub_stmt = pub_stmt[0]

            # Publisher
            publisher = find_elem(pub_stmt, 'publisher')
            if publisher is not None:
                org_name = find_elem(publisher, 'orgName')
                if org_name is not None:
                    template_data['publisher_name'] = org_name.text
                    template_data['publisher_corresp'] = org_name.get('corresp', '')

            # Authority
            authority = find_elem(pub_stmt, 'authority')
            if authority is not None:
                org_name = find_elem(authority, 'orgName')
                if org_name is not None:
                    template_data['authority_name'] = org_name.text
                    template_data['authority_corresp'] = org_name.get('corresp', '')

            # Distributor
            distributor = find_elem(pub_stmt, 'distributor')
            if distributor is not None:
                org_name = find_elem(distributor, 'orgName')
                if org_name is not None:
                    template_data['distributor_name'] = org_name.text
                    template_data['distributor_ref'] = org_name.get('ref', '')

            # License
            availability = find_elem(pub_stmt, 'availability')
            if availability is not None:
                licence = find_elem(availability, 'licence')
                if licence is not None:
                    template_data['license_text'] = licence.text
                    template_data['license_target'] = licence.get('target', '')

            # Publication place
            pub_place = find_elem(pub_stmt, 'pubPlace')
            if pub_place is not None:
                template_data['pub_place'] = pub_place.text

        # Extract funder info
        funder_elem = findall_elem(root, 'funder')
        if funder_elem:
            funder = funder_elem[0]
            org_name = find_elem(funder, 'orgName')
            num = find_elem(funder, 'num')
            if org_name is not None:
                template_data['funder_name'] = org_name.text
                template_data['funder_ref'] = org_name.get('ref', '')
            if num is not None:
                template_data['funder_num'] = num.text

        # Extract series titles
        series_stmt = findall_elem(root, 'seriesStmt')
        if series_stmt:
            series_stmt = series_stmt[0]
            titles = findall_elem(series_stmt, 'title')
            template_data['series_titles'] = []
            for title in titles:
                template_data['series_titles'].append({
                    'text': title.text,
                    'lang': title.get(f'{{{XML_NS}}}lang', ''),
                    'ref': title.get('ref', '')
                })

            # Project director and research team
            resp_stmts = findall_elem(series_stmt, 'respStmt')
            for resp_stmt in resp_stmts:
                ana = resp_stmt.get('ana', '')
                resp = find_elem(resp_stmt, 'resp')

                if 'pdr' in ana:  # Project director
                    pers_name = find_elem(resp_stmt, 'persName')
                    if pers_name is not None:
                        forename = find_elem(pers_name, 'forename')
                        surname = find_elem(pers_name, 'surname')
                        if forename is not None and surname is not None:
                            template_data['project_director'] = {
                                'forename': forename.text,
                                'surname': surname.text,
                                'resp': resp.text if resp is not None else 'Project director'
                            }
                elif 'rth' in ana:  # Research team head
                    org_name = find_elem(resp_stmt, 'orgName')
                    if org_name is not None:
                        template_data['research_team'] = {
                            'name': org_name.text,
                            'ref': org_name.get('ref', ''),
                            'resp': resp.text if resp is not None else 'Software developement'
                        }

        # Extract project description paragraphs
        project_desc = findall_elem(root, 'projectDesc')
        if project_desc:
            project_desc = project_desc[0]
            paragraphs = findall_elem(project_desc, 'p')
            template_data['project_desc_paragraphs'] = [p.text for p in paragraphs if p.text]

            # Also get the ab/ref element
            ab = find_elem(project_desc, 'ab')
            if ab is not None:
                ref = find_elem(ab, 'ref')
                if ref is not None:
                    template_data['project_context_ref'] = {
                        'text': ref.text,
                        'target': ref.get('target', ''),
                        'type': ref.get('type', '')
                    }

        print(f"[OK] Loaded template data from {template_file}")

    except Exception as e:
        print(f"Warning: Could not parse template file: {e}")

    return template_data


def parse_csv_column(csv_file):
    """Parse the CSV file and return dataset dictionaries."""
    datasets = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Get header row (dataset names in columns 2+)
    dataset_headers = rows[1][2:]  # Skip first two columns
    num_datasets = len([h for h in dataset_headers if h.strip()])

    # Create dataset dictionaries
    for i in range(num_datasets):
        datasets.append({})

    # Parse each row
    for row in rows[4:]:  # Skip header rows
        if len(row) < 2 or not row[0].strip():
            continue

        field_name = row[0].strip()

        # Store data for each dataset column
        for i in range(num_datasets):
            col_idx = i + 2  # Offset for first two columns
            if col_idx < len(row):
                value = row[col_idx].strip()
                if value:
                    datasets[i][field_name] = value

    return datasets


def create_tei_element(tag, text=None, attrib=None):
    """Create a TEI element with namespace."""
    elem = ET.Element(f"{{{TEI_NS}}}{tag}", attrib or {})
    if text:
        elem.text = text
    return elem


def get_dataset_folder(dataset_id):
    """Get the folder name for a dataset ID."""
    return DATASET_FOLDERS.get(str(dataset_id))


def add_folder_prefix(filename, dataset_id):
    """Add folder prefix to filename if folder mapping exists.

    Uses ../ prefix since TEI files are in output/ subdirectory.
    """
    folder = get_dataset_folder(dataset_id)
    if folder and filename:
        return f"../{folder}/{filename}"
    return filename


def sanitize_xml_id(filename):
    """Sanitize filename to create a valid XML ID.

    XML IDs must:
    - Start with a letter or underscore (not a digit)
    - Contain only letters, digits, hyphens, underscores, and periods
    """
    if not filename:
        return "id_unknown"

    # Remove file extension and replace problematic characters
    id_str = filename.replace('.csv', '').replace('.pdf', '').replace('.jpg', '').replace('.JPG', '').replace('.jpeg', '').replace('.png', '')
    # Replace spaces and other characters with underscores
    id_str = id_str.replace(' ', '_').replace('.', '_').replace('-', '_')

    # Ensure it starts with a letter or underscore
    if id_str and id_str[0].isdigit():
        id_str = f"_{id_str}"

    return id_str if id_str else "id_unknown"


def parse_file_entry(entry, field_name="", dataset_id=""):
    """Parse 'filename - title' format and return (filename, title).

    If title is missing, logs a warning and returns filename with None title.
    """
    if not entry or entry.strip() == '':
        return None, None

    entry = entry.strip()

    if ' - ' not in entry:
        # Missing title - log warning but continue with filename
        warning = f"WARNUNG Dataset {dataset_id}: {field_name} - Fehlender Titel (Format sollte sein: 'dateiname - Titel'). Gefunden: '{entry}'"
        conversion_warnings.append(warning)
        return entry, None

    parts = entry.split(' - ', 1)
    filename = parts[0].strip()
    title = parts[1].strip()

    if not filename:
        warning = f"FEHLER Dataset {dataset_id}: {field_name} - Leerer Dateiname vor ' - '"
        conversion_warnings.append(warning)
        return None, None

    if not title:
        warning = f"WARNUNG Dataset {dataset_id}: {field_name} - Leerer Titel nach ' - '"
        conversion_warnings.append(warning)
        return filename, None

    return filename, title


def parse_citation_authors(citation_text):
    """Extract author names from citation text."""
    authors = []

    # Try to extract authors before the first period or before "19" (year)
    # Common patterns: "Author1, Author2, and Author3. *Title*"
    if not citation_text:
        return authors

    # Split at first period or before year/title
    match = re.match(r'^([^.]+?)\.', citation_text)
    if not match:
        # Try to find text before italicized title
        match = re.match(r'^([^*]+)\*', citation_text)

    if match:
        author_part = match.group(1).strip()
        # Split by comma and "and"
        author_part = author_part.replace(' and ', ', ')
        author_names = [a.strip() for a in author_part.split(',') if a.strip()]
        authors = author_names

    return authors


def markdown_to_tei(text):
    """Convert markdown formatting to TEI elements."""
    if not text:
        return None

    # Convert *text* to <hi rend="italic">text</hi>
    # We need to return a list of text and elements
    parts = []
    current_pos = 0

    for match in re.finditer(r'\*([^*]+)\*', text):
        # Add text before match
        if match.start() > current_pos:
            parts.append(('text', text[current_pos:match.start()]))

        # Add italic element
        parts.append(('italic', match.group(1)))
        current_pos = match.end()

    # Add remaining text
    if current_pos < len(text):
        parts.append(('text', text[current_pos:]))

    return parts


def add_mixed_content(parent, text):
    """Add text with markdown formatting to parent element."""
    if not text:
        return

    parts = markdown_to_tei(text)
    if not parts:
        parent.text = text
        return

    for i, (part_type, content) in enumerate(parts):
        if part_type == 'text':
            if i == 0:
                parent.text = content
            else:
                # Add to tail of previous element
                if len(parent) > 0:
                    if parent[-1].tail:
                        parent[-1].tail += content
                    else:
                        parent[-1].tail = content
        elif part_type == 'italic':
            hi = create_tei_element('hi', content, attrib={'rend': 'italic'})
            parent.append(hi)


def add_title(parent, title_text, level=None, lang=None, ref=None):
    """Add a title element."""
    attrib = {}
    if level:
        attrib['level'] = level
    if lang:
        attrib[f'{{{XML_NS}}}lang'] = lang
    if ref:
        attrib['ref'] = ref

    title = create_tei_element('title', title_text, attrib)
    parent.append(title)
    return title


def add_person_name(parent, forename, surname):
    """Add a persName element."""
    pers_name = create_tei_element('persName')
    pers_name.append(create_tei_element('forename', forename))
    pers_name.append(create_tei_element('surname', surname))
    parent.append(pers_name)
    return pers_name


def get_wikidata_qid(location_name):
    """Map location names (countries/regions) to Wikidata QIDs."""
    mapping = {
        # Countries
        'Serbia': 'Q403',
        'Albania': 'Q222',
        'Montenegro': 'Q236',
        'Turkey': 'Q43',
        'Bosnia': 'Q225',
        'Greece': 'Q41',
        'Bulgaria': 'Q219',
        'Romania': 'Q218',
        'Croatia': 'Q224',
        # Regions/Cities
        'Istanbul': 'Q406',
        'Kruševac': 'Q201442',
        'Krušev ac': 'Q201442',  # Handle potential encoding issues
    }
    return mapping.get(location_name, None)


def create_tei_document(dataset, template_data):
    """Create a complete TEI document from dataset dictionary using template data."""

    # Root TEI element
    root = create_tei_element('TEI')

    # ========== TEI HEADER ==========
    header = create_tei_element('teiHeader', attrib={f'{{{XML_NS}}}lang': 'en'})
    root.append(header)

    # --- fileDesc ---
    file_desc = create_tei_element('fileDesc')
    header.append(file_desc)

    # titleStmt
    title_stmt = create_tei_element('titleStmt')
    file_desc.append(title_stmt)

    dataset_title = dataset.get('Datensatz Titel', 'Untitled Dataset')
    dataset_id = dataset.get('Datensatz ID', '000')
    add_title(title_stmt, f"Nr. {dataset_id}: {dataset_title}")

    # Extract editors from citation
    citation_text = dataset.get('Zitierempfehlung', '')
    author_names = parse_citation_authors(citation_text)

    if author_names:
        for author_name in author_names[:3]:  # Limit to first 3 editors
            # Try to split into first/last name
            name_parts = author_name.strip().split()
            if len(name_parts) >= 2:
                forename = ' '.join(name_parts[:-1])
                surname = name_parts[-1]
                editor = create_tei_element('editor', attrib={'ana': 'marcrelator:edt'})
                add_person_name(editor, forename, surname)
                title_stmt.append(editor)
    else:
        # Fallback placeholder
        editor = create_tei_element('editor', attrib={'ana': 'marcrelator:edt'})
        add_person_name(editor, 'FIRST', 'LAST')
        title_stmt.append(editor)

    # respStmt for XML encoding (always Christian Steiner)
    resp_stmt = create_tei_element('respStmt', attrib={'ana': 'marcrelator:mrk'})
    resp_stmt.append(create_tei_element('resp', 'XML encoding'))
    add_person_name(resp_stmt, 'Christian', 'Steiner')
    title_stmt.append(resp_stmt)

    # funder (from template)
    funder = create_tei_element('funder', attrib={'ana': 'marcrelator:fnd'})
    funder_name = template_data.get('funder_name', 'Austrian Science Fund (FWF)')
    funder_ref = template_data.get('funder_ref', 'https://www.fwf.ac.at/de/')
    funder_num = template_data.get('funder_num', 'P 38285-G')

    org_name = create_tei_element('orgName', funder_name, attrib={'ref': funder_ref})
    funder.append(org_name)
    funder.append(create_tei_element('num', funder_num))
    title_stmt.append(funder)

    # publicationStmt (from template)
    pub_stmt = create_tei_element('publicationStmt')
    file_desc.append(pub_stmt)

    publisher = create_tei_element('publisher')
    pub_name = template_data.get('publisher_name', 'Institut für Geschichte, Universität Graz')
    pub_corresp = template_data.get('publisher_corresp', 'http://geschichte.uni-graz.at/')
    publisher.append(create_tei_element('orgName', pub_name, attrib={'corresp': pub_corresp}))
    pub_stmt.append(publisher)

    # First authority: Digital Humanities Craft OG
    authority1 = create_tei_element('authority', attrib={'ana': 'marcrelator:his'})
    auth_name1 = template_data.get('authority_name', 'Digital Humanities Craft OG')
    auth_corresp1 = template_data.get('authority_corresp', 'https://dhcraft.org')
    authority1.append(create_tei_element('orgName', auth_name1, attrib={'corresp': auth_corresp1}))
    pub_stmt.append(authority1)

    # Second authority: Institut für Digitale Geisteswissenschaften
    authority2 = create_tei_element('authority', attrib={'ana': 'marcrelator:his'})
    authority2.append(create_tei_element('orgName', 'Institut für Digitale Geisteswissenschaften, Universität Graz',
                                         attrib={'ref': 'https://digital-humanities.uni-graz.at'}))
    pub_stmt.append(authority2)

    distributor = create_tei_element('distributor', attrib={'ana': 'marcrelator:rps'})
    dist_name = template_data.get('distributor_name', 'GAMS - Geisteswissenschaftliches Asset Management System')
    dist_ref = template_data.get('distributor_ref', 'https://gams.uni-graz.at')
    distributor.append(create_tei_element('orgName', dist_name, attrib={'ref': dist_ref}))
    pub_stmt.append(distributor)

    availability = create_tei_element('availability')
    lic_text = template_data.get('license_text', 'Creative Commons BY-NC 4.0')
    lic_target = template_data.get('license_target', 'https://creativecommons.org/licenses/by-nc/4.0')
    availability.append(create_tei_element('licence', lic_text, attrib={'target': lic_target}))
    pub_stmt.append(availability)

    # Use current year for publication date
    year = '2025'
    pub_stmt.append(create_tei_element('date', year, attrib={'when': year, 'ana': 'dcterms:issued'}))

    pub_place_text = template_data.get('pub_place', 'Graz')
    pub_stmt.append(create_tei_element('pubPlace', pub_place_text, attrib={'ana': 'marcrelator:pup'}))

    pid = dataset.get('PID', f'o:histdem.{dataset_id}')
    pub_stmt.append(create_tei_element('idno', pid, attrib={'type': 'PID'}))

    # seriesStmt (from template)
    series_stmt = create_tei_element('seriesStmt')
    file_desc.append(series_stmt)

    # Add series titles from template
    for title_data in template_data.get('series_titles', []):
        add_title(series_stmt, title_data['text'],
                 ref=title_data['ref'], lang=title_data['lang'])

    # Project director respStmt (from template)
    if 'project_director' in template_data:
        pdr = template_data['project_director']
        pdr_stmt = create_tei_element('respStmt', attrib={'ana': 'marcrelator:pdr'})
        pdr_stmt.append(create_tei_element('resp', pdr['resp']))
        add_person_name(pdr_stmt, pdr['forename'], pdr['surname'])
        series_stmt.append(pdr_stmt)

    # Research team respStmt (from template)
    if 'research_team' in template_data:
        team = template_data['research_team']
        rth_stmt = create_tei_element('respStmt', attrib={'ana': 'marcrelator:rth'})
        rth_stmt.append(create_tei_element('resp', team['resp']))
        rth_stmt.append(create_tei_element('orgName', team['name'], attrib={'ref': team['ref']}))
        series_stmt.append(rth_stmt)

    # sourceDesc
    source_desc = create_tei_element('sourceDesc')
    file_desc.append(source_desc)

    # Main source bibl with date and location
    source_bibl = create_tei_element('bibl')
    source_desc.append(source_bibl)

    # Add date information
    year_val = dataset.get('Jahr')
    date_from = dataset.get('Datum Von')
    date_to = dataset.get('Datum Bis')

    if date_from and date_to:
        date_elem = create_tei_element('date', f"{date_from}-{date_to}",
                     attrib={'from': date_from, 'to': date_to, 'ana': 'dcterms:created'})
    elif year_val:
        date_elem = create_tei_element('date', year_val,
                     attrib={'when': year_val, 'ana': 'dcterms:created'})
    else:
        date_elem = create_tei_element('date', 'YEAR',
                     attrib={'when': 'YEAR', 'ana': 'dcterms:created'})
    source_bibl.append(date_elem)

    # Country with Wikidata QID (read from CSV or fallback to lookup)
    country = dataset.get('Land', 'COUNTRY')
    country_qid = dataset.get('Land Wikidata', '').strip()
    if not country_qid:
        # Fallback to old mapping function if CSV field is empty
        country_qid = get_wikidata_qid(country) or 'None'
    country_elem = create_tei_element('country', country,
                   attrib={'ana': 'marcrelator:prp', 'ref': f'wd:{country_qid}'})
    source_bibl.append(country_elem)

    # Region if available
    region = dataset.get('Region')
    if region:
        region_qid = dataset.get('Region Wikidata', '').strip()
        if not region_qid:
            # Fallback to old mapping function if CSV field is empty
            region_qid = get_wikidata_qid(region)

        if region_qid:
            region_elem = create_tei_element('region', region,
                           attrib={'ana': 'marcrelator:prp', 'ref': f'wd:{region_qid}'})
        else:
            # Fallback if QID not found
            region_elem = create_tei_element('region', region,
                           attrib={'ana': 'marcrelator:prp', 'ref': 'wd:QXXX'})
        source_bibl.append(region_elem)

    # Citation bibl
    if citation_text:
        citation_bibl = create_tei_element('bibl', attrib={'type': 'citation'})
        source_desc.append(citation_bibl)

        # Add parsed authors
        for author_name in author_names:
            citation_bibl.append(create_tei_element('author', author_name))

        add_title(citation_bibl, dataset_title, level='a')
        add_title(citation_bibl, 'Mosaic Historical Microdata File', level='s')

        # Try to extract publisher from citation
        if 'mosaic.ipums.org' in citation_text:
            citation_bibl.append(create_tei_element('publisher', 'mosaic.ipums.org'))
        elif 'censusmosaic.org' in citation_text:
            citation_bibl.append(create_tei_element('publisher', 'www.censusmosaic.org'))
        else:
            citation_bibl.append(create_tei_element('publisher', 'mosaic.ipums.org'))

        # Extract year from citation (look for 4 digits at end)
        year_match = re.search(r'(\d{4})\.?\s*$', citation_text)
        if year_match:
            citation_bibl.append(create_tei_element('date', year_match.group(1)))
        else:
            citation_bibl.append(create_tei_element('date', year_val or '2024'))

        # Citation recommendation with markdown to TEI conversion
        rs_citation = create_tei_element('rs', attrib={'type': 'citation_recommendation'})
        add_mixed_content(rs_citation, citation_text)
        citation_bibl.append(rs_citation)

    # Data files bibl
    data_bibl = create_tei_element('bibl', attrib={'type': 'data'})
    source_desc.append(data_bibl)

    # CSV codes
    csv_codes = dataset.get('CSV Codes')
    if csv_codes:
        filename, title = parse_file_entry(csv_codes, 'CSV Codes', dataset_id)
        if filename:
            rs_codes = create_tei_element('rs', attrib={'type': 'codes'})
            add_title(rs_codes, title or 'Data with Codes')
            # Add folder prefix to URL
            file_url = add_folder_prefix(filename, dataset_id)
            media_id = sanitize_xml_id(filename)
            media = create_tei_element('media', attrib={
                'url': file_url,
                'mimeType': 'text/csv',
                f'{{{XML_NS}}}id': media_id
            })
            rs_codes.append(media)
            data_bibl.append(rs_codes)

    # CSV labels
    csv_labels = dataset.get('CSV Labels')
    if csv_labels:
        filename, title = parse_file_entry(csv_labels, 'CSV Labels', dataset_id)
        if filename:
            rs_labels = create_tei_element('rs', attrib={'type': 'labels'})
            add_title(rs_labels, title or 'Data with Labels')
            # Add folder prefix to URL
            file_url = add_folder_prefix(filename, dataset_id)
            media_id = sanitize_xml_id(filename)
            media = create_tei_element('media', attrib={
                'url': file_url,
                'mimeType': 'text/csv',
                f'{{{XML_NS}}}id': media_id
            })
            rs_labels.append(media)
            data_bibl.append(rs_labels)

    # Additional files bibl
    additional_bibl = create_tei_element('bibl', attrib={'type': 'additional'})
    has_additional = False

    # Process Zusatzdateien (PDFs)
    for i in range(1, 11):
        zusatz_key = f'Zusatzdatei {i}'
        zusatz_val = dataset.get(zusatz_key)
        if zusatz_val:
            filename, title = parse_file_entry(zusatz_val, zusatz_key, dataset_id)
            if filename:
                has_additional = True
                rs_type = 'sample' if title and 'sample' in title.lower() else 'literature'
                rs_elem = create_tei_element('rs', attrib={'type': rs_type})
                add_title(rs_elem, title or filename)

                # Add folder prefix to URL
                file_url = add_folder_prefix(filename, dataset_id)
                mime_type = 'application/pdf' if filename.endswith('.pdf') else 'application/octet-stream'
                media_id = sanitize_xml_id(filename)
                media = create_tei_element('media', attrib={
                    'url': file_url,
                    'mimeType': mime_type,
                    f'{{{XML_NS}}}id': media_id
                })
                rs_elem.append(media)
                additional_bibl.append(rs_elem)

    # Process Bilder (images)
    for i in range(1, 6):
        bild_key = f'Bild {i}'
        bild_val = dataset.get(bild_key)
        if bild_val:
            filename, title = parse_file_entry(bild_val, bild_key, dataset_id)
            if filename:
                has_additional = True
                # Determine type based on title/filename
                if title and ('map' in title.lower() or 'karte' in title.lower()):
                    rs_type = 'map'
                else:
                    rs_type = 'scan'

                rs_elem = create_tei_element('rs', attrib={'type': rs_type})
                add_title(rs_elem, title or filename)

                # Add folder prefix to URL
                file_url = add_folder_prefix(filename, dataset_id)

                # Determine MIME type
                ext = filename.split('.')[-1].lower()
                mime_map = {
                    'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                    'png': 'image/png', 'pdf': 'application/pdf'
                }
                mime_type = mime_map.get(ext, 'image/jpeg')

                media_id = sanitize_xml_id(filename)

                if mime_type.startswith('image/'):
                    graphic = create_tei_element('graphic', attrib={
                        'url': file_url,
                        'mimeType': mime_type,
                        f'{{{XML_NS}}}id': media_id
                    })
                    rs_elem.append(graphic)
                else:
                    media = create_tei_element('media', attrib={
                        'url': file_url,
                        'mimeType': mime_type,
                        f'{{{XML_NS}}}id': media_id
                    })
                    rs_elem.append(media)

                additional_bibl.append(rs_elem)

    # Literature without PDF
    for i in range(1, 5):
        lit_key = f'Literatur {i}'
        lit_val = dataset.get(lit_key)
        if lit_val:
            has_additional = True
            rs_lit = create_tei_element('rs', attrib={'type': 'literature'})
            add_title(rs_lit, lit_val)
            additional_bibl.append(rs_lit)

    if has_additional:
        source_desc.append(additional_bibl)

    # --- encodingDesc ---
    encoding_desc = create_tei_element('encodingDesc')
    header.append(encoding_desc)

    # projectDesc (from template)
    project_desc = create_tei_element('projectDesc')
    encoding_desc.append(project_desc)

    # Add context reference
    if 'project_context_ref' in template_data:
        ref_data = template_data['project_context_ref']
        ab = create_tei_element('ab')
        ref = create_tei_element('ref', ref_data['text'],
                                 attrib={'target': ref_data['target'], 'type': ref_data['type']})
        ab.append(ref)
        project_desc.append(ab)

    # Add project description paragraphs from template
    for p_text in template_data.get('project_desc_paragraphs', []):
        project_desc.append(create_tei_element('p', p_text))

    # listPrefixDef
    list_prefix = create_tei_element('listPrefixDef')
    encoding_desc.append(list_prefix)

    # MARC relator
    prefix_marc = create_tei_element('prefixDef', attrib={
        'ident': 'marcrelator',
        'matchPattern': '([a-z]+)',
        'replacementPattern': 'http://id.loc.gov/vocabulary/relators/$1'
    })
    prefix_marc.append(create_tei_element('p', 'Taxonomie Rollen MARC'))
    list_prefix.append(prefix_marc)

    # DCterms
    prefix_dc = create_tei_element('prefixDef', attrib={
        'ident': 'dcterms',
        'matchPattern': '([a-z]+)',
        'replacementPattern': 'http://purl.org/dc/terms/$1'
    })
    prefix_dc.append(create_tei_element('p', 'DCterms'))
    list_prefix.append(prefix_dc)

    # Wikidata
    prefix_wd = create_tei_element('prefixDef', attrib={
        'ident': 'wd',
        'matchPattern': r'(Q\d+)',
        'replacementPattern': 'https://www.wikidata.org/entity/$1'
    })
    prefix_wd.append(create_tei_element('p', 'Wikidata'))
    list_prefix.append(prefix_wd)

    # --- profileDesc ---
    profile_desc = create_tei_element('profileDesc')
    header.append(profile_desc)

    # langUsage
    lang_usage = create_tei_element('langUsage')
    profile_desc.append(lang_usage)

    # Parse language codes
    lang_codes = dataset.get('Sprachcodes', 'en')
    for lang_code in lang_codes.split(','):
        lang_code = lang_code.strip()
        # Simple language name mapping
        lang_names = {
            'sr': 'Serbian', 'sq': 'Albanian', 'en': 'English',
            'de': 'German', 'hy': 'Armenian', 'tr': 'Turkish'
        }
        lang_name = lang_names.get(lang_code, lang_code.upper())
        language = create_tei_element('language', lang_name,
                                      attrib={'ident': lang_code})
        lang_usage.append(language)

    # textClass with keywords
    text_class = create_tei_element('textClass')
    profile_desc.append(text_class)

    keywords = create_tei_element('keywords')
    text_class.append(keywords)

    kw_list = create_tei_element('list')
    keywords.append(kw_list)

    # Parse keywords
    kw_text = dataset.get('Schlagwörter', '')
    for keyword in kw_text.split(','):
        keyword = keyword.strip()
        if keyword:
            item = create_tei_element('item')
            item.append(create_tei_element('term', keyword))
            kw_list.append(item)

    # ========== TEI TEXT ==========
    text = create_tei_element('text')
    root.append(text)

    body = create_tei_element('body')
    text.append(body)

    # Head
    head_text = dataset.get('Überschrift', f'{country} {year_val}')
    body.append(create_tei_element('head', head_text))

    # Description paragraphs
    description = dataset.get('Beschreibung', '')
    if description:
        # Try to split long descriptions into paragraphs at double newlines
        paragraphs = description.split('\n\n') if '\n\n' in description else [description]
        for para in paragraphs:
            if para.strip():
                body.append(create_tei_element('p', para.strip()))
    else:
        body.append(create_tei_element('p', 'Description pending.'))

    # Notes
    notes = dataset.get('Anmerkungen', '')
    body.append(create_tei_element('note', notes if notes else 'No additional notes.'))

    return root


def prettify_xml(elem):
    """Return a pretty-printed XML string."""
    rough_string = ET.tostring(elem, encoding='utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="   ", encoding='utf-8').decode('utf-8')


def main():
    global conversion_warnings
    conversion_warnings = []  # Reset warnings for this run

    if len(sys.argv) < 2:
        print("Usage: python convert_csv_to_tei_v2.py <csv_file> [output_dir]")
        sys.exit(1)

    csv_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'output'

    # Load template data from 147_tei.xml
    template_file = '147_tei.xml'
    template_data = extract_template_data(template_file)

    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)

    print(f"\nReading CSV file: {csv_file}")
    datasets = parse_csv_column(csv_file)

    print(f"Found {len(datasets)} datasets\n")

    for i, dataset in enumerate(datasets):
        dataset_id = dataset.get('Datensatz ID', f'{i+1}')
        dataset_title = dataset.get('Datensatz Titel', 'Untitled')

        print(f"Processing Dataset {dataset_id}: {dataset_title}")

        # Create TEI document
        tei_root = create_tei_document(dataset, template_data)

        # Add processing instruction
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += '<?xml-model href="histdem.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>\n'

        # Pretty print
        xml_content += prettify_xml(tei_root).split('?>\n', 1)[1]  # Remove duplicate XML declaration

        # Write to file
        output_file = Path(output_dir) / f"{dataset_id}_tei.xml"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        print(f"  [OK] Written to {output_file}")

    print(f"\n[OK] Conversion complete! Generated {len(datasets)} TEI files in '{output_dir}/' directory")

    # Print warnings if any
    if conversion_warnings:
        print(f"\n{'='*80}")
        print(f"WARNUNGEN UND FEHLER IN CSV-DATEN:")
        print(f"{'='*80}")
        for warning in conversion_warnings:
            print(f"  {warning}")
        print(f"{'='*80}")
        print(f"HINWEIS: TEI-Dateien wurden trotz Warnungen generiert, aber sind möglicherweise")
        print(f"unvollständig. Bitte beheben Sie die CSV-Daten und führen die Konvertierung erneut aus.")
        print(f"{'='*80}\n")

    print(f"\nAutomatisierte Features:")
    print(f"  - Standard-Metadaten aus 147_tei.xml Vorlage extrahiert")
    print(f"  - Autoren aus Zitiertext geparst")
    print(f"  - Markdown (*kursiv*) zu TEI (<hi rend='italic'>) konvertiert")
    print(f"  - Länder und Regionen automatisch auf Wikidata QIDs gemappt")
    print(f"  - XML-Encoder auf Christian Steiner gesetzt")
    print(f"  - Datei-URLs mit Ordnerpräfixen versehen")
    print(f"\nManuelle Nachbearbeitung erforderlich:")
    print(f"  1. Autoren-Parsing-Genauigkeit prüfen (komplexe Namen müssen ggf. angepasst werden)")
    print(f"  2. Wikidata QIDs für unbekannte Orte ergänzen (nach 'wd:QXXX' suchen)")
    print(f"  3. Gegen histdem.rng Schema validieren")


if __name__ == '__main__':
    main()
