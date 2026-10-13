import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TrendWindowTests(unittest.TestCase):
    def setUp(self):
        self.source=(ROOT/'generate.py').read_text()
    def test_three_seven_thirty_and_default(self):
        self.assertIn('[3,7,30].forEach',self.source)
        self.assertIn('renderTrends(7)',self.source)
    def test_distinct_source_dates_and_cutoff(self):
        self.assertIn('new Map(rows.map(v=>[v[dateField],v]))',self.source)
        self.assertIn('windowDays-1',self.source)
        self.assertIn('v[dateField]>=cutoff',self.source)
    def test_no_premature_trend(self):
        self.assertIn('Latest difference only — not yet a trend',self.source)
        self.assertIn('Early indication — limited history',self.source)
    def test_history_archive_unchanged(self):
        self.assertIn('days=730', (ROOT/'bank_history.py').read_text())
        workflow=(ROOT/'github-workflows/currents.yml').read_text()
        self.assertIn('history_storage.py restore',workflow)
        self.assertIn('history_storage.py save',workflow)
if __name__=='__main__':unittest.main()
