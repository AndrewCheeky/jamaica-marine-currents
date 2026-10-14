import json
import tempfile
import unittest
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ocean_features

class OceanFeatureTests(unittest.TestCase):
    def setUp(self):
        self.lat=np.linspace(17,19,40);self.lon=np.linspace(-78,-76,40)
        y,x=np.meshgrid(self.lat,self.lon,indexing='ij')
        self.sst=28+1.4*np.tanh((x+77)/.16)
        self.u=-.15*(x+77);self.v=-.15*(y-18)
    def test_native_grid_diagnostics(self):
        fields=ocean_features.diagnostics(self.lat,self.lon,self.sst,self.u,self.v)
        self.assertEqual(set(fields),set(ocean_features.KINDS))
        self.assertGreater(np.nanmax(fields['sst_front']),0)
        self.assertGreater(np.nanmax(fields['convergence']),0)
    def test_land_mask_not_detected_as_front(self):
        sst=self.sst.copy();sst[10:14,10:14]=np.nan
        fields=ocean_features.diagnostics(self.lat,self.lon,sst,self.u,self.v)
        self.assertTrue(np.isnan(fields['sst_front'][9:15,9:15]).all())
    def test_grid_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            ocean_features.diagnostics(self.lat,self.lon,self.sst[:-1],self.u,self.v)
    def test_bank_candidates_georeferenced(self):
        fields=ocean_features.diagnostics(self.lat,self.lon,self.sst,self.u,self.v)
        banks,points=ocean_features._candidates(fields,self.lat,self.lon,[{'key':'b','name':'Bank','lat':18,'lon':-77}])
        self.assertIn('b',banks)
        for p in points:
            lon,lat=p['geometry']['coordinates']
            self.assertTrue(-78<=lon<=-76 and 17<=lat<=19)
            self.assertGreater(p['properties']['search_radius_km'],0)
    def test_persistence_uses_distinct_dates(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'feature-history.json'
            bank={'b':{'features':[{'kind':'sst_front','lat':18,'lon':-77}]}}
            ocean_features._history(path,bank,'2026-10-11')
            ocean_features._history(path,bank,'2026-10-12')
            ocean_features._history(path,bank,'2026-10-13')
            self.assertEqual(bank['b']['features'][0]['historical_matching_dates'],2)
            self.assertEqual(len(json.loads(path.read_text())['banks']['b']),3)
    def test_feature_history_corruption_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'feature-history.json';path.write_text('{broken')
            with self.assertRaises(json.JSONDecodeError):
                ocean_features._history(path,{'b':{'features':[]}},'2026-10-13')
            self.assertEqual(path.read_text(),'{broken')

if __name__=='__main__':unittest.main()
