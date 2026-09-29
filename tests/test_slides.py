"""v3.3 slide/evidence contract and offline navigation tests."""
from __future__ import annotations

import copy
import re
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_comprehensive_demo import make_comprehensive
from report_tools import render, validate


class SlideTests(unittest.TestCase):
    def setUp(self): self.r=make_comprehensive()

    def test_editorial_and_legacy_compatibility(self):
        self.assertTrue(validate(self.r, editorial=True)['valid'])
        old=copy.deepcopy(self.r)
        del old['presentation']
        for section in old['sections']:
            section.pop('evidence_points')
            section.pop('reasoning')
        self.assertTrue(validate(old)['valid'])
        self.assertFalse(validate(old,editorial=True)['valid'])
        with self.assertRaisesRegex(ValueError,'presentation.slides'): render(old,layout='slides')

    def test_evidence_references_checked(self):
        self.r['sections'][0]['evidence_points'][0]['metric_ids'][0]='missing_metric'
        result=validate(self.r)
        self.assertFalse(result['valid'])
        self.assertIn('引用不存在',str(result['errors']))

    def test_evidence_source_must_cover_metric(self):
        self.r['sections'][0]['evidence_points'][0]['source_ids']=['S13']
        result=validate(self.r)
        self.assertFalse(result['valid'])
        self.assertIn('缺少指标',str(result['errors']))

    def test_vague_headline_rejected_only_in_editorial_mode(self):
        self.r['sections'][0]['headline']='增长并不代表经营质量改善'
        self.assertTrue(validate(self.r)['valid'])
        self.assertFalse(validate(self.r,editorial=True)['valid'])

    def test_slide_plan_references_and_coverage(self):
        slides=self.r['presentation']['slides']
        self.assertGreaterEqual(len(slides),len(self.r['sections'])*2)
        self.assertEqual(slides[0]['kind'],'cover')
        self.assertEqual(slides[-1]['kind'],'back')
        bad=copy.deepcopy(self.r)
        next(s for s in bad['presentation']['slides'] if s['kind']=='analysis')['evidence_ids']=['bad']
        self.assertFalse(validate(bad)['valid'])
        bad=copy.deepcopy(self.r)
        bad['presentation']['slides']=[s for s in bad['presentation']['slides'] if s.get('section_id')!='D08' or s.get('phase')!='reasoning']
        self.assertIn('覆盖全部分析单元',str(validate(bad)['errors']))
        bad=copy.deepcopy(self.r)
        next(s for s in bad['presentation']['slides'] if s.get('section_id')=='O08' and s['kind']=='appendix')['row_end']=8
        self.assertIn('表格行遗漏或重复',str(validate(bad)['errors']))

    def test_navigation_anchors_and_offline(self):
        out=render(self.r,layout='slides')
        ids=re.findall(r'\bid="([^"]+)"',out)
        hrefs=re.findall(r'href="#([^"]+)"',out)
        self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue(set(hrefs)<=set(ids),set(hrefs)-set(ids))
        self.assertEqual(out.count('<section class="slide '),len(self.r['presentation']['slides']))
        self.assertIn("ArrowRight",out)
        self.assertIn('@page{size:13.333in 7.5in',out)
        self.assertNotRegex(out,r'(?:src|href)="https?://')
        self.assertIn('SL_appendix_D08',out)

    def test_html_escapes_untrusted_content(self):
        self.r['sections'][0]['evidence_points'][0]['statement']='<script>alert(1)</script>'
        out=render(self.r,layout='slides')
        self.assertNotIn('<script>alert(1)</script>',out)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;',out)


if __name__=='__main__': unittest.main()
