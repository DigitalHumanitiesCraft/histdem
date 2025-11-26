#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bildkomprimierungsskript für das histdem-Projekt
Reduziert Bildgrößen auf maximal 1MB durch Qualitätsanpassung und Größenoptimierung.
"""

import sys
from pathlib import Path
from PIL import Image
import os
import time

# Set UTF-8 encoding for output on Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Maximum file size in bytes (1MB)
MAX_FILE_SIZE = 1 * 1024 * 1024

# Folder name mapping for each dataset
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

# Supported image extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.JPG', '.JPEG', '.png', '.PNG', '.tif', '.tiff', '.TIF', '.TIFF'}


def get_file_size_mb(file_path):
    """Get file size in MB."""
    size_bytes = file_path.stat().st_size
    return size_bytes / (1024 * 1024)


def compress_image(image_path, max_size_bytes=MAX_FILE_SIZE, quality_start=95, quality_min=60):
    """
    Compress image to target file size by adjusting quality.

    Args:
        image_path: Path to the image file
        max_size_bytes: Maximum file size in bytes
        quality_start: Starting quality (1-100)
        quality_min: Minimum acceptable quality

    Returns:
        Tuple of (success, original_size_mb, new_size_mb, quality_used)
    """
    original_size = image_path.stat().st_size
    original_size_mb = original_size / (1024 * 1024)

    # If already under limit, skip
    if original_size <= max_size_bytes:
        return True, original_size_mb, original_size_mb, None

    # Open image
    try:
        img = Image.open(image_path)

        # Convert RGBA to RGB if saving as JPEG
        if img.mode == 'RGBA' and image_path.suffix.lower() in {'.jpg', '.jpeg'}:
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = background
        elif img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')

        # Determine output format
        output_format = 'JPEG' if image_path.suffix.lower() in {'.jpg', '.jpeg'} else 'PNG'

        # Create backup
        backup_path = image_path.with_suffix(image_path.suffix + '.backup')
        if not backup_path.exists():
            # Close the image before renaming
            img_copy = img.copy()
            img.close()
            img = img_copy

            # Wait a moment to ensure file handle is released
            time.sleep(0.1)

            try:
                image_path.rename(backup_path)
            except PermissionError:
                # File is locked, try copying instead
                import shutil
                shutil.copy2(image_path, backup_path)
        else:
            # Backup already exists, just read from original
            pass

        # Try different quality levels
        quality = quality_start
        temp_path = image_path.with_suffix('.tmp' + image_path.suffix)

        while quality >= quality_min:
            # Save with current quality
            if output_format == 'JPEG':
                img.save(temp_path, format=output_format, quality=quality, optimize=True)
            else:
                img.save(temp_path, format=output_format, optimize=True)

            # Check size
            new_size = temp_path.stat().st_size

            if new_size <= max_size_bytes:
                # Success! Replace original
                temp_path.replace(image_path)
                new_size_mb = new_size / (1024 * 1024)
                return True, original_size_mb, new_size_mb, quality

            # Reduce quality and try again
            quality -= 5

        # If we couldn't compress enough with quality alone, try resizing
        # Resize to 90% and try again
        if temp_path.exists():
            temp_path.unlink()

        # Calculate new dimensions (reduce by 10%)
        new_width = int(img.width * 0.9)
        new_height = int(img.height * 0.9)
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Try with resized image
        quality = quality_start
        while quality >= quality_min:
            if output_format == 'JPEG':
                img_resized.save(temp_path, format=output_format, quality=quality, optimize=True)
            else:
                img_resized.save(temp_path, format=output_format, optimize=True)

            new_size = temp_path.stat().st_size

            if new_size <= max_size_bytes:
                temp_path.replace(image_path)
                new_size_mb = new_size / (1024 * 1024)
                return True, original_size_mb, new_size_mb, quality

            quality -= 5

        # Still couldn't compress enough
        if temp_path.exists():
            temp_path.unlink()

        # Restore from backup
        if backup_path.exists():
            backup_path.rename(image_path)

        return False, original_size_mb, original_size_mb, None

    except Exception as e:
        print(f"  [FEHLER] Fehler beim Komprimieren: {e}")
        # Restore from backup if exists
        backup_path = image_path.with_suffix(image_path.suffix + '.backup')
        if backup_path.exists() and not image_path.exists():
            backup_path.rename(image_path)
        return False, original_size_mb, original_size_mb, None


def process_folder(folder_path, dry_run=False):
    """
    Process all images in a folder.

    Args:
        folder_path: Path to the dataset folder
        dry_run: If True, only report what would be done

    Returns:
        Tuple of (total_images, compressed_images, failed_images, space_saved_mb)
    """
    total_images = 0
    compressed_images = 0
    failed_images = 0
    space_saved_mb = 0.0

    # Find all image files
    image_files = []
    for ext in IMAGE_EXTENSIONS:
        image_files.extend(folder_path.glob(f'*{ext}'))

    if not image_files:
        return 0, 0, 0, 0.0

    print(f"\n  Gefundene Bilder: {len(image_files)}")

    for image_path in sorted(image_files):
        total_images += 1
        original_size_mb = get_file_size_mb(image_path)

        if original_size_mb <= 1.0:
            print(f"  [OK] {image_path.name}: {original_size_mb:.2f} MB (bereits unter Limit)")
            continue

        if dry_run:
            print(f"  [WÜRDE KOMPRIMIEREN] {image_path.name}: {original_size_mb:.2f} MB")
            compressed_images += 1
        else:
            print(f"  [KOMPRIMIERE] {image_path.name}: {original_size_mb:.2f} MB...", end='')
            success, orig_mb, new_mb, quality = compress_image(image_path)

            if success and new_mb < orig_mb:
                saved = orig_mb - new_mb
                space_saved_mb += saved
                compressed_images += 1
                quality_str = f" (Qualität: {quality})" if quality else ""
                print(f" → {new_mb:.2f} MB{quality_str} [Gespart: {saved:.2f} MB]")
            elif success:
                print(f" → Bereits optimiert")
            else:
                print(f" → FEHLGESCHLAGEN")
                failed_images += 1

    return total_images, compressed_images, failed_images, space_saved_mb


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Verwendung:")
        print(f"  {sys.argv[0]} all              # Komprimiert alle Bilder in allen Datensatz-Ordnern")
        print(f"  {sys.argv[0]} <dataset_id>     # Komprimiert Bilder für einen bestimmten Datensatz (z.B. 147)")
        print(f"  {sys.argv[0]} all --dry-run    # Zeigt nur an, was komprimiert würde")
        print()
        print("Verfügbare Datensätze:")
        for dataset_id, folder in sorted(DATASET_FOLDERS.items()):
            print(f"  {dataset_id}: {folder}")
        sys.exit(1)

    mode = sys.argv[1]
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("\n=== TESTLAUF (keine Änderungen) ===\n")
    else:
        print("\n=== BILDKOMPRIMIERUNG ===\n")
        print("Maximale Dateigröße: 1 MB")
        print("Backup-Dateien werden erstellt (.backup)\n")

    base_path = Path('.')

    # Determine which folders to process
    folders_to_process = []

    if mode == 'all':
        folders_to_process = [(dataset_id, base_path / folder)
                             for dataset_id, folder in DATASET_FOLDERS.items()]
    elif mode in DATASET_FOLDERS:
        folder = base_path / DATASET_FOLDERS[mode]
        folders_to_process = [(mode, folder)]
    else:
        print(f"Fehler: Ungültiger Modus '{mode}'")
        print("Verwenden Sie 'all' oder eine Datensatz-ID (z.B. '147')")
        sys.exit(1)

    # Process folders
    total_folders = 0
    total_images = 0
    total_compressed = 0
    total_failed = 0
    total_space_saved = 0.0

    for dataset_id, folder_path in folders_to_process:
        if not folder_path.exists():
            print(f"[WARNUNG] Ordner nicht gefunden: {folder_path}")
            continue

        total_folders += 1
        print(f"\n{'='*60}")
        print(f"Datensatz {dataset_id}: {folder_path.name}")
        print('='*60)

        images, compressed, failed, saved = process_folder(folder_path, dry_run)

        total_images += images
        total_compressed += compressed
        total_failed += failed
        total_space_saved += saved

    # Summary
    print(f"\n{'='*60}")
    print("ZUSAMMENFASSUNG")
    print('='*60)
    print(f"Verarbeitete Ordner: {total_folders}")
    print(f"Gefundene Bilder: {total_images}")
    print(f"Komprimierte Bilder: {total_compressed}")
    if total_failed > 0:
        print(f"Fehlgeschlagen: {total_failed}")
    if not dry_run:
        print(f"Eingesparter Speicherplatz: {total_space_saved:.2f} MB")
    print()

    if dry_run:
        print("Dies war ein Testlauf. Führen Sie den Befehl ohne --dry-run aus, um die Komprimierung durchzuführen.")
    else:
        print("Fertig! Backup-Dateien (.backup) können nach Überprüfung gelöscht werden.")
    print()


if __name__ == '__main__':
    main()
