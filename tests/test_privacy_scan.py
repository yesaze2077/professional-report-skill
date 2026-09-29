"""Public artifact scanner catches text hidden in media and release archives."""
from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'qa'))
from privacy_scan import scan


class PrivacyScanTests(unittest.TestCase):
    def test_zip_member(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'release.zip'
            with zipfile.ZipFile(target,'w') as archive:
                archive.writestr('README.md','contact: private@'+'example.com')
            self.assertIn('email',' '.join(scan(Path(directory))))

    def test_png_text_chunk(self):
        with tempfile.TemporaryDirectory() as directory:
            payload=b'Comment\x00/Users/' + b'example/private'
            chunk=len(payload).to_bytes(4,'big')+b'tEXt'+payload+b'\x00'*4
            end=(0).to_bytes(4,'big')+b'IEND'+b'\x00'*4
            (Path(directory)/'preview.png').write_bytes(b'\x89PNG\r\n\x1a\n'+chunk+end)
            self.assertIn('absolute_path',' '.join(scan(Path(directory))))


if __name__=='__main__': unittest.main()
