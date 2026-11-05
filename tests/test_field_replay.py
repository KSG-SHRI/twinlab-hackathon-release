"""Checks for the descriptive extract tool, not evidence of data provenance."""
import csv
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import field_replay as replay


class FieldReplayTests(unittest.TestCase):
    def test_extract_preserves_source_values_and_only_selected_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'input.zip'
            destination = Path(directory) / 'output.csv'
            with ZipFile(archive, 'w') as zipped:
                for filename in replay.FILES:
                    zipped.writestr(filename, 'TIMESTAMP,T_Room_106_Avg,T_Room_204_Avg,T_out_Avg,ignored\n'
                                    '12/7/2017 0:00,32,50,68,other\n')
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            with patch.object(replay, 'ARCHIVE_SHA256', digest):
                replay.extract(archive, destination)
            rows = replay.read_rows(destination)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0], dict(zip(replay.FIELDS, (next(iter(replay.FILES)),
                '12/7/2017 0:00', '32', '50', '68'))))
            self.assertEqual(replay.average_c(rows, 'T_out_Avg'), (20, 4))

    def test_rejects_wrong_archive_and_unexpected_source(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            archive = directory / 'wrong.zip'
            archive.write_bytes(b'not the expected archive')
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                replay.extract(archive, directory / 'out.csv')
            extract = directory / 'input.csv'
            extract.write_text(','.join(replay.FIELDS) + '\nunknown,1,2,3,4\n')
            with self.assertRaisesRegex(ValueError, 'source file'):
                replay.read_rows(extract)

    def test_nonfinite_and_missing_readings_are_not_averaged(self):
        rows = [{'x': s} for s in ['32', '50', '', 'nan', 'inf', '-inf']]
        self.assertEqual(replay.average_c(rows, 'x'), (5, 2))
        self.assertEqual(replay.average_c([{'x': ''}], 'x'), (None, 0))

    def test_checked_in_extract_has_expected_shape(self):
        # Shape checks detect accidental changes but do not establish provenance.
        rows = replay.read_rows(replay.DEFAULT)
        self.assertEqual(len(rows), 384)
        for filename in replay.FILES:
            self.assertEqual(sum(row['source_file'] == filename for row in rows), 96)


if __name__ == '__main__':
    unittest.main()
