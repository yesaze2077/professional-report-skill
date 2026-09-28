"""Bounded regression checks; no external service, source truth or semantic guarantees."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from report_tools import calculate, number, read_json, render, validate, write_new, P
from build_demo import make_demo


class ReportTests(unittest.TestCase):
    def setUp(self):self.r=make_demo()
    def bad(self,expected=''):
        v=validate(self.r);self.assertFalse(v['valid'])
        if expected:self.assertIn(expected,' '.join(v['errors']))
    def test_demo_valid(self):
        v=validate(self.r);self.assertTrue(v['valid']);self.assertEqual(v['calculations_checked'],34)
    def test_demo_deterministic(self):self.assertEqual(make_demo(),make_demo())
    def test_unknown_field(self):self.r['unknown']=1;self.bad('未知字段')
    def test_missing_required(self):del self.r['meta']['period'];self.bad('缺少必填')
    def test_language_contract(self):self.r['meta']['language']='en-US';self.bad()
    def test_bool_not_number(self):self.r['metrics']['paid_q1']['value']=True;self.bad('类型')
    def test_nan_rejected(self):self.r['metrics']['paid_q1']['value']=float('nan');self.bad('有限')
    def test_duplicate_source(self):self.r['sources'].append(copy.deepcopy(self.r['sources'][0]));self.bad('ID重复')
    def test_unknown_source(self):self.r['metrics']['paid_q1']['source_id']='not_found';self.bad('来源不存在')
    def test_unsafe_source(self):self.r['sources'][0]['locator']='javascript:alert(1)';self.bad('禁止危险')
    def test_source_absolute_path(self):self.r['sources'][0]['locator']='/'+'Users'+'/placeholder/data.json';self.bad('机器绝对路径')
    def test_source_credential(self):self.r['sources'][0]['locator']='https://'+'name:secret'+'@'+'example.invalid/data';self.bad('凭据')
    def test_missing_not_zero(self):self.r['metrics']['paid_q1']['status']='missing';self.bad('null')
    def test_null_not_observed(self):self.r['metrics']['paid_q1']['value']=None;self.bad('null')
    def test_ratio_scale(self):self.r['metrics']['achievement']['value']=96;self.bad('比例')
    def test_wrong_arithmetic(self):self.r['metrics']['sales_growth']['value']=.3;self.bad('计算结果')
    def test_table_width(self):self.r['sections'][1]['table']['rows'][0].pop();self.bad('列数')
    def test_table_reference(self):self.r['sections'][1]['table']['rows'][0][1]['metric_id']='absent';self.bad('引用不存在')
    def test_waterfall_mismatch(self):self.r['metrics']['sales_q2']['value']+=1;self.bad('瀑布图')
    def test_waterfall_roles(self):self.r['sections'][0]['chart']['rows'][0]['role']='delta';self.bad('起点')
    def test_unsupported_chart(self):self.r['sections'][0]['chart']['type']='sunburst';self.bad()
    def test_missing_series_label(self):del self.r['sections'][1]['chart']['series_labels'];self.bad('时期名称')
    def test_chart_row_extra(self):self.r['sections'][1]['chart']['rows'][0]['metric_id']='sales_q1';self.bad('图行字段')
    def test_clipped_axis(self):self.r['sections'][1]['chart']['y_max']=3;self.bad('截掉')
    def test_manual_bar_baseline(self):self.r['sections'][2]['chart']['y_min']=10;self.bad('零基线')
    def test_chart_provenance(self):self.r['sections'][1]['chart']['source_ids']=['S1'];self.bad('图表来源')
    def test_action_reference(self):self.r['actions'][0]['related_sections']=['absent'];self.bad('引用不存在')
    def test_causal_warn_not_certification(self):
        self.r['sections'][0]['claim_type']='causal';v=validate(self.r)
        self.assertTrue(v['valid']);self.assertTrue(v['warnings'])
    def test_missing_checks_warn(self):self.r['checks']=[];self.assertTrue(validate(self.r)['warnings'])
    def test_sensitive_email(self):self.r['summary']['bottom_line']='contact'+'@'+'example.invalid';self.bad('邮箱')
    def test_escape_html(self):
        self.r['summary']['bottom_line']='<script>alert(1)</script>'
        out=render(self.r);self.assertNotIn('<script>',out);self.assertIn('&lt;script&gt;',out)
    def test_selfcontained_html(self):
        out=render(self.r);self.assertNotIn('<script',out);self.assertNotIn('src="http',out)
        self.assertIn('lang="zh-CN"',out);self.assertEqual(out.count('<svg '),3)
    def test_report_page_count(self):self.assertEqual(render(self.r).count('<section class="report-page">'),7)
    def test_line_gap(self):
        c=self.r['sections'][0]['chart']
        c.update(type='line',rows=[dict(label='1月',metric_id='paid_q1'),dict(label='2月',metric_id='gap'),dict(label='3月',metric_id='paid_q2')])
        self.r['metrics']['gap']=dict(value=None,unit='美元',status='missing',source_id='S1')
        self.assertTrue(validate(self.r)['valid']);out=render(self.r)
        self.assertIn('未提供',out);self.assertNotIn('class="trend"',out)
    def test_line_min_periods(self):
        self.r['sections'][0]['chart'].update(type='line',rows=[dict(label='1月',metric_id='paid_q1'),dict(label='2月',metric_id='paid_q2')]);self.bad('三个')
    def test_all_missing_chart(self):
        self.r['sections'][2]['chart']['rows']=[dict(label='缺失项',metric_id='missing_item')]
        self.r['metrics']['missing_item']=dict(value=None,unit='条',status='missing',source_id='S3');self.bad('没有可呈现')
    def test_non_synthetic_no_demo_claim(self):
        self.r['meta']['synthetic']=False;out=render(self.r)
        self.assertNotIn('下列动作为合成案例演示',out)
    def test_unbounded_contribution(self):
        self.r['metrics']['negative_contribution']=dict(value=-1.5,unit='净增量份额',status='calculated',source_id='S1')
        self.r['metrics']['large_contribution']=dict(value=2.5,unit='净增量份额',status='calculated',source_id='S1')
        self.assertTrue(validate(self.r)['valid']);self.assertEqual(number(2.5,.01,0,'%'),'250%')
    def test_normal_line_render(self):
        self.r['sections'][0]['chart'].update(type='line',rows=[dict(label='一月',metric_id='paid_q1'),dict(label='二月',metric_id='organic_q1'),dict(label='三月',metric_id='paid_q2')])
        self.assertEqual(render(self.r).count('class="trend"'),2)
    def test_zero_bar_render(self):
        self.r['sections'][2]['chart']['rows']=[dict(label='零值',metric_id='zero_item')]
        self.r['metrics']['zero_item']=dict(value=0,unit='条',status='synthetic',source_id='S3')
        self.assertIn('零值',render(self.r))
    def test_chinese_value_unit_stays_together(self):
        self.assertIn('<span class="nowrap">0.52个百分点</span>',P('下降0.52个百分点'))
    def test_format_wan(self):self.assertEqual(number(1440000,10000,0,'万美元'),'144万美元')
    def test_format_percentage(self):self.assertEqual(number(.0288,.01,2,'%'),'2.88%')
    def test_format_round_half_up(self):self.assertEqual(number(2.345,1,2),'2.35')
    def test_negative_zero(self):self.assertEqual(number(-.00001,1,2),'0.00')
    def test_missing_display(self):self.assertEqual(number(None,status='pending'),'待更新')
    def test_pp_calculation(self):self.assertAlmostEqual(calculate('pp_change',[.024,.03]),-.6)
    def test_relative_change(self):self.assertAlmostEqual(calculate('relative_change',[144,120]),.2)
    def test_zero_baseline(self):
        with self.assertRaises(ValueError):calculate('relative_change',[2,0])
    def test_negative_baseline(self):
        with self.assertRaises(ValueError):calculate('relative_change',[2,-1])
    def test_zero_denominator(self):
        with self.assertRaises(ValueError):calculate('ratio',[2,0])
    def test_pp_input_scale(self):
        with self.assertRaises(ValueError):calculate('pp_change',[2.4,3])
    def test_weighted_total(self):
        m=self.r['metrics'];self.assertEqual(m['total_q2_cvr']['value'],7200/250000)
        self.assertNotEqual(m['total_q2_cvr']['value'],(.024+.04)/2)
    def test_write_protect(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'sample.html';write_new(p,'old')
            with self.assertRaises(FileExistsError):write_new(p,'new')
            self.assertEqual(p.read_text(),'old');write_new(p,'new',force=True);self.assertEqual(p.read_text(),'new')
    def test_json_duplicate_key(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(ValueError):read_json(p)
    def test_json_nan(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.json';p.write_text('{"a":NaN}')
            with self.assertRaises(ValueError):read_json(p)


if __name__=='__main__':unittest.main()
