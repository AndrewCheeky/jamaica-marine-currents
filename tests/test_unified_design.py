import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class UnifiedDesignTests(unittest.TestCase):
 def test_shared_theme_and_images(self):
  self.assertIn('marine-theme.css',(ROOT/'index.html').read_text())
  self.assertTrue((ROOT/'assets/jamaica-sea-sunset.jpg').exists())
 def test_feature_modal_and_missing_values(self):
  html=(ROOT/'ocean_features_interactive.html').read_text()
  for term in ('detail-modal','feature-buttons',"shape.on('click'",'value===undefined'):
   self.assertIn(term,html)
  self.assertNotIn("String(value??'Unavailable')",html)
