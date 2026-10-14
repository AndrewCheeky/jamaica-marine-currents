import pathlib
import unittest

class CollapsibleTrendTests(unittest.TestCase):
    def test_native_details_and_summary(self):
        s=(pathlib.Path(__file__).resolve().parents[1]/'generate.py').read_text()
        self.assertIn("trendsDetails=document.createElement('details')",s)
        self.assertIn("trendsSummary=document.createElement('summary')",s)
        self.assertIn("trendsDetails.append(trendControls,cards,meaning,historyDetails)",s)
        self.assertIn("trendsDetails.open=wasOpen",s)
