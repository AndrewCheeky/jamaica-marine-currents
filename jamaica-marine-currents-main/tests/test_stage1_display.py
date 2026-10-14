import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class Stage1DisplayTests(unittest.TestCase):
    def test_plain_language_headings(self):
        source = (ROOT / 'generate.py').read_text()
        self.assertIn('Ocean Conditions · ', source)
        self.assertIn('How conditions are changing · ', source)
        self.assertIn('What this means for fishing', source)
        self.assertNotIn("qh.textContent='Data freshness & quality", source)
    def test_forecast_and_satellite_dates_distinguished(self):
        source = (ROOT / 'generate.py').read_text()
        self.assertIn("'Forecast valid'", source)
        self.assertIn("'Satellite observed'", source)
        self.assertIn('Data details', source)
        self.assertIn('About this history', source)
    def test_history_workflow_unchanged(self):
        source = (ROOT / 'github-workflows/currents.yml').read_text()
        self.assertIn('history_storage.py restore', source)
        self.assertIn('history_storage.py save', source)
