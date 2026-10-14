import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class FeatureFiltersTests(unittest.TestCase):
    def test_buttons_and_switching(self):
        s=(ROOT/'generate.py').read_text()
        for key in ('all','sst_front','currents','eddy_candidate'):
            self.assertIn('data-feature="'+key+'"',s)
        self.assertIn("featureFilter=btn.dataset.feature;show()",s)
        self.assertIn('view.images?.[featureFilter]||view.image',s)
    def test_independent_map_generation(self):
        s=(ROOT/'ocean_features.py').read_text()
        self.assertIn("('currents',('convergence','shear'))",s)
        self.assertIn("'images':images",s)
