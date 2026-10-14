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

class OfflineBasemapTests(unittest.TestCase):
    def test_no_third_party_tiles(self):
        html=(ROOT/'ocean_features_interactive.html').read_text()
        self.assertNotIn('tile.openstreetmap.org',html)
        self.assertNotIn('L.tileLayer(',html)
        self.assertIn("L.polygon(points",html)
        self.assertNotIn("L.imageOverlay(",html)
        self.assertIn("map.fitBounds([[17.05,-79.1],[19.1,-75.7]]",html)
    def test_local_geography_is_packaged_by_generator(self):
        self.assertTrue((ROOT/'jamaica-geography.svg').is_file())
        self.assertIn("out/'jamaica-geography.svg'",(ROOT/'ocean_features.py').read_text())
    def test_verbose_gps_list_removed(self):
        code=(ROOT/'generate.py').read_text()
        self.assertNotIn("filtered.forEach(f=>{const p=document.createElement('p')",code)
