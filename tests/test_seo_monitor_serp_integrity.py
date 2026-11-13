import json
import tempfile
import unittest
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
from seo_monitor.checks import rank, backlink_gap
from seo_monitor.config import Settings, load_config
from seo_monitor.storage import Store

WRAP = 'https://google.com/goto?url=opaque'
ROW = dict(keyword='vuelo en globo segovia', language_code='es', location_name='Segovia Spain', device='mobile', priority='P0', cluster='segovia', target_url='https://www.voyagerballoons.eu/vuelo-en-globo-segovia')

def organic(url, breadcrumb=None, position=12):
    return dict(type='organic', url=url, breadcrumb=breadcrumb, rank_absolute=position)

class SerpIntegrityTests(unittest.TestCase):
    def test_observed_wrapper_recovers_domain_not_landing(self):
        rows, match = rank._interpret_serp({'items':[organic(WRAP,'https://www.voyagerballoons.eu')]}, {'voyagerballoons.eu'})
        self.assertEqual(match['resolved_domain'],'voyagerballoons.eu')
        self.assertIsNone(match['resolved_url'])
        self.assertEqual(match['rank_absolute'],12)

    def test_unresolved_wrapper_cannot_prove_absence(self):
        with self.assertRaises(rank.SearchError):
            rank._interpret_serp({'items':[organic(WRAP,'Más de 100 Me gusta')]}, {'voyagerballoons.eu'})

    def test_empty_organic_cannot_prove_absence(self):
        with self.assertRaises(rank.SearchError): rank._interpret_serp({'items':None}, {'voyagerballoons.eu'})

    def test_unknown_before_match_cannot_prove_first_position(self):
        with self.assertRaises(rank.SearchError):
            rank._interpret_serp({'items':[organic(WRAP),organic(WRAP,'https://voyagerballoons.eu')]}, {'voyagerballoons.eu'})

    def test_unknown_after_match_does_not_hide_known_position(self):
        _, match = rank._interpret_serp({'items':[organic(WRAP,'https://voyagerballoons.eu'),organic(WRAP)]}, {'voyagerballoons.eu'})
        self.assertEqual(match['rank_absolute'],12)

    def test_different_domain_is_not_target(self):
        _, match = rank._interpret_serp({'items':[organic(WRAP,'https://voyagerballoons.eu.evil.test')]}, {'voyagerballoons.eu'})
        self.assertIsNone(match)

    def test_normal_url_preserves_exact_landing(self):
        _, match = rank._interpret_serp({'items':[organic(ROW['target_url'])]}, {'voyagerballoons.eu'})
        self.assertEqual(match['resolved_url'],ROW['target_url'])

    def test_poisoned_history_excluded_without_erasing_original(self):
        item=SimpleNamespace(payload_json=json.dumps({'top_results':[{'url':WRAP}]}))
        self.assertFalse(rank._valid_history(item))
        self.assertTrue(rank._valid_history(SimpleNamespace(payload_json='{"serp_identity_version":1}')))

    def test_null_serp_response_preserves_provider_cost(self):
        response=SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'tasks':[{'status_code':20000,'cost':0.004,'result':None}]})
        with patch.object(rank.requests,'post',return_value=response):
            with self.assertRaises(rank.SearchError) as ctx: rank._search(Settings.from_env(),ROW,20)
        self.assertEqual(ctx.exception.cost,0.004)

    def test_run_records_recovered_domain_and_no_false_landing_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store('sqlite:///'+str(Path(d)/'s.db'));store.initialize()
            settings=replace(Settings.from_env(), dataforseo_login='x',dataforseo_password='x')
            with patch.object(rank,'load_keyword_inventory',return_value=[ROW]),patch.object(rank,'_search',return_value=({'items':[organic(WRAP,'https://www.voyagerballoons.eu')]},0.004)):
                run=store.start_job('rank');result=rank.run(load_config(settings),store,run,settings);store.save_result(run,result)
            self.assertEqual(result.summary['found_in_requested_depth'],1)
            self.assertEqual(result.alerts,[])
            self.assertIsNone(store.keyword_ranking_history(ROW['keyword'],ROW['location_name'],'mobile')[0].ranking_url)

    def test_invalid_run_keeps_existing_real_alert_and_does_not_save_false_position(self):
        from seo_monitor.types import CheckResult,AlertSpec
        with tempfile.TemporaryDirectory() as d:
            store=Store('sqlite:///'+str(Path(d)/'s.db'));store.initialize()
            settings=replace(Settings.from_env(), dataforseo_login='x',dataforseo_password='x')
            key='rank:voyager:es:Segovia Spain:mobile:vuelo en globo segovia:drop'
            prior=CheckResult(job_name='rank');prior.alerts=[AlertSpec(dedupe_key=key,severity='P2',category='rank',title='real',message='real',action='check')]
            store.save_result(store.start_job('rank'),prior)
            with patch.object(rank,'load_keyword_inventory',return_value=[ROW]),patch.object(rank,'_search',return_value=({'items':[organic(WRAP)]},0.004)):
                run=store.start_job('rank');result=rank.run(load_config(settings),store,run,settings);store.save_result(run,result)
            self.assertEqual(result.summary['keywords_checked'],0)
            self.assertEqual(result.summary['provider_cost_usd'],0.004)
            self.assertFalse(result.summary['measurement_complete'])
            self.assertIn(key,[a.dedupe_key for a in store.open_alerts()])
            self.assertEqual(store.keyword_ranking_history(ROW['keyword'],ROW['location_name'],'mobile'),[])

class LegacyBacklinkTests(unittest.TestCase):
    config={'tracking':{'legacy_shop_domain':'shop.voyagerballoons.eu'}}
    def record(self,*urls):
        return dict(domain='aosabordovento.net',url='https://aosabordovento.net',miss_streak=7,links=[{'target_url':u} for u in urls])
    def test_only_legacy_targets_remain_open_observation(self):
        a=backlink_gap._lost_alert(self.record('https://shop.voyagerballoons.eu/cart/?add-to-cart=4174'),self.config)
        self.assertEqual(a.severity,'P3');self.assertTrue(a.metadata['legacy_targets_only']);self.assertIn('retirada',a.title)
    def test_current_target_stays_urgent(self):
        a=backlink_gap._lost_alert(self.record('https://www.voyagerballoons.eu/'),self.config)
        self.assertEqual(a.severity,'P1')
    def test_mixed_targets_stay_urgent(self):
        a=backlink_gap._lost_alert(self.record('https://shop.voyagerballoons.eu/cart','https://www.voyagerballoons.eu/'),self.config)
        self.assertEqual(a.severity,'P1')
    def test_missing_evidence_or_configuration_cannot_downgrade(self):
        for rec,cfg in [(self.record(),self.config),(self.record(None),self.config),(self.record('https://shop.voyagerballoons.eu/cart'),{})]:
            self.assertFalse(backlink_gap._legacy_only_loss(rec,cfg))
