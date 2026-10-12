import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bank_history
import history_storage
from recover_history import merge

ROOT=Path(__file__).resolve().parents[1]
GENERATE=(ROOT/'generate.py').read_text()
WORKFLOW=(ROOT/'.github/workflows/currents.yml').read_text()

class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'bank-history.json'
        self.now=datetime(2026,10,12,tzinfo=timezone.utc)
        self.bank={'key':'mackerel','sst_c':27.2,'chlorophyll_mg_m3':.22,'current_knots':1.2,
                   'sst_time_utc':'2026-10-11T12:00:00Z','current_time_utc':'2026-10-11T12:00:00Z',
                   'chlorophyll_date':'2026-10-10','species_scores':{}}
    def tearDown(self):self.tmp.cleanup()
    def test_two_years_and_no_90_snapshot_cap(self):
        rows=[]
        for i in range(140):
            day=(self.now-timedelta(days=i*4)).date().isoformat()
            rows.append({'sst_date':day,'current_date':day,'chlorophyll_date':day,'sst_c':26,'chlorophyll_mg_m3':.2,'current_knots':1})
        self.path.write_text(json.dumps({'banks':{'mackerel':rows}}))
        result=bank_history.update(self.path,[self.bank],now=self.now)
        self.assertEqual(result['retention_days'],730)
        self.assertGreater(len(result['banks']['mackerel']),90)
    def test_expired_inactive_banks_removed(self):
        self.path.write_text(json.dumps({'banks':{'inactive':[{'sst_date':'2020-01-01'}]}}))
        result=bank_history.update(self.path,[],now=self.now)
        self.assertEqual(result['banks']['inactive'],[])
    def test_corrupt_history_fails_closed(self):
        self.path.write_text('{broken')
        with self.assertRaises(ValueError):bank_history.update(self.path,[self.bank],now=self.now)
        self.assertEqual(self.path.read_text(),'{broken')
    def test_no_duplicate_observation(self):
        first=bank_history.update(self.path,[self.bank],now=self.now)
        second=bank_history.update(self.path,[self.bank],now=self.now+timedelta(hours=1))
        self.assertEqual(len(first['banks']['mackerel']),len(second['banks']['mackerel']))
    def test_merge_no_overwrite(self):
        original={'banks':{'x':[{'sst_date':'2026-01-01','score_model_version':'v1','sst_c':26}]}}
        extra={'banks':{'x':[{'sst_date':'2026-01-01','score_model_version':'v1','sst_c':99},{'sst_date':'2026-02-01','score_model_version':'v1'}]}}
        result,count=merge(original,[extra]);self.assertEqual(count,1);self.assertEqual(result['banks']['x'][0]['sst_c'],26)
    def test_invalid_archive_rejected(self):
        with self.assertRaises(ValueError):history_storage.validate_history(b'{"banks":{"x":{}}}')
    def test_missing_existing_remote_file_fails(self):
        with patch.object(history_storage,'request',return_value={'object':{'sha':'abc'}}),patch.object(history_storage,'get_content',return_value=None):
            with self.assertRaises(RuntimeError):history_storage.restore()
    def test_save_verifies_remote_checksum(self):
        with patch.object(history_storage,'LOCAL',self.path),patch.object(history_storage,'request',side_effect=[{'object':{'sha':'abc'}},{'content':{'sha':'saved'}}]),patch.object(history_storage,'get_content',return_value={'sha':'old','content':'e30='}):
            self.path.write_text(json.dumps({'banks':{'x':[{'sst_date':'2026-10-01'}]}}))
            with self.assertRaises(RuntimeError):history_storage.save()

class SiteTests(unittest.TestCase):
    def test_overlay_order(self):
        self.assertLess(GENERATE.index('value="waves"'),GENERATE.index('value="eddies"'))
    def test_default_fad(self):
        self.assertIn('<option value="1day" selected>FAD 1DAY</option>',GENERATE)
    def test_heading_date_line_absent(self):
        self.assertNotIn('Chl: ',(ROOT/'composite.py').read_text())
        self.assertIn("status.textContent='';status.hidden=true",GENERATE)
    def test_saturday_logic(self):
        self.assertIn('days_ahead = (5 - local_now.weekday()) % 7',GENERATE)
        self.assertIn("if key == 'weekend':",GENERATE)
        self.assertIn('Weekend forecast not yet available',GENERATE)
        self.assertIn('model time too far from requested target',GENERATE)
    def test_freshness(self):
        self.assertIn("chlAge<=1?'Current':chlAge<=3?'Delayed':'Stale'",GENERATE)
        self.assertIn("timeZone:'America/Jamaica'",GENERATE)
    def test_workflow(self):
        self.assertIn('python history_storage.py restore',WORKFLOW)
        self.assertIn('python history_storage.py save',WORKFLOW)
        self.assertIn('python -m unittest discover -s tests -v',WORKFLOW)
        self.assertIn('contents: write',WORKFLOW)
        self.assertEqual(WORKFLOW.count("- cron:"),1)
        self.assertIn('15 5,11,17,23',WORKFLOW)

if __name__=='__main__':unittest.main()
