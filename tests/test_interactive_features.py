import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class InteractiveFeatureTests(unittest.TestCase):
    def test_interactive_page_has_leaflet_and_popup(self):
        html=(ROOT/'ocean_features_interactive.html').read_text()
        for token in ('L.map(', 'L.circleMarker(', 'L.polyline(', 'bindPopup(', 'Copy GPS', 'ocean-features.geojson', 'jfi-feature-controls'):
            self.assertIn(token,html)
    def test_generator_embeds_map_and_switches_from_image(self):
        code=(ROOT/'generate.py').read_text()
        self.assertIn('id="interactive-features"',code)
        self.assertIn('interactiveFeatures.src=',code)
        self.assertIn('syncFeatureMap()',code)
    def test_feature_generator_exports_lines_and_html(self):
        code=(ROOT/'ocean_features.py').read_text()
        self.assertIn("'type':'LineString'",code)
        self.assertIn("out/'ocean-features-interactive.html'",code)
