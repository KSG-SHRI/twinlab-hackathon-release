"""Inspect a small, attributed research-facility temperature extract offline.

Descriptive measurements only. Not an evaluation of TwinLab's interventions.
"""
import argparse
import csv
import hashlib
import io
import math
from pathlib import Path
from statistics import mean
from zipfile import ZipFile

ARCHIVE_SHA256 = '1e6cd3df991abf865f7567e6cc0ac246968299eb02dfe9464d887727f930dde0'
FILES = {
    '171207_ExcessiveInfiltrationThroughTheBuildingEnvelope_FI1.csv': '20% increased effective leakage area',
    '171209_ExcessiveInfiltrationThroughTheBuildingEnvelope_B1.csv': 'baseline',
    '171210_ExcessiveInfiltrationThroughTheBuildingEnvelope_B2.csv': 'baseline',
    '171214_ExcessiveInfiltrationThroughTheBuildingEnvelope_FI2.csv': '40% increased effective leakage area',
}
FIELDS = ('source_file', 'TIMESTAMP', 'T_Room_106_Avg', 'T_Room_204_Avg', 'T_out_Avg')
DEFAULT = Path(__file__).parent / 'data' / 'ornl_infiltration_subset.csv'


def extract(archive, destination):
    """Keep source filename, timestamp, and three unmodified Fahrenheit readings."""
    archive = Path(archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError('Source archive does not match the documented SHA-256')
    with ZipFile(archive) as z, Path(destination).open('w', newline='', encoding='utf-8') as f:
        out = csv.DictWriter(f, fieldnames=FIELDS, lineterminator='\n')
        out.writeheader()
        for filename in FILES:
            with z.open(filename) as raw:
                for row in csv.DictReader(io.TextIOWrapper(raw, encoding='utf-8-sig', newline='')):
                    out.writerow({'source_file': filename, **{key: row[key] for key in FIELDS[1:]}})


def read_rows(path):
    with Path(path).open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError('Unexpected extract columns')
        rows = list(reader)
    if any(row['source_file'] not in FILES for row in rows):
        raise ValueError('Unexpected source file')
    return rows


def average_c(rows, name):
    values = []
    for row in rows:
        try:
            v = float(row[name])
            if math.isfinite(v):
                values.append((v - 32) * 5 / 9)
        except ValueError:
            pass
    return (mean(values), len(values)) if values else (None, 0)


def report(rows):
    for filename, condition in FILES.items():
        day = [row for row in rows if row['source_file'] == filename]
        print(f'{filename[:6]} | {condition} | {len(day)} recorded rows')
        for key, label in [('T_Room_106_Avg', 'Room 106'), ('T_Room_204_Avg', 'Room 204'), ('T_out_Avg', 'Outside')]:
            value, n = average_c(day, key)
            print(f'  {label}: ' + (f'{value:.2f} °C mean ({n} valid readings)' if value is not None else 'no valid readings'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract', metavar='ARCHIVE', help='Recreate the extract from the documented source archive')
    parser.add_argument('--output', default=str(DEFAULT), help='Extract destination or path to an existing extract')
    args = parser.parse_args()
    if args.extract:
        extract(args.extract, args.output)
    report(read_rows(args.output))


if __name__ == '__main__':
    main()
