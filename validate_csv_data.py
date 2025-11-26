#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV-Datenvalidierungsskript für das histdem-Projekt
Generiert einen menschenlesbaren Bericht über Dateninkonsistenzen und fehlende Informationen.
"""

import csv
import sys
import re
from pathlib import Path

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Folder name mapping for each dataset (same as in convert_csv_to_tei.py)
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


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.END}\n")


def print_section(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BLUE}{'-' * len(text)}{Colors.END}")


def print_ok(text):
    print(f"{Colors.GREEN}[OK] {text}{Colors.END}")


def print_warning(text):
    print(f"{Colors.YELLOW}[WARNING] {text}{Colors.END}")


def print_error(text):
    print(f"{Colors.RED}[ERROR] {text}{Colors.END}")


def validate_file_entry(entry, field_name):
    """
    Validiert das Dateieintragsformat.
    Erwartetes Format: "dateiname.ext - Titel" oder nur "dateiname.ext"
    Gibt zurück: (is_valid, issues_list)
    """
    issues = []

    if not entry or entry.strip() == '':
        return True, []  # Leer ist OK für optionale Felder

    entry = entry.strip()

    # Prüfe auf " - " Trenner
    if ' - ' in entry:
        parts = entry.split(' - ', 1)
        filename = parts[0].strip()
        title = parts[1].strip()

        if not filename:
            issues.append(f"Leerer Dateiname vor ' - '")
        if not title:
            issues.append(f"Leerer Titel nach ' - '")
    else:
        # Kein Trenner - nur Dateiname (potenziell inkonsistent mit anderen Datensätzen)
        filename = entry
        issues.append(f"Fehlender Titel (Format sollte sein: 'dateiname - Titel')")

    # Validiere, dass Dateiname eine Erweiterung hat
    if '.' not in filename:
        issues.append(f"Dateiname ohne Erweiterung: '{filename}'")

    # Prüfe auf häufige Probleme
    if filename.endswith(' '):
        issues.append(f"Dateiname hat nachfolgendes Leerzeichen")
    if filename.startswith(' '):
        issues.append(f"Dateiname hat führendes Leerzeichen")

    return len(issues) == 0, issues


def validate_csv_labels_match_codes(codes_entry, labels_entry):
    """Prüft ob Labels-Dateiname zum Codes-Dateinamenmuster passt"""
    issues = []

    if not codes_entry or not labels_entry:
        return True, []

    # Extrahiere Dateinamen
    codes_file = codes_entry.split(' - ')[0].strip() if ' - ' in codes_entry else codes_entry.strip()
    labels_file = labels_entry.split(' - ')[0].strip() if ' - ' in labels_entry else labels_entry.strip()

    # Prüfe ob Codes-Datei mit _codes.csv endet
    if not codes_file.endswith('_codes.csv'):
        issues.append(f"Codes-Dateiname endet nicht mit '_codes.csv': '{codes_file}'")

    # Prüfe ob Labels-Datei mit _labels.csv endet
    if not labels_file.endswith('_labels.csv'):
        issues.append(f"Labels-Dateiname endet nicht mit '_labels.csv': '{labels_file}'")

    # Prüfe ob Basisnamen übereinstimmen
    codes_base = codes_file.replace('_codes.csv', '')
    labels_base = labels_file.replace('_labels.csv', '').replace('_codes.csv', '')  # Behandle Fehlerfall

    if codes_base != labels_base:
        issues.append(f"Basis-Dateinamen stimmen nicht überein: codes='{codes_base}' vs labels='{labels_base}'")

    return len(issues) == 0, issues


def validate_date_range(year, date_from, date_to):
    """Validiert Datumskonsistenz"""
    issues = []

    # Wenn Datumsbereich existiert, sollten beide Werte vorhanden sein
    if date_from and not date_to:
        issues.append(f"Datumsbereich unvollständig: hat 'Datum Von' ({date_from}) aber 'Datum Bis' fehlt")
    if date_to and not date_from:
        issues.append(f"Datumsbereich unvollständig: hat 'Datum Bis' ({date_to}) aber 'Datum Von' fehlt")

    # Wenn beide date_from und date_to existieren, sollte year leer sein oder im Bereich liegen
    if date_from and date_to and year:
        try:
            year_int = int(year)
            from_int = int(date_from)
            to_int = int(date_to)

            if not (from_int <= year_int <= to_int):
                issues.append(f"Jahr {year} liegt nicht im Datumsbereich {date_from}-{date_to}")
        except ValueError:
            pass  # Wird von anderer Validierung erfasst

    return len(issues) == 0, issues


def validate_required_fields(dataset):
    """Prüft ob erforderliche Felder vorhanden sind"""
    issues = []

    required_fields = [
        'Datensatz ID',
        'Datensatz Titel',
        'Land',
        'PID',
        'Anzahl Personen',
        'Anzahl Haushalte',
        'Zitierempfehlung',
        'Schlagwörter',
        'Sprachcodes',
        'Überschrift',
        'Beschreibung'
    ]

    for field in required_fields:
        value = dataset.get(field, '').strip()
        if not value:
            issues.append(f"Pflichtfeld '{field}' ist leer")

    return len(issues) == 0, issues


def check_file_exists(filename, dataset_id, base_path="."):
    """Check if a file exists in the dataset's folder.

    Returns: (exists, full_path_or_error_message)
    """
    if not filename:
        return True, ""  # Empty filename is OK (already validated elsewhere)

    folder = DATASET_FOLDERS.get(str(dataset_id))
    if not folder:
        return False, f"Kein Ordner-Mapping für Dataset {dataset_id} gefunden"

    folder_path = Path(base_path) / folder
    if not folder_path.exists():
        return False, f"Ordner '{folder}' existiert nicht"

    file_path = folder_path / filename
    if not file_path.exists():
        return False, f"Datei nicht gefunden: {folder}/{filename}"

    return True, str(file_path)


def validate_files_exist(dataset, dataset_id, base_path="."):
    """Check if all files mentioned in the dataset actually exist."""
    issues = []

    # Check CSV Codes
    csv_codes = dataset.get('CSV Codes', '')
    if csv_codes:
        filename = csv_codes.split(' - ')[0].strip() if ' - ' in csv_codes else csv_codes.strip()
        if filename:
            exists, msg = check_file_exists(filename, dataset_id, base_path)
            if not exists:
                issues.append(f"CSV Codes: {msg}")

    # Check CSV Labels
    csv_labels = dataset.get('CSV Labels', '')
    if csv_labels:
        filename = csv_labels.split(' - ')[0].strip() if ' - ' in csv_labels else csv_labels.strip()
        if filename:
            exists, msg = check_file_exists(filename, dataset_id, base_path)
            if not exists:
                issues.append(f"CSV Labels: {msg}")

    # Check Zusatzdateien
    for i in range(1, 11):
        zusatz_val = dataset.get(f'Zusatzdatei {i}', '')
        if zusatz_val:
            filename = zusatz_val.split(' - ')[0].strip() if ' - ' in zusatz_val else zusatz_val.strip()
            if filename:
                exists, msg = check_file_exists(filename, dataset_id, base_path)
                if not exists:
                    issues.append(f"Zusatzdatei {i}: {msg}")

    # Check Bilder
    for i in range(1, 6):
        bild_val = dataset.get(f'Bild {i}', '')
        if bild_val:
            filename = bild_val.split(' - ')[0].strip() if ' - ' in bild_val else bild_val.strip()
            if filename:
                exists, msg = check_file_exists(filename, dataset_id, base_path)
                if not exists:
                    issues.append(f"Bild {i}: {msg}")

    return len(issues) == 0, issues


def main():
    if len(sys.argv) < 2:
        print(f"Verwendung: {sys.argv[0]} <csv_datei>")
        sys.exit(1)

    csv_file = sys.argv[1]

    if not Path(csv_file).exists():
        print(f"Fehler: Datei '{csv_file}' nicht gefunden")
        sys.exit(1)

    # Read CSV
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Get dataset columns (skip first two columns: FELDNAME and TITEL/BESCHREIBUNG)
    all_columns = list(rows[0].keys())
    dataset_columns = [col for col in all_columns if col.startswith('Datensatz ')]

    print_header("CSV-DATENVALIDIERUNGSBERICHT")
    print(f"Datei: {csv_file}")
    print(f"Anzahl Datensätze: {len(dataset_columns)}")

    # Convert rows to column-based structure
    datasets = {}
    for col in dataset_columns:
        dataset_data = {}
        for row in rows:
            field_name = row.get('FELDNAME', '')
            if field_name:
                dataset_data[field_name] = row.get(col, '').strip()
        datasets[col] = dataset_data

    total_issues = 0
    datasets_with_issues = 0

    # Validate each dataset
    for dataset_col in dataset_columns:
        dataset = datasets[dataset_col]
        dataset_id = dataset.get('Datensatz ID', 'Unknown')
        dataset_title = dataset.get('Datensatz Titel', 'Unknown')

        print_section(f"Dataset {dataset_id}: {dataset_title[:60]}")

        dataset_issues = []

        # 1. Check required fields
        valid, issues = validate_required_fields(dataset)
        if not valid:
            dataset_issues.extend(issues)

        # 2. Validate CSV Codes
        csv_codes = dataset.get('CSV Codes', '')
        valid, issues = validate_file_entry(csv_codes, 'CSV Codes')
        if not valid:
            for issue in issues:
                dataset_issues.append(f"CSV Codes: {issue}")

        # 3. Validate CSV Labels
        csv_labels = dataset.get('CSV Labels', '')
        valid, issues = validate_file_entry(csv_labels, 'CSV Labels')
        if not valid:
            for issue in issues:
                dataset_issues.append(f"CSV Labels: {issue}")

        # 4. Check CSV Codes/Labels consistency
        if csv_codes and csv_labels:
            valid, issues = validate_csv_labels_match_codes(csv_codes, csv_labels)
            if not valid:
                dataset_issues.extend(issues)

        # 5. Validate date fields
        year = dataset.get('Jahr', '')
        date_from = dataset.get('Datum Von', '')
        date_to = dataset.get('Datum Bis', '')
        valid, issues = validate_date_range(year, date_from, date_to)
        if not valid:
            dataset_issues.extend(issues)

        # 6. Validate Zusatzdateien
        for i in range(1, 11):
            zusatz = dataset.get(f'Zusatzdatei {i}', '')
            if zusatz:
                valid, issues = validate_file_entry(zusatz, f'Zusatzdatei {i}')
                if not valid:
                    for issue in issues:
                        dataset_issues.append(f"Zusatzdatei {i}: {issue}")

        # 7. Validate Bilder
        for i in range(1, 6):
            bild = dataset.get(f'Bild {i}', '')
            if bild:
                valid, issues = validate_file_entry(bild, f'Bild {i}')
                if not valid:
                    for issue in issues:
                        dataset_issues.append(f"Bild {i}: {issue}")

        # 8. Check PID format
        pid = dataset.get('PID', '')
        if pid and not re.match(r'^o:histdem\.\d+$', pid):
            dataset_issues.append(f"PID-Format inkorrekt: '{pid}' (erwartet: o:histdem.NNN)")

        # 9. Check if PID matches Datensatz ID
        if pid and dataset_id:
            expected_pid = f"o:histdem.{dataset_id}"
            if pid != expected_pid:
                dataset_issues.append(f"PID '{pid}' stimmt nicht mit Datensatz ID '{dataset_id}' überein (erwartet: {expected_pid})")

        # 10. Validate language codes (should be ISO 639-1)
        lang_codes = dataset.get('Sprachcodes', '')
        if lang_codes:
            codes = [c.strip() for c in lang_codes.split(',')]
            for code in codes:
                if len(code) != 2 or not code.islower():
                    dataset_issues.append(f"Sprachcode '{code}' scheint nicht im ISO 639-1 Format zu sein")

        # 11. Check if files exist
        valid, issues = validate_files_exist(dataset, dataset_id)
        if not valid:
            dataset_issues.extend(issues)

        # Print results
        if dataset_issues:
            datasets_with_issues += 1
            total_issues += len(dataset_issues)
            print_error(f"{len(dataset_issues)} Problem(e) gefunden:")
            for issue in dataset_issues:
                print(f"  - {issue}")
        else:
            print_ok("Keine Probleme gefunden - Daten sind vollständig und konsistent")

    # Summary
    print_header("ZUSAMMENFASSUNG")
    print(f"Geprüfte Datensätze: {len(dataset_columns)}")
    print(f"Datensätze mit Problemen: {datasets_with_issues}")
    print(f"Gefundene Probleme insgesamt: {total_issues}")

    if total_issues == 0:
        print_ok("\n[OK] Alle Daten sind konsistent und vollständig!")
    else:
        print_error(f"\n[FEHLER] Bitte beheben Sie die {total_issues} Problem(e) vor der Konvertierung")

    print()

    return 0 if total_issues == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
