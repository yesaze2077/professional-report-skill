"""Long-report integrity tests. Not a certification of business analysis or true sources."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import re
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_comprehensive_demo import make_comprehensive
from report_tools import render, validate

class LongReportTests(unittest.TestCase):
    def setUp(self):self.r=make_comprehensive()
    def bad(self,token):
        result=validate(self.r)
        self.assertFalse(result['valid']);self.assertIn(token,' '.join(result['errors']))
    def test_demo_integrity(self):
        r=validate(self.r);self.assertTrue(r['valid']);self.assertFalse(r['warnings']);self.assertEqual(r['calculations_checked'],296)
    def test_deterministic(self):self.assertEqual(self.r,make_comprehensive())
    def test_comprehensive_needs_plan(self):del self.r['composition'];self.bad('composition')
    def test_comprehensive_needs_coverage(self):del self.r['coverage'];self.bad('coverage')
    def test_cover_first(self):self.r['composition']['pages'].reverse();self.bad('封面')
    def test_summary_unique(self):self.r['composition']['pages'][1]['kind']='summary';self.bad('唯一')
    def test_full_structure(self):
        kinds=[p['kind'] for p in self.r['composition']['pages']]
        self.assertEqual(kinds[:3],['cover','toc','summary']);self.assertEqual(kinds[-1],'back')
        self.assertEqual(kinds.count('visual'),2)
    def test_full_cover_metadata(self):del self.r['meta']['author'];self.bad('author')
    def test_visual_source_ref(self):
        p=next(p for p in self.r['composition']['pages'] if p['kind']=='visual')
        p['evidence_source_id']='ZZ';self.bad('视觉证据')
    def test_page_duplicate(self):self.r['composition']['pages'][1]['id']=self.r['composition']['pages'][0]['id'];self.bad('ID重复')
    def test_dom_namespace_collision(self):self.r['composition']['pages'][1]['id']='D01';self.bad('锚点ID冲突')
    def test_missing_section(self):
        p=next(p for p in self.r['composition']['pages'] if p['kind']=='content');self.r['composition']['pages'].remove(p);self.bad('遗漏分析单元')
    def test_duplicate_section(self):
        p=copy.deepcopy(next(p for p in self.r['composition']['pages'] if p['kind']=='content'));p['id']='Duplicate';self.r['composition']['pages'].append(p);self.bad('重复呈现分析单元')
    def test_missing_action(self):
        p=next(p for p in self.r['composition']['pages'] if p['kind']=='actions');p['action_ids'].pop();self.bad('遗漏完整行动')
    def test_missing_source(self):next(p for p in self.r['composition']['pages'] if p['kind']=='sources')['source_ids'].pop();self.bad('遗漏来源')
    def test_invalid_reference(self):next(p for p in self.r['composition']['pages'] if p['kind']=='sources')['source_ids'][0]='ZZ';self.bad('不存在')
    def test_wrong_payload_for_kind(self):self.r['composition']['pages'][1]['action_ids']=['A01'];self.bad('不接受')
    def test_covered_requires_evidence(self):self.r['coverage'][0]['section_ids']=[];self.bad('必须指向正文')
    def test_coverage_invalid_action(self):self.r['coverage'][0]['action_ids']=['Z'];self.bad('引用不存在')
    def test_duplicate_domain(self):self.r['coverage'].append(copy.deepcopy(self.r['coverage'][0]));self.bad('模块重复')
    def test_missing_next_step_is_warning(self):
        next(c for c in self.r['coverage'] if c['status']=='missing')['action_ids']=[]
        r=validate(self.r);self.assertTrue(r['valid']);self.assertTrue(r['warnings'])
    def test_all_pages_all_details(self):
        out=render(self.r)
        self.assertEqual(out.count('<section class="report-page '),45);self.assertEqual(out.count('<svg '),9)
        for coll in ['sections','actions']:
            for x in self.r[coll]:self.assertEqual(out.count('id="'+x['id']+'"'),1)
        for x in self.r['sources']:self.assertEqual(out.count('id="src-'+x['id']+'"'),1)
    def test_anchors_resolve(self):
        out=render(self.r);ids=re.findall(r'\bid="([^"]+)"',out);hrefs=re.findall(r'href="#([^"]+)"',out)
        self.assertEqual(len(ids),len(set(ids)));self.assertTrue(set(hrefs)<=set(ids))
    def test_all_12_actions_in_overview(self):
        ss={s['id']:s for s in self.r['sections']};rows=ss['O06']['table']['rows']+ss['O07']['table']['rows']
        self.assertEqual(len(rows),12)
        for row,action in zip(rows,self.r['actions']):
            self.assertTrue(row[0].startswith(action['id']));self.assertEqual(row[3],action['timing']);self.assertEqual(row[4],action['related_sections'][0])
    def test_customer_definitions_not_contradictory(self):
        ss={s['id']:s for s in self.r['sections']};s=json.dumps(self.r,ensure_ascii=False)
        self.assertNotIn('当季新客无季度内追加订单',s);self.assertNotIn('当季新客没有季度内追加订单',s)
        self.assertIn('非首单',ss['D13']['headline'])
        for q,months in [('q1',['jan','feb','mar']),('q2',['apr','may','jun'])]:
            mm=self.r['metrics'];v=lambda k:mm[k]['value']
            self.assertEqual(sum(v(m+'_cohort_n') for m in months),v(q+'_new_buyers'))
    def test_mature_windows_not_zero(self):
        for key in ['jun_rate30','may_rate60','apr_rate90']:
            x=self.r['metrics'][key];self.assertIsNone(x['value']);self.assertEqual(x['status'],'pending')
    def test_all_device_channel_reconciliations(self):
        v=lambda k:self.r['metrics'][k]['value']
        for p in ['q1','q2']:
            for ch in ['paid','organic','email','direct']:
                for field in ['sessions','orders']:
                    self.assertEqual(v(p+'_mobile_'+ch+'_'+field)+v(p+'_desktop_'+ch+'_'+field),v(ch+'_'+p+'_'+field))
    def test_plan_not_fixed_to_45(self):
        self.r['composition']['pages'].remove(next(p for p in self.r['composition']['pages'] if p['kind']=='visual'))
        self.assertTrue(validate(self.r)['valid'])
        out=render(self.r);self.assertEqual(out.count('<section class="report-page '),44);self.assertIn('44 / 44',out)
    def test_no_network_or_script(self):
        out=render(self.r);self.assertNotIn('<script',out);self.assertNotIn('src="http',out);self.assertIn('lang="zh-CN"',out)
    def test_escaping_still_applies(self):
        self.r['sections'][0]['paragraphs'][0]='<script>bad()</script>'
        out=render(self.r);self.assertNotIn('<script>',out);self.assertIn('&lt;script&gt;',out)
    def test_real_report_provenance_not_declared_synthetic(self):
        self.r['meta']['synthetic']=False;out=render(self.r)
        self.assertNotIn('本页列示的是合成数据字典与假设',out)
    def test_declared_membership_gap_not_silently_omitted(self):
        c=next(x for x in self.r['coverage'] if x['domain']=='会员与推荐机制');self.assertEqual(c['status'],'missing');self.assertTrue(c['action_ids'])

if __name__=='__main__':unittest.main()
