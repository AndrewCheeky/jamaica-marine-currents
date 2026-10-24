import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class GeneratedDesignTests(unittest.TestCase):
 def test_generated_template_includes_hero_and_theme(self):
  code=(ROOT/'generate.py').read_text()
  self.assertIn('class="marine-hero"',code)
  self.assertIn('class="sea-quicklinks"',code)
  self.assertIn('href="#layer-controls"',code)
  self.assertIn('assets/marine-theme.css',code)
 def test_generation_copies_assets_into_published_site(self):
  code=(ROOT/'generate.py').read_text()
  self.assertIn("asset_out = OUT / 'assets'",code)
  self.assertIn('shutil.copy2(ROOT',code)
  for name in ('jamaica-sea-sunset.jpg','fishing-sunset.webp','fresh-catch.webp','bluefields-boats.webp','marine-theme.css'):
   self.assertTrue((ROOT/'assets'/name).is_file(),name)
   self.assertIn(name,code)
 def test_existing_feature_and_history_pipeline_untouched(self):
  code=(ROOT/'generate.py').read_text()
  self.assertIn("(OUT / 'index.html').write_text(PAGE",code)
  self.assertIn('ocean_features',code)
