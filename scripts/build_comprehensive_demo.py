#!/usr/bin/env python3
"""Deterministic, synthetic 45-page ecommerce diagnosis example. No network or real data.

Extends the v3.0 illustrative scale, not a real company's records. All quantitative
source tables, named calculations, coverage and page composition are retained in JSON.
"""
from __future__ import annotations
import argparse
import json
from report_tools import ROOT, calculate, number, validate, write_new, render


def make_comprehensive() -> dict:
    M={};checks=[];sections=[];actions=[];pages=[]
    def m(k,v,u='美元',src='S01',status='synthetic'):
        M[k]=dict(value=v,unit=u,status=status,source_id=src);return k
    def v(k):return M[k]['value']
    def c(k,op,ids,u='美元',src='S01',status='calculated'):
        value=calculate(op,[v(x) for x in ids]);m(k,value,u,src,status)
        checks.append(dict(id='C_'+k,op=op,inputs=ids,result_metric=k,tolerance=1e-7));return k
    def ratio(k,a,b,src='S01',u='比例'):return c(k,'ratio',[a,b],u,src)
    def delta(k,a,b,src='S01',u='美元'):return c(k,'difference',[a,b],u,src)
    def cell(k,scale=1,d=0,suffix=''):return dict(metric_id=k,scale=scale,decimals=d,suffix=suffix)
    def cash(k):return cell(k,10000,1,'')
    def pct(k,d=1):return cell(k,.01,d,'%')
    def fmt(k,scale=1,d=1,suffix=''):return number(v(k),scale,d,suffix,M[k]['status'])
    def money(k,d=1):return fmt(k,10000,d,'万美元')
    def per(k,d=1):return fmt(k,.01,d,'%')
    # Reconciled commercial records.
    for p,vals in [('q1',(1400000,140000,60000,6800,200000,1500000)),('q2',(1800000,270000,90000,7200,250000,1500000)),('ly',(1260000,126000,54000,6000,180000,1100000))]:
        gross,discount,refund,orders,sessions,target=vals
        for name,value,unit,src in [('gross',gross,'美元','S01'),('discount',discount,'美元','S01'),('refund',refund,'美元','S01'),('orders',orders,'单','S01'),('sessions',sessions,'次','S02'),('target',target,'美元','S12')]:m(p+'_'+name,value,unit,src)
        delta(p+'_after_discount',p+'_gross',p+'_discount')
        delta(p+'_net',p+'_after_discount',p+'_refund')
        ratio(p+'_aov',p+'_net',p+'_orders',u='美元／单')
        ratio(p+'_cvr',p+'_orders',p+'_sessions','S02')
        ratio(p+'_achievement',p+'_net',p+'_target')
        ratio(p+'_discount_rate',p+'_discount',p+'_gross')
        ratio(p+'_refund_ratio',p+'_refund',p+'_after_discount')
        ratio(p+'_gross_aov',p+'_gross',p+'_orders',u='美元／单')
        ratio(p+'_discount_aov',p+'_discount',p+'_orders',u='美元／单')
        ratio(p+'_refund_aov',p+'_refund',p+'_orders',u='美元／单')
    for metric,unit,src in [('net','美元','S01'),('orders','单','S01'),('aov','美元／单','S01'),('sessions','次','S02')]:
        delta(metric+'_delta','q2_'+metric,'q1_'+metric,src,unit)
        c(metric+'_growth','relative_change',['q2_'+metric,'q1_'+metric],'相对变化率',src)
    c('net_yoy','relative_change',['q2_net','ly_net'],'相对变化率')
    delta('target_gap','q2_net','q2_target')
    c('cvr_pp','pp_change',['q2_cvr','q1_cvr'],'个百分点','S02')
    for p,vals in [('q1',(552000,96000,36000,180000,24000)),('q2',(720000,129600,43200,240000,31200))]:
        for k,a in zip(['cogs','fulfill','fees','ads','crm_cost'],vals):m(p+'_'+k,a,'美元','S03')
        c(p+'_variable_cost','sum',[p+'_'+k for k in ['cogs','fulfill','fees','ads','crm_cost']],'美元','S03')
        delta(p+'_contribution',p+'_net',p+'_variable_cost','S03')
        ratio(p+'_contribution_rate',p+'_contribution',p+'_net','S03')
        delta(p+'_gross_profit',p+'_net',p+'_cogs','S03')
        ratio(p+'_gross_margin',p+'_gross_profit',p+'_net','S03')
        c(p+'_pre_marketing_cost','sum',[p+'_'+k for k in ['cogs','fulfill','fees']],'美元','S03')
        delta(p+'_pre_marketing_contribution',p+'_net',p+'_pre_marketing_cost','S03')
        ratio(p+'_pre_marketing_rate',p+'_pre_marketing_contribution',p+'_net','S03')
    delta('contribution_delta','q2_contribution','q1_contribution','S03')
    c('contribution_growth','relative_change',['q2_contribution','q1_contribution'],'相对变化率','S03')
    for k in ['cogs','fulfill','fees','ads','crm_cost']:
        # Cost rises are negative steps in the contribution bridge.
        delta(k+'_bridge','q1_'+k,'q2_'+k,'S03')
    channels=[('paid','付费渠道',600000,780000,100000,140000,3000,3300),('organic','自然搜索',300000,330000,60000,64000,1800,1900),('email','邮件归属',180000,190000,20000,24000,1000,1050),('direct','直接及其他',120000,140000,20000,22000,1000,950)]
    for name,label,s1,s2,t1,t2,o1,o2 in channels:
        for p,s,t,o in [('q1',s1,t1,o1),('q2',s2,t2,o2)]:
            m(name+'_'+p+'_sales',s,'美元','S01');m(name+'_'+p+'_sessions',t,'次','S02');m(name+'_'+p+'_orders',o,'单','S01')
            ratio(name+'_'+p+'_cvr',name+'_'+p+'_orders',name+'_'+p+'_sessions','S02')
            ratio(name+'_'+p+'_mix',name+'_'+p+'_sales',p+'_net')
        delta(name+'_delta',name+'_q2_sales',name+'_q1_sales')
        ratio(name+'_increment_share',name+'_delta','net_delta',u='净增量份额')
    for p in ['q1','q2']:
        for suffix,target in [('sales','net'),('sessions','sessions'),('orders','orders')]:
            checks.append(dict(id='C_channel_'+p+'_'+suffix,op='sum',inputs=[x[0]+'_'+p+'_'+suffix for x in channels],result_metric=p+'_'+target,tolerance=1e-7))
    # Device/channel cuts match channel and site totals exactly.
    device_rows={
      'q1':{'mobile':[(70000,1700),(30000,850),(10000,500),(10000,550)],'desktop':[(30000,1300),(30000,950),(10000,500),(10000,450)]},
      'q2':{'mobile':[(105000,2100),(42000,1000),(14000,550),(14000,550)],'desktop':[(35000,1200),(22000,900),(10000,500),(8000,400)]}}
    for p,devs in device_rows.items():
        for dev,arr in devs.items():
            for (channel,*_), (ss,oo) in zip(channels,arr):
                key=p+'_'+dev+'_'+channel
                m(key+'_sessions',ss,'次','S02');m(key+'_orders',oo,'单','S02');ratio(key+'_cvr',key+'_orders',key+'_sessions','S02')
            for field,u in [('sessions','次'),('orders','单')]:c(p+'_'+dev+'_'+field,'sum',[p+'_'+dev+'_'+x[0]+'_'+field for x in channels],u,'S02')
            ratio(p+'_'+dev+'_cvr',p+'_'+dev+'_orders',p+'_'+dev+'_sessions','S02');ratio(p+'_'+dev+'_share',p+'_'+dev+'_sessions',p+'_sessions','S02')
        for field in ['sessions','orders']:
            checks.append(dict(id='C_device_'+p+'_'+field,op='sum',inputs=[p+'_'+d+'_'+field for d in ['mobile','desktop']],result_metric=p+'_'+field,tolerance=1e-7))
    for dev in ['mobile','desktop']:c(dev+'_pp','pp_change',['q2_'+dev+'_cvr','q1_'+dev+'_cvr'],'个百分点','S02')
    for p,arr in [('q1',[120000,90000,16000,6000,3600]),('q2',[175000,122500,17500,7000,4200])]:
        st=['visit','pdp','cart','checkout','paid']
        for k,n in zip(st,arr):m(p+'_funnel_'+k,n,'次','S02')
        for a,b in zip(st[1:],st[:-1]):ratio(p+'_'+a+'_step',p+'_funnel_'+a,p+'_funnel_'+b,'S02')
    # Sequential decomposition: traffic, then conversion, then order value.
    c('traffic_index','ratio',['q2_sessions','q1_sessions'],'倍数','S02')
    c('sales_at_traffic','multiply',['q1_net','traffic_index'])
    delta('traffic_bridge','sales_at_traffic','q1_net')
    ratio('cvr_index','q2_cvr','q1_cvr','S02','倍数')
    c('sales_at_cvr','multiply',['sales_at_traffic','cvr_index'])
    delta('cvr_bridge','sales_at_cvr','sales_at_traffic')
    delta('aov_bridge','q2_net','sales_at_cvr')
    for dev in ['mobile','desktop']:c('mix_'+dev,'multiply',['q2_'+dev+'_share','q1_'+dev+'_cvr'],'比例','S02')
    c('mixed_cvr','sum',['mix_mobile','mix_desktop'],'比例','S02')
    c('mix_pp','pp_change',['mixed_cvr','q1_cvr'],'个百分点','S02');c('within_pp','pp_change',['q2_cvr','mixed_cvr'],'个百分点','S02')
    # Paid acquisition and source-attributed first purchasers.
    for p,ss in [('q1',[(420000,110000,1200),(180000,70000,800)]),('q2',[(500000,135000,1300),(280000,105000,850)])]:
        for group,vals in zip(['search','social'],ss):
            for k,value,u in zip(['sales','spend','new'],vals,['美元','美元','人']):m(p+'_'+group+'_'+k,value,u,'S04')
            ratio(p+'_'+group+'_cac',p+'_'+group+'_spend',p+'_'+group+'_new','S04','美元／人')
            ratio(p+'_'+group+'_roas',p+'_'+group+'_sales',p+'_'+group+'_spend','S04','倍数')
        c(p+'_paid_new','sum',[p+'_search_new',p+'_social_new'],'人','S04')
        ratio(p+'_paid_cac',p+'_ads',p+'_paid_new','S04','美元／人')
        ratio(p+'_paid_roas','paid_'+p+'_sales',p+'_ads','S04','倍数')
        for kind,result in [('sales','paid_'+p+'_sales'),('spend',p+'_ads')]:checks.append(dict(id='C_paid_'+p+'_'+kind,op='sum',inputs=[p+'_search_'+kind,p+'_social_'+kind],result_metric=result,tolerance=1e-7))
    c('paid_cac_growth','relative_change',['q2_paid_cac','q1_paid_cac'],'相对变化率','S04')
    # Search and page evidence are bounded observations, not market research.
    for p,arr in [('q1',[8000000,90000,2000000,35000,6000000,55000]),('q2',[9000000,96000,2200000,40000,6800000,56000])]:
        for k,n in zip(['impressions','clicks','brand_impressions','brand_clicks','nonbrand_impressions','nonbrand_clicks'],arr):m(p+'_search_'+k,n,'次','S05')
        for k in ['','brand_','nonbrand_']:ratio(p+'_search_'+k+'ctr',p+'_search_'+k+'clicks',p+'_search_'+k+'impressions','S05')
    m('audit_pdp_n',24,'页','S05')
    for k,n in [('audit_fitment_gap',9),('audit_instruction_gap',7),('audit_delivery_gap',10),('audit_heavy_media',8)]:m(k,n,'页','S05')
    for p,lcp,inp in [('q1',3.8,260),('q2',4.6,340)]:m(p+'_lcp',lcp,'秒','S05');m(p+'_inp',inp,'毫秒','S05')
    # Products and stock.
    cats=[('protection','防护与车身',480000,648000,240000,356400),('storage','储物与运输',300000,345600,138000,179712),('electric','照明与电气',240000,259200,108000,116640),('comfort','舒适与其他',180000,187200,66000,67248)]
    for k,label,s1,s2,c1,c2 in cats:
        for p,sales,cost in [('q1',s1,c1),('q2',s2,c2)]:
            m(p+'_'+k+'_sales',sales,'美元','S06');m(p+'_'+k+'_cost',cost,'美元','S06')
            delta(p+'_'+k+'_gross',p+'_'+k+'_sales',p+'_'+k+'_cost','S06');ratio(p+'_'+k+'_margin',p+'_'+k+'_gross',p+'_'+k+'_sales','S06');ratio(p+'_'+k+'_share',p+'_'+k+'_sales',p+'_net','S06')
    for p in ['q1','q2']:
        for field,result in [('sales',p+'_net'),('cost',p+'_cogs')]:checks.append(dict(id='C_product_'+p+'_'+field,op='sum',inputs=[p+'_'+x[0]+'_'+field for x in cats],result_metric=result,tolerance=1e-7))
    for p,top,inv,old in [('q1',600000,750000,150000),('q2',936000,900000,270000)]:
        m(p+'_top20_sales',top,'美元','S06');ratio(p+'_top20_share',p+'_top20_sales',p+'_net','S06')
        m(p+'_inventory',inv,'美元','S06');m(p+'_aged_inventory',old,'美元','S06');ratio(p+'_aged_share',p+'_aged_inventory',p+'_inventory','S06')
    m('top20_sku_count',20,'个','S06');m('top20_oos_count',5,'个','S06');m('active_sku_count',500,'个','S06');m('aged_sku_count',186,'个','S06')
    # Customer totals and mature cohorts.
    for p,arr in [('q1',[4000,1800,4000,2800,720000,480000]),('q2',[4200,1900,4200,3000,840000,600000])]:
        for k,a,u in zip(['new_buyers','return_buyers','first_orders','return_orders','first_sales','return_sales'],arr,['人','人','单','单','美元','美元']):m(p+'_'+k,a,u,'S07')
        c(p+'_buyers','sum',[p+'_new_buyers',p+'_return_buyers'],'人','S07')
        ratio(p+'_return_order_share',p+'_return_orders',p+'_orders','S07');ratio(p+'_return_sales_share',p+'_return_sales',p+'_net','S07')
        checks.append(dict(id='C_customer_'+p+'_sales',op='sum',inputs=[p+'_first_sales',p+'_return_sales'],result_metric=p+'_net',tolerance=1e-7))
        checks.append(dict(id='C_customer_'+p+'_orders',op='sum',inputs=[p+'_first_orders',p+'_return_orders'],result_metric=p+'_orders',tolerance=1e-7))
    cohort=[('jan',1200,108,156,192),('feb',1300,113,163,202),('mar',1500,128,180,225),('apr',1400,108,151,None),('may',1400,98,None,None),('jun',1400,None,None,None)]
    for k,n,d30,d60,d90 in cohort:
        m(k+'_cohort_n',n,'人','S07')
        for day,val in [(30,d30),(60,d60),(90,d90)]:
            m(k+'_rep'+str(day),val,'人','S07','pending' if val is None else 'synthetic')
            if val is None:m(k+'_rate'+str(day),None,'比例','S07','pending')
            else:ratio(k+'_rate'+str(day),k+'_rep'+str(day),k+'_cohort_n','S07')
    c('early_cohort_n','sum',[k+'_cohort_n' for k in ['jan','feb','mar']],'人','S07');c('early_rep30','sum',[k+'_rep30' for k in ['jan','feb','mar']],'人','S07');ratio('early_rate30','early_rep30','early_cohort_n','S07')
    c('recent_cohort_n','sum',[k+'_cohort_n' for k in ['apr','may']],'人','S07');c('recent_rep30','sum',[k+'_rep30' for k in ['apr','may']],'人','S07');ratio('recent_rate30','recent_rep30','recent_cohort_n','S07')
    c('cohort_pp','pp_change',['recent_rate30','early_rate30'],'个百分点','S07')
    # Consent-eligible subscription list and subscription-to-order conversion.
    for p,arr in [('q1',[34000,6000,1200,800,120000]),('q2',[38000,9000,2000,1000,150000])]:
        for k,n in zip(['list_start','signups','unsubs','suppressed','eligible_sessions'],arr):m(p+'_'+k,n,'人' if k!='eligible_sessions' else '次','S08')
        c(p+'_list_out','sum',[p+'_unsubs',p+'_suppressed'],'人','S08');delta(p+'_list_net',p+'_signups',p+'_list_out','S08','人');c(p+'_list_end','sum',[p+'_list_start',p+'_list_net'],'人','S08');ratio(p+'_signup_rate',p+'_signups',p+'_eligible_sessions','S08')
    for k,n,buy in [('apr_sub',3000,300),('may_sub',3200,288),('jun_sub',2800,None)]:
        m(k+'_n',n,'人','S08');m(k+'_buy',buy,'人','S08','pending' if buy is None else 'synthetic')
        if buy is not None:ratio(k+'_rate',k+'_buy',k+'_n','S08')
        else:m(k+'_rate',None,'比例','S08','pending')
    # Email platform internal grouping is exclusive; cross-platform attribution is not additive.
    m('thousand',1000,'倍数','S12')
    for p,arr in [('q1',[1200000,1188000,356400,17820,1050000,138000,210000,90000,1500]),('q2',[1560000,1536600,537810,15366,1380000,156600,224000,120000,1720])]:
        for k,a,u in zip(['sent','delivered','opens','clicks','campaign_del','flow_del','campaign_rev','flow_rev','attributed_orders'],arr,['次','次','次','次','次','次','美元','美元','单']):m(p+'_mail_'+k,a,u,'S09')
        c(p+'_mail_rev','sum',[p+'_mail_campaign_rev',p+'_mail_flow_rev'],'美元','S09')
        for k in ['opens','clicks']:ratio(p+'_mail_'+k+'_rate',p+'_mail_'+k,p+'_mail_delivered','S09')
        for name in ['campaign','flow']:
            ratio(p+'_'+name+'_unit_rev',p+'_mail_'+name+'_rev',p+'_mail_'+name+'_del','S09','美元／次')
            c(p+'_'+name+'_rpm','multiply',[p+'_'+name+'_unit_rev','thousand'],'美元／千次送达','S09')
        ratio(p+'_mail_flow_mix',p+'_mail_flow_rev',p+'_mail_rev','S09')
        ratio(p+'_mail_delivery_rate',p+'_mail_delivered',p+'_mail_sent','S09')
        checks.append(dict(id='C_mail_del_'+p,op='sum',inputs=[p+'_mail_campaign_del',p+'_mail_flow_del'],result_metric=p+'_mail_delivered',tolerance=1e-7))
    flows=[('welcome','欢迎与首购',55000,30000,150),('cart','弃购挽回',50000,52000,260),('post','购后推荐',30000,20000,100),('win','沉默召回',21600,18000,90)]
    for k,label,dd,rr,oo in flows:
        m(k+'_delivered',dd,'次','S09');m(k+'_rev',rr,'美元','S09');m(k+'_mail_orders',oo,'单','S09');ratio(k+'_rev_per',k+'_rev',k+'_delivered','S09','美元／次');c(k+'_rpm','multiply',[k+'_rev_per','thousand'],'美元／千次送达','S09')
    for field,total in [('delivered','q2_mail_flow_del'),('rev','q2_mail_flow_rev')]:checks.append(dict(id='C_flow_'+field,op='sum',inputs=[x[0]+'_'+field for x in flows],result_metric=total,tolerance=1e-7))
    m('post_reached',1200,'人','S09');ratio('post_coverage','post_reached','q2_new_buyers','S09')
    # Fulfilment and bounded support sample.
    for p,arr in [('q1',[6500,6100,2000,10]),('q2',[6800,6100,2700,16])]:
        for k,n,u in zip(['delivery_n','ontime','tickets','first_response'],arr,['单','单','件','小时']):m(p+'_'+k,n,u,'S10')
        ratio(p+'_ontime_rate',p+'_ontime',p+'_delivery_n','S10')
    m('feedback_n',200,'条','S10')
    for k,n in [('fitment',65),('shipping',42),('instructions',31),('packaging',18)]:m(k,n,'条','S10');ratio(k+'_share',k,'feedback_n','S10')
    # Proposed scenario parameters, never forecasts or approved targets.
    for key,x in [('low',.0005),('base',.001),('high',.002)]:
        m(key+'_mobile_lift',x,'比例','S12','estimated')
        c(key+'_new_orders','multiply',['q2_mobile_sessions',key+'_mobile_lift'],'单','S12','estimated')
        c(key+'_net_gain','multiply',[key+'_new_orders','q2_aov'],'美元','S12','estimated')
        c(key+'_contribution_gain','multiply',[key+'_net_gain','q2_pre_marketing_rate'],'美元','S12','estimated')
    # Monthly net revenue supports a six-period chart and reconciles to quarterly totals.
    for k,x in zip(['jan','feb','mar','apr','may','jun'],[360000,390000,450000,440000,470000,530000]):m(k+'_sales',x,'美元','S01')
    for p,months in [('q1',['jan','feb','mar']),('q2',['apr','may','jun'])]:checks.append(dict(id='C_month_'+p,op='sum',inputs=[k+'_sales' for k in months],result_metric=p+'_net',tolerance=1e-7))

    sources=[
      ('S01','订单与统一渠道归属','2025年第二季度、2026年第一至第二季度','净销售额＝折扣前商品金额－折扣－退款；不含税费、运费。按订单所属季度累计至2026年7月7日，本期退款尚可能继续发生。统一渠道类别互斥；平台自报归因另列。按来源分类的收入不是因果增量。','q1_*、q2_*、ly_*；paid_*、organic_*、email_*、direct_*；月度销售'),
      ('S02','会话、设备与顺序转化路径','2026年第一、第二季度','会话口径与订单归属保持一致；示例约定每个成交会话一笔订单。设备×渠道各层加总一致。移动漏斗是同一会话内依次发生的商品浏览、加购、结算、支付，不混用全站独立事件数。','*_sessions、*_cvr、*_funnel_*、*_step、mix_*、within_pp'),
      ('S03','商品成本与经营贡献额','2026年第一、第二季度','经营贡献额＝净销售额－商品成本－履约成本－支付费－广告费－邮件及工具费用。不含人员、固定管理费、税和资本成本，不是净利润。成本为合成口径，真实业务需核对退款成本冲回与成本分摊。','*_cogs、*_fulfill、*_fees、*_ads、*_crm_cost、*_contribution*'),
      ('S04','付费渠道费用与新客','2026年第一、第二季度','搜索／社交收入合计对齐统一付费归属收入；获客成本仅使用本组首次购买客户。广告平台曝光和展示归因未使用；费用比率不等于边际投放回报。','*_search_spend、*_social_spend、*_new、*_cac、*_roas'),
      ('S05','搜索表现及页面检查样本','2026年第一、第二季度；页面检查截至7月7日','搜索曝光与点击来自独立合成口径，不等于网站会话。品牌词按固定词表划分。24个页面为高访问商品页目的性检查，页面性能为同口径移动样本的第75百分位值（各季10,000条合成观测）；未提供实验或逐访客交叉记录。','*_search_impressions、*_search_clicks、*_search_*ctr、audit_*、*_lcp、*_inp'),
      ('S06','商品分类、集中度与库存快照','2026年第一、第二季度；期末库存快照','四个品类互斥、商品成本加总与S03一致；Top20按当季净销售额排序。库存按成本计价，长库龄为超过180天。5个重点SKU无可售库存是快照事实，不能直接换算缺货损失。','*_protection_*、*_storage_*、*_electric_*、*_comfort_*、*_inventory、*_top20_*'),
      ('S07','购买客户及复购队列','2026年1—6月首购客户；观察截至7月7日','新客按首次有效支付去重，期前老客活跃人数与其互斥。首单与非首单订单分组互斥；非首单同时包括当季新客追加购买和期前老客订单，不可当作期前老客收入。30／60／90天复购按首购月队列及完整观察窗计算，未成熟单元为待更新。','*_buyers、*_first_*、*_return_*、*_cohort_n、*_rep*、*_rate30/60/90'),
      ('S08','可触达订阅名单与首购队列','2026年第一、第二季度；观察截至7月7日','有效名单＝期初有效名单＋新增有效订阅－退订－抑制；新增按邮箱去重，名单具有可触达资格。弹窗转化分母为符合展示资格的会话。首购队列只用观察满30天的4—5月订阅者，6月暂不作0。','*_list_*、*_signups、*_unsubs、*_suppressed、*_signup_rate、*_sub_*'),
      ('S09','邮件活动与自动化过程数据','2026年第一、第二季度','成功送达次数是过程分母。点击为单封去重、跨发送可重复的记录次数，非季度独立人数；打开仅为记录打开。平台内部采用固定窗口的最后符合条件邮件归因、分组互斥，但与S01渠道归属不可相加；平台归因不是因果效果。','*_mail_*、*_rpm、welcome_*、cart_*、post_*、win_*'),
      ('S10','履约、客服与多主题反馈','2026年第一、第二季度；反馈样本n＝200','准时交付分母仅为本期已签收且有承诺日期的订单，未签收订单不纳入。响应时长为工单中位数。200条客服反馈允许多主题编码，无真实引语，不能代表所有购买者或全部退货原因。','*_delivery_n、*_ontime*、*_tickets、*_first_response、feedback_n、fitment等'),
      ('S11','测量覆盖与治理检查清单','基于本示例的可用字段范围','跨来源订单／会话定义可对齐；广告和邮件平台归因不能叠加；缺少逐访客因果识别、长期价值与完整组织成本。覆盖台账保留缺失／部分覆盖，不把未提供的证据解释为不存在问题。','coverage；D19及管理总览范围说明'),
      ('S12','目标、情景参数及建议行动','示例第二季度目标；建议90天推进窗口','150万美元为合成目标；行动角色、时间、分阶段门槛均是待批准建议。移动情景只覆盖17.5万次移动会话，其余条件不变；按当前净客单价和广告前单位贡献率估算，未扣新增实施成本，不是净利润或预测，情景不相加。','*_target、low_*、base_*、high_*；actions、composition'),
      ('S13','外部市场及竞争证据缺口','本示例未配置外部市场样本','没有可比较的市场规模、竞争者流量、价格篮子、交付承诺或品牌调查；会员与推荐机制也未配置参与和成本记录。只能讨论自身搜索与内容表现，不形成市场份额、行业排名或竞争优势判断。补证方案与原有经营任务分别记录。','coverage中的市场、品牌、竞争与长期价值限制')]
    SS=[dict(id=k,title=t,period=p,locator='comprehensive-report.json · '+loc,note=n) for k,t,p,n,loc in sources]
    def chart(typ,title,unit,rows,scale=1,decimals=1,period='2026年第一季度与第二季度',**kw):
        mids=[]
        for rr in rows:
            mids.extend([rr[x] for x in ['metric_id','before','after'] if x in rr])
        return dict(type=typ,title=title,unit=unit,period=period,alt=title+'；对应数值见可展开数据表。',source_ids=list(dict.fromkeys(M[x]['source_id'] for x in mids)),scale=scale,decimals=decimals,rows=rows,**kw)
    def sec(i,eyebrow,title,paras,src,meaning,limit,headers=None,rows=None,ch=None,claim='interpretation'):
        item=dict(id=i,eyebrow=eyebrow,headline=title,paragraphs=paras,source_ids=src,claim_type=claim,implication=meaning,limitation=limit)
        if headers is not None:item['table']=dict(headers=headers,rows=rows)
        if ch:item['chart']=ch
        sections.append(item);return i
    def pg(i,kind,chapter,label,**kw):pages.append(dict(id=i,kind=kind,chapter=chapter,label=label,**kw))
    def content(i,chapter,label):pg('P_'+i,'content',chapter,label,section_ids=[i])
    # Formal front matter precedes the management overview.
    pg('P_cover','cover','前置页','报告封面')
    pg('P_toc','toc','前置页','目录与阅读路径')
    pg('P_summary','summary','管理层总览','总体判断')
    # 3-4: a full quantitative view, not a 3-card replacement for the report.
    sec('O01','管理总览 1／8 · 经营结果','收入增长20%，经营贡献额反而下降11.5%',[
        '第二季度净销售额达到144万美元，完成示例目标的96.0%；同比增长33.3%、环比增长20.0%。收入规模继续扩大，但增长没有同比例转化为可覆盖固定费用的经营贡献。',
        '经营贡献额从31.2万美元降至27.6万美元，贡献率由26.0%降至19.2%。需要同时审视商品成本、履约费用、折扣和投放，不宜只按销售额完成率评价经营质量。'],['S01','S02','S03','S12'],
        '把销售额、经营贡献额与贡献率并列管理；先处理利润侵蚀与核心转化问题，再决定增投。相关证据见D01—D05。',
        '贡献额尚未扣人员与固定管理费用；退款截至日后的变动仍可能影响净额。示例目标不是实际企业预算。',
        ['核心指标','第一季度','第二季度','变化／解释'],[
        ['净销售额（万美元）',cash('q1_net'),cash('q2_net'),'环比+20.0%；同比+33.3%'],
        ['目标完成率',pct('q1_achievement'),pct('q2_achievement'),'本期差6.0万美元'],
        ['有效支付订单（单）',cell('q1_orders'),cell('q2_orders'),'增加400单（+5.9%）'],
        ['净客单价（美元／单）',cell('q1_aov',1,2),cell('q2_aov',1,2),'增加23.53美元（+13.3%）'],
        ['会话数（万次）',cell('q1_sessions',10000,1),cell('q2_sessions',10000,1),'增加5.0万次（+25.0%）'],
        ['全站转化率',pct('q1_cvr',2),pct('q2_cvr',2),'下降0.52个百分点'],
        ['商品毛利率',pct('q1_gross_margin'),pct('q2_gross_margin'),'下降4.0个百分点'],
        ['经营贡献额（万美元）',cash('q1_contribution'),cash('q2_contribution'),'减少3.6万美元（−11.5%）'],
        ['经营贡献率',pct('q1_contribution_rate'),pct('q2_contribution_rate'),'下降6.8个百分点']])
    content('O01','管理层总览','关键数据：结果与经营贡献')
    sec('O02','管理总览 2／8 · 过程与效率','转化、获客成本、邮件效率与交付出现不同程度回落',[
        '增长过程并非全面恶化：有效订阅名单净增和自动化归因收入占比均提高。但移动端转化、付费新客成本、主动邮件的单位送达价值及准时交付率出现需要解释的变化。',
        '下表保留正向、负向与待验证指标，避免只挑选符合“增长承压”叙事的数据。复购采用已成熟队列，与季度汇总的时间口径不同。'],['S02','S04','S07','S08','S09','S10'],
        '先锁定可控环节及验证成本；不要把全部过程指标下降归为同一个根因。相关证据见D07—D18。',
        '复购基准为1—3月首购队列，本期比较组为4—5月；邮件归因、样本与履约分母各有边界，详见对应章节。',
        ['过程指标','基准值','本期／比较值','管理含义'],[
        ['移动端转化率',pct('q1_mobile_cvr',2),pct('q2_mobile_cvr',2),'下降0.60个百分点'],
        ['付费新客成本（美元／人）',cell('q1_paid_cac',1,2),cell('q2_paid_cac',1,2),'上升24.0%，见D05'],
        ['首次购买客户（人）',cell('q1_new_buyers'),cell('q2_new_buyers'),'增长5.0%，低于流量增速'],
        ['新客30天复购率',pct('early_rate30',2),pct('recent_rate30',2),'仅比较满30天队列'],
        ['有效名单净增（人）',cell('q1_list_net'),cell('q2_list_net'),'增长50.0%，需检验后续价值'],
        ['主动邮件每千次送达收入（美元）',cell('q1_campaign_rpm',1,2),cell('q2_campaign_rpm',1,2),'200.00→162.32'],
        ['自动化占邮件平台收入',pct('q1_mail_flow_mix'),pct('q2_mail_flow_mix'),'30.0%→34.9%'],
        ['准时交付率',pct('q1_ontime_rate'),pct('q2_ontime_rate'),'93.8%→89.7%']])
    content('O02','管理层总览','关键数据：增长过程与效率')
    # Insight register: 12 independent findings, not capped by the three top messages.
    insight_rows1=[
      ['F01','规模增长没有带来贡献额增长','净销售额+20.0%，经营贡献额−11.5%','将贡献额作为增投门槛','D01 / D03；A05 / A12'],
      ['F02','付费渠道扩张伴随新客成本上行','账面增量占75.0%；新客成本90.00→111.63美元','先核对边际效果，不平均加预算','D04 / D05；A04'],
      ['F03','移动端下降不只来自渠道占比改变','四类渠道内的移动转化率均下降','继续定位商品、用户与路径差异','D07；A02'],
      ['F04','移动加购环节的阶段转化变弱','商品浏览→加购17.8%→14.3%；结算→支付仍60.0%','优先查商品决策障碍，而非先改支付','D08 / D09；A02'],
      ['F05','客单价上升与折扣侵蚀并存','折前单均金额上升；折扣率10.0%→15.0%','按商品贡献审核优惠结构','D11；A05'],
      ['F06','主力缺货与长尾积压同时存在','销售前20个商品规格（SKU）贡献65.0%；其中5个无可售库存；长库龄占30.0%','按SKU调配，不做全站统一清仓','D10 / D12；A03']]
    insight_rows2=[
      ['F07','新客规模增长，但短期复购走弱','成熟队列30天复购8.73%→7.36%','检验首单人群与第二单适配','D13 / D14；A08'],
      ['F08','订阅量改善，尚未证明购买价值提高','净增名单4,000→6,000；4—5月订阅首购588／6,200','把订阅后首购与留存纳入验收','D15；A07'],
      ['F09','主动邮件送达增长快于归因收入','成功送达增加31.4%，归因收入仅增6.7%','验证名单分层、选品与频次','D16；A09'],
      ['F10','自动化表现较好，但购后触达覆盖有限','平台自动化收入+33.3%；购后覆盖1,200／4,200人','优先补齐购后试点而非全量加频','D17；A08'],
      ['F11','交付与商品说明是独立体验问题','准时率89.7%；适配反馈65／200条','拆开履约动作与内容纠错','D09 / D18；A10'],
      ['F12','外部竞争与因果收益仍缺证据','无可比市场样本；缺实验与长期价值数据','补证后才做定位和收益承诺','D06 / D19；A01 / A06 / A11']]
    for i,rr,title in [('O03',insight_rows1,'六项发现解释增长规模与经营质量的分化'),('O04',insight_rows2,'六项发现连接客户价值、邮件经营与验证边界')]:
        sec(i,'管理总览 · 12项核心发现',title,['核心发现按影响与决策关联整理，而不是每个指标单独占一条。F编号在总览中用于快速定位；D编号指向完成论证的诊断章节，A编号指向完整行动卡。','事实和计算已由合成明细支撑；“应优先做什么”属于基于证据的建议，不意味着原因已经确定。'],['S01','S02','S03','S04','S05','S06','S07','S08','S09','S10','S11','S13'],
            '只看本页即可获得主题、证据与管理含义；执行前仍需进入对应诊断页确认口径和限制。','频率不是收益，渠道归属不是因果；未提供资料的领域保留缺口，不按低表现评分。',
            ['编号','核心发现','关键证据','决策含义','正文／行动'],rr)
        content(i,'管理层总览','核心发现总览'+('（上）' if i=='O03' else '（下）'))
    sec('O05','管理总览 5／8 · 策略与待决事项','先修复可控问题，再通过验证决定资源增配',[
        '建议维持基础经营节奏，优先保护主力商品可售性、折扣后的贡献额与核心购买路径；对追加广告和全量发送保持条件式审批。这里的“先”是建议的依赖顺序，不是已生效的预算冻结。',
        '四项策略覆盖现有发现，但不把每一项都包装为新增项目。需要批准的是范围、协作资源和验收机制，具体负责人和数值门槛在启动会上确认。'],['S01','S02','S03','S06','S07','S09','S12'],
        '优先批准数据核对、跨职能协调和小范围试点；对大规模加投、全站折扣和无法计量的改造暂不作收益承诺。',
        '用户运营、商品、供应链、投放和研发并不由同一岗位天然控制；责任边界必须显式协调。',
        ['策略方向','需要作出的决定','建议顺序','关联行动'],[
        ['守住经营贡献','确认贡献口径与折扣审批边界；避免以销售额单独验收','先核对，再调整','A01 / A05 / A12'],
        ['修复购买路径与供给','批准移动问题定位及重点SKU可售性核对','主力商品与高访问路径优先','A02 / A03 / A10'],
        ['提升客户与邮件价值','批准订阅首购、购后与主动邮件的分层试点','共享分组和测量，避免重复触达','A07 / A08 / A09'],
        ['有条件扩大有效增长','补充搜索需求与竞争证据；按实测边际贡献分配投放','验证后再扩大','A04 / A06 / A11']])
    content('O05','管理层总览','策略与需要管理层确认的事项')
    # Action definitions are used for both overview and detail pages.
    action_data=[
      ('A01','统一订单、渠道与贡献额口径','先澄清分母和可叠加范围，形成所有决策共同基线。','建议数据负责人牵头，财务复核','建议第1—2周','交付指标字典、三类来源对账表、差异清单；每项差异有解释与影响范围','影响主判断的差异未解释，不进入增量收益审批','订单、会话、商品成本、费用和平台归因字段',['D01','D03','D19'],'P0','指标字典与对账结果'),
      ('A02','定位移动端损失并提出单变量试点','四渠道内转化均下降，且商品浏览到加购变弱；先核对而非直接大改版。','建议站点负责人牵头，研发与数据协作','建议第1—3周','按渠道×商品×新老客核对阶段转化；交付一个可证伪的问题及试点方案','无法定位稳定异常或测量失效，先修测量；不把未验证页面假设全量上线','稳定事件定义、会话级路径、库存与价格记录',['D07','D08','D09'],'P0','问题定位与受控试点方案'),
      ('A03','处理主力缺货并分层处置长库龄库存','重点SKU无可售库存与长尾积压并存，统一清仓会混淆供给和周转问题。','建议商品与供应链负责人联合负责','建议第1—2周完成清单','逐项确认5个重点SKU补货／替代／暂停投放；分层列出180天以上库存的处置条件','补货周期和贡献测算不明时，不承诺到货；不对全站统一降价','可售库存、在途量、补货周期、逐SKU毛利与退货成本',['D10','D12'],'P0','重点SKU与长库龄分层清单'),
      ('A04','分开验证搜索与社交投放的边际价值','社交新客成本涨幅更大，但平均费用指标无法证明新增预算是否划算。','建议投放负责人负责，数据与财务参与','建议第3—6周','锁定可比新客和观察窗，形成分组或地域对照的预算试点及回收报告','贡献额或关键护栏恶化时停止扩量；门槛须试验前约定','A01；可隔离预算、可用样本、适用隐私边界',['D04','D05'],'P1','分渠道预算试点与复核'),
      ('A05','建立折扣与品类贡献审核','净客单价上升与折扣率提高同时存在，不能只按客单价认定促销有效。','建议商品负责人牵头，财务与运营会签','建议第1—3周','交付品类／重点SKU折扣后贡献表、现行优惠叠加规则及例外审批要求','未完成成本核对的商品不承诺可持续折扣；不将商品毛利当净利润','A01；商品成本、退款、履约及优惠组合',['D03','D10','D11'],'P0','折扣审核表与例外流程'),
      ('A06','建立非品牌搜索需求与竞争证据清单','自身曝光增长不等于需求池已开发；缺少可比较竞争样本。','建议内容／搜索负责人负责，商品团队参与','建议第2—4周','按需求词、落地页和商品对应关系整理机会；补齐同口径竞争样本、获取日期与适用边界','没有可验证需求和可售商品时不批量生产内容；外部数据缺失继续标记','搜索词与页面数据、可售SKU、获准使用的外部资料',['D06','D09'],'P1','需求—内容—商品证据地图'),
      ('A07','验证订阅到首购的完整路径','有效名单净增提高，但不能用订阅量替代购买质量。','建议订阅增长负责人负责，邮件负责人协作','建议第3—6周','建立按来源和首订月份的30天首购、退订及贡献表；测试一种触达或权益变化','退订、投诉或贡献护栏恶化不扩大；优惠资格与去重规则必须先核对','A01；订阅资格、来源标签、订单关联与可比较样本',['D15','D16'],'P1','订阅首购分组试点'),
      ('A08','补齐首单到第二单的购后试点','购后覆盖只有28.6%；短期复购变化需结合首购物品、使用周期和后续需求。','建议用户运营与邮件负责人联合负责','建议第3—8周','按首购品类设计内容／关联推荐／复购路径；保留对照，跟踪成熟队列第二单与贡献额','不在收到结果前承诺复购提升；退款或退订护栏恶化则缩小范围','A01；商品适配信息、签收事件、可售关联商品',['D13','D14','D17'],'P1','购后路径与成熟队列回收'),
      ('A09','以单位送达价值复核主动邮件频次','发送扩张与点击率回落同步，需区分名单、选品、活动构成和频次。','建议邮件负责人负责','建议第2—6周','按来源、活跃度和购买阶段分组；比较每千次送达贡献、点击与退订，记录触达排重','同一用户不同时进入互相干扰的频次试验；仅归因收入改善不足以判定扩大','A01；送达、点击、退订与统一订单关联',['D16','D17'],'P1','分层频次与选品试点'),
      ('A10','修正交付承诺与适配说明的高频缺口','准时率下降、适配反馈集中，但它们需要不同责任主体处理。','建议履约负责人和站点内容负责人分工','建议第1—4周','逐项核实承诺日期、延迟告知与重点页面说明；记录修正前后问题类型和退货护栏','不可兑现的时效不继续展示；少量客服样本不外推为总体问题率','物流签收、页面承诺、24页审查清单与反馈编码',['D09','D18'],'P1','承诺与页面说明纠错清单'),
      ('A11','按覆盖人群和真实效果测算试点收益','多个动作覆盖同一批访客，情景之和会高估总体收益。','建议数据负责人设计，业务与财务共同验收','建议第2周定口径，第6—10周回收','预先定义主指标、分配单元、最小有意义效应和护栏；计算去重后的收益范围','样本或观测窗不够时报告不确定；不以不显著判定无效果，不重复加总收益','A01；可控发布范围、测量稳定性和样本量评估',['D07','D14','D19','T02'],'P1','试验协议与去重收益模型'),
      ('A12','建立跨职能周复核与阶段决策','问题同时涉及投放、商品、研发与履约，用户运营不能独立承担全部结果。','建议经营负责人主持，各模块负责人参加','建议每周复核；第4、8、12周决策','使用同一行动编号追踪输出、指标、依赖与异常；留下继续／调整／停止的决策记录','责任与资源未明确的项目不列为已承诺；超出试点范围须重新审批','A01；经营与各职能共同确认资源和决策权限',['D03','D12','D19','T01','T03'],'P0','周复核与阶段决策台账')]
    for a_id,title,rat,owner,timing,success,gate,deps,rels,priority,deliverable in action_data:
        actions.append(dict(id=a_id,title=title,rationale=rat,owner=owner,timing=timing,success=success,gate=gate,dependencies=deps,related_sections=rels,status='proposed'))
    for oid,subset,title in [('O06',action_data[:6],'先列出基础治理与增长效率的六项待办'),('O07',action_data[6:],'客户经营与协同机制的六项待办继续前置')]:
        rr=[[a[0]+'／'+a[-2],a[1],a[-1],a[4],a[8][0]] for a in subset]
        sec(oid,'管理总览 · 12项待办总账',title,[
            '总览保留全部12项优先待办，不只列三条口号。这里只呈现动作、交付物、建议顺序与证据入口；完整角色、验收指标、依赖和停止条件在第36—39页展开。',
            'P0表示建议先建立基础或控制风险；P1表示依赖条件满足后验证。排序不是工作量承诺，也不意味着所有项目同时启动。'],['S11','S12'],
            '先确认可投入资源，再按依赖分批执行；每项任务只保留一个编号，避免摘要和正文形成两套清单。',
            '周期与角色均为建议，非真实组织安排。未核实的阈值在启动前确认，不填入任意增长目标。',
            ['编号／优先级','行动事项','具体交付','建议时间','证据入口'],rr)
        content(oid,'管理层总览','优先待办总账'+('（上）' if oid=='O06' else '（下）'))
    coverage=[
      ('经营规模与目标','covered',['D01','D02'],'统一口径、同比环比与算术分解',['A01','A12']),
      ('经营贡献与费用','partial',['D03'],'已到经营贡献额；缺固定费用，不能判断净利润',['A01','A05']),
      ('付费与自然获客','covered',['D04','D05','D06'],'渠道记录与费用可核对；因果回报另行验证',['A04','A06']),
      ('品牌与竞争格局','partial',['D06'],'只有自身品牌词；市场规模与竞争样本缺失',['A06']),
      ('站内转化与页面','partial',['D07','D08','D09'],'定位变化与样本缺陷，未识别单一根因',['A02','A10']),
      ('商品、折扣与库存','covered',['D10','D11','D12'],'品类成本、净额与库存快照可核对',['A03','A05']),
      ('新老客户与短期复购','covered',['D13','D14'],'分母明确；未成熟窗口排除',['A08']),
      ('订阅与首购','partial',['D15'],'有名单与成熟队列；缺长期价值及来源交叉',['A07']),
      ('邮件活动与自动化','covered',['D16','D17'],'量、率、平台收入与购后覆盖分别呈现',['A08','A09']),
      ('履约、客服与用户反馈','partial',['D18'],'签收样本与200条反馈，不代表总体因果',['A10']),
      ('测量与数据质量','covered',['D19'],'口径、缺口及影响范围明确登记',['A01','A11']),
      ('长期客户价值','missing',[],'未配置完整长期队列与贡献成本；不推算终身价值',['A01','A11']),
      ('会员与推荐机制','missing',[],'未配置权益参与、推荐及成本记录，暂不判断新增机制价值',['A01'])]
    cover_objects=[dict(domain=d,status=st,section_ids=si,explanation=e,action_ids=aa) for d,st,si,e,aa in coverage]
    status_name={'covered':'已覆盖','partial':'部分覆盖','missing':'资料缺失','not_applicable':'不适用'}
    sec('O08','管理总览 8／8 · 范围与缺口','13个诊断模块均有交代，缺资料不等于无问题',[
        '“全面”指对承诺范围逐项回答、限定或说明缺口，不是把所有数据都写进正文。外部竞争、长期客户价值和根因识别不足的部分留在覆盖台账，不静默删除。'],['S11','S13'],
        '执行中优先补齐会改变资源决策的缺口；不把研究缺口全部升格为P0，也不在补证之前声称已完成完整商业审计。',
        '“已覆盖”只表示示例已完成所需描述与分析，不代表已经证明因果或通过真实数据审计。',
        ['诊断模块','覆盖状态','正文位置','主要边界'],[[d,status_name[st],' / '.join(si) if si else '补证：'+' / '.join(aa),e] for d,st,si,e,aa in coverage])
    content('O08','管理层总览','诊断范围与未决证据')
    # Detailed business chapters, pages 11-29.
    sec('D01','01｜经营结果与增长质量','本期增长以月度扩张延续，但离目标仍差6万美元',[
        '第二季度净销售额同比增长33.3%，说明增长并非只来自与较低的第一季度比较；但单一同比不足以排除季节性和品类变化。按现有目标仍差6万美元，不能将96.0%的完成率写为“达标”。',
        '六个月销售从36万、39万、45万美元，变化为44万、47万和53万美元。第二季度的增长主要体现在后两个月；需在复盘中继续核对活动、供给与价格变化，不能只由折线猜测原因。'],['S01','S02','S12'],
        'A12复核规模和贡献的同步变化；本节只回答达成情况，是否健康需结合D03。',
        '目标为合成目标；仅含六个月趋势，不能据此估计全年季节曲线。退款观察截至日可能影响后续净额。',
        ['比较期间','净销售额（万美元）','订单（单）','会话（万次）','转化率'],[
        ['2025年第二季度',cash('ly_net'),cell('ly_orders'),cell('ly_sessions',10000,1),pct('ly_cvr',2)],
        ['2026年第一季度',cash('q1_net'),cell('q1_orders'),cell('q1_sessions',10000,1),pct('q1_cvr',2)],
        ['2026年第二季度',cash('q2_net'),cell('q2_orders'),cell('q2_sessions',10000,1),pct('q2_cvr',2)]],
        chart('line','图1｜月度净销售额','万美元',[dict(label=l,metric_id=k+'_sales') for k,l in [('jan','1月'),('feb','2月'),('mar','3月'),('apr','4月'),('may','5月'),('jun','6月')]],10000,0,'2026年1—6月'))
    content('D01','01｜经营结果与增长质量','规模、目标与同比环比')
    sec('D02','01｜经营结果与增长质量','流量增加带来的算术增量，被转化下降部分抵消',[
        '采用“先流量、再转化、最后客单价”的顺序替换：流量从20万增至25万次，对应增加30万美元；转化率从3.40%降至2.88%，抵消约22.94万美元；客单价上升再增加约16.94万美元。',
        '三项变化合计24万美元，与实际净销售额增量相等。这说明哪项指标在指定拆分中贡献多少，不表示如果只改转化就一定获得相同增量。'],['S01','S02'],
        'A02优先定位转化变化，A05核对客单价与优惠结构；机会测算必须另设可实现幅度和覆盖范围。',
        '顺序改变会改变分项归属；本例交互项按指定替换顺序分配，不重复计入，不作为因果模型。',
        ['分解步骤','对应销售额（万美元）','相对前一步变化（万美元）'],[
        ['第一季度基线',cash('q1_net'),'—'],['只替换会话数',cash('sales_at_traffic'),cash('traffic_bridge')],['再替换转化率',cash('sales_at_cvr'),cash('cvr_bridge')],['最后替换净客单价',cash('q2_net'),cash('aov_bridge')]],
        chart('waterfall','图2｜按指定顺序的收入变化分解','万美元',[dict(label='一季度',metric_id='q1_net',role='start'),dict(label='流量',metric_id='traffic_bridge',role='delta'),dict(label='转化率',metric_id='cvr_bridge',role='delta'),dict(label='客单价',metric_id='aov_bridge',role='delta'),dict(label='二季度',metric_id='q2_net',role='total')],10000,1),claim='calculation')
    content('D02','01｜经营结果与增长质量','规模增长的算术分解')
    sec('D03','01｜经营结果与增长质量','新增24万美元销售，未覆盖新增27.6万美元经营成本',[
        '销售增加24万美元，但列示成本增加27.6万美元，经营贡献额净减少3.6万美元。商品成本增加16.8万美元是金额最大的扣减项；广告费用增加6万美元，履约费用增加3.36万美元。',
        '这张桥图用于对账，不把成本变化解释成“浪费”。商品组合、运费、退款和供给策略仍需进一步拆解，后续策略应避免只压缩某项费用而损害交付或销售。'],['S01','S03'],
        'A05先核对折扣后品类贡献，A12建立联合损益复核；预算讨论至少同时看净销售额和贡献额。',
        '这里不是净利润。退款、成本冲回和归属周期需保持一致；真实组织还应加入人员及固定成本后再判断盈利。',
        ['项目','第一季度（万美元）','第二季度（万美元）','解释'],[
        ['商品毛利',cash('q1_gross_profit'),cash('q2_gross_profit'),'毛利额增加，毛利率下降'],['履约成本',cash('q1_fulfill'),cash('q2_fulfill'),'增长快于销售'],['广告费用',cash('q1_ads'),cash('q2_ads'),'增加6.0万美元'],['经营贡献额',cash('q1_contribution'),cash('q2_contribution'),'减少3.6万美元']],
        chart('waterfall','图3｜经营贡献额变动桥','万美元',[dict(label='一季度',metric_id='q1_contribution',role='start'),dict(label='净销售',metric_id='net_delta',role='delta')]+[dict(label=l,metric_id=k+'_bridge',role='delta') for k,l in [('cogs','商品成本'),('fulfill','履约'),('fees','支付费'),('ads','广告'),('crm_cost','工具')]]+[dict(label='二季度',metric_id='q2_contribution',role='total')],10000,1),claim='calculation')
    content('D03','01｜经营结果与增长质量','经营贡献与费用桥')
    sec('D04','02｜获客、搜索与外部边界','付费渠道占本期销售54.2%，贡献账面增量75.0%',[
        '付费渠道净销售额从60万增至78万美元，增加18万美元；自然搜索、邮件和直接及其他分别增加3万、1万和2万美元。增量集中在付费渠道，但其他渠道仍在增长。',
        '统一口径下，付费会话增长40.0%、订单仅增长10.0%，其转化率从3.00%降至2.36%。先解释扩量后的客户和商品结构，再评估是否持续扩量。'],['S01','S02'],
        'A04使用分渠道边际验证，而不是因“增量贡献最大”就增加相同比例预算；自然与邮件不能凭较低份额认定无机会。',
        '账面归属不等于新增效果，渠道转化差异也受人群意图影响；本表不能直接用作公平渠道排名。',
        ['渠道','本期净额（万美元）','本期会话（万次）','本期转化率','占账面增量'],[[label,cash(k+'_q2_sales'),cell(k+'_q2_sessions',10000,1),pct(k+'_q2_cvr',2),pct(k+'_increment_share')] for k,label,*_ in channels],
        chart('hbar','图4｜分渠道净销售额增量','万美元',[dict(label=label,metric_id=k+'_delta') for k,label,*_ in channels],10000,1))
    content('D04','02｜获客、搜索与外部边界','渠道结构与转化效率')
    sec('D05','02｜获客、搜索与外部边界','社交新客成本升至123.53美元，涨幅高于搜索',[
        '付费新客由2,000人增至2,150人，增长7.5%；广告费用由18万增至24万美元，增长33.3%。因此本组平均获客成本由90.00美元升至111.63美元。',
        '搜索新客成本从91.67美元升至103.85美元；社交从87.50美元升至123.53美元。社交扩张更快，但无法仅凭季度均值确认创意疲劳、受众饱和或平台涨价。'],['S03','S04'],
        'A04优先拆解社交的新增人群、素材、商品和预算段；以可对照的贡献结果决定保留、调整或缩小。',
        '搜索可能承接品牌和其他渠道创造的需求；平台均值不直接代表边际回报，也不能将预算一律转向搜索。',
        ['渠道','基准费用／本期费用（万美元）','基准新客／本期新客','本期费用回收比','待验证问题'],[
        ['付费搜索','11.0／13.5','1,200／1,300',cell('q2_search_roas',1,2,'倍'),'品牌词占比及新增需求'],['付费社交','7.0／10.5','800／850',cell('q2_social_roas',1,2,'倍'),'增量人群与商品组合']],
        chart('dumbbell','图5｜首次购买客户的平均广告成本','美元／人',[dict(label='付费搜索',before='q1_search_cac',after='q2_search_cac'),dict(label='付费社交',before='q1_social_cac',after='q2_social_cac'),dict(label='付费合计',before='q1_paid_cac',after='q2_paid_cac')],1,1,series_labels=['第一季度','第二季度'],y_min=0,y_max=150))
    content('D05','02｜获客、搜索与外部边界','付费预算与新客成本')
    sec('D06','02｜获客、搜索与外部边界','非品牌曝光增长，尚未转化为相同比例点击',[
        '搜索曝光由800万增至900万次，点击由9万增至9.6万次。品牌词点击由3.5万增至4万次；非品牌点击仅由5.5万增至5.6万次，尽管相应曝光由600万增至680万次。',
        '非品牌词的点击率由0.92%降至0.82%，可能包含词群、排名和页面差异。自身数据只支持需求覆盖和内容匹配诊断，不能证明品牌竞争力弱、市场份额下降或市场规模不足。'],['S01','S05','S13'],
        'A06按需求词—页面—商品核对点击缺口，补充有日期、同口径的竞争样本后，再讨论内容投入与品牌定位。',
        '未提供市场规模、竞争者流量、价格篮子或品牌调查。搜索点击不等于会话，品牌词分类也不等于品牌认知度。',
        ['证据层','现有观察','能回答什么','不能回答什么'],[
        ['自身品牌词','曝光200万→220万；点击3.5万→4万','品牌相关搜索表现','品牌知名度／市场份额'],['非品牌词','曝光600万→680万；点击5.5万→5.6万','点击覆盖与页面匹配线索','机会的最终销售额'],['自然搜索归属','净销售30万→33万美元','本店自然渠道收入变化','对竞争者的相对领先'],['市场与竞争','未提供可比较样本','明确补证问题与范围','市场规模、排名或壁垒'],['建议补证','统一地区、品类、时点与价格条件','形成可比较的需求与方案','用搜索估算值冒充精确财务数据']])
    content('D06','02｜获客、搜索与外部边界','自然搜索、品牌与竞争缺口')
    sec('D07','03｜站内转化与购买体验','四类渠道内的移动转化率均下降，不能只归为流量结构',[
        '移动会话占比从60.0%升至70.0%。先替换设备占比、后替换设备内转化率，结构变化解释全站下降0.10个百分点，组内变化解释下降0.42个百分点，合计下降0.52个百分点。',
        '进一步看渠道内的移动端，四组转化率均下降。这排除了“只因渠道占比变化”的单一解释，但还未排除各渠道内部商品、地区、首访比例和库存差异。'],['S01','S02'],
        'A02继续按商品、新老客与可售状态交叉核对；不能把剩余组内变化全部写成页面性能导致。',
        '算术分解按明确顺序计算；细分会话质量未充分匹配，不支持因果结论。',
        ['移动端渠道','基准会话／订单','本期会话／订单','基准转化率','本期转化率'],[[label,f'{v("q1_mobile_"+k+"_sessions"):,}／{v("q1_mobile_"+k+"_orders"):,}',f'{v("q2_mobile_"+k+"_sessions"):,}／{v("q2_mobile_"+k+"_orders"):,}',pct('q1_mobile_'+k+'_cvr',2),pct('q2_mobile_'+k+'_cvr',2)] for k,label,*_ in channels],
        chart('dumbbell','图6｜同一渠道内的移动端转化率','%',[dict(label=label,before='q1_mobile_'+k+'_cvr',after='q2_mobile_'+k+'_cvr') for k,label,*_ in channels],.01,2,series_labels=['第一季度','第二季度'],y_min=0,y_max=6))
    content('D07','03｜站内转化与购买体验','设备与渠道交叉核对')
    sec('D08','03｜站内转化与购买体验','移动端损失更早出现，支付阶段不是唯一优先项',[
        '移动会话增长45.8%，商品浏览增长36.1%，加购仅增长9.4%。商品浏览到加购率从17.8%降至14.3%；访问到商品浏览的比例也从75.0%降至70.0%。',
        '结算到支付保持60.0%，加购到结算则从37.5%升至40.0%。如果直接以全站转化下降为由优先改支付，就会忽视更早发生的商品选择与购买决策问题。'],['S02'],
        'A02先检查进入商品页之前的意图匹配、商品可售与购买说明；支付仍需监测，但不是现有证据唯一指向。',
        '漏斗为相同会话的顺序路径；重访与跨设备购买未纳入，不能把阶段流失人数直接当可挽回订单。',
        ['移动端步骤','第一季度（次）','第二季度（次）','基准阶段转化','本期阶段转化'],[[label,cell('q1_funnel_'+key),cell('q2_funnel_'+key),'—' if key=='visit' else pct('q1_'+key+'_step'),'—' if key=='visit' else pct('q2_'+key+'_step')] for key,label in [('visit','访问'),('pdp','商品浏览'),('cart','加购'),('checkout','开始结算'),('paid','支付')]],
        chart('hbar','图7｜移动端顺序路径的会话规模','万次',[dict(label=label,metric_id='q2_funnel_'+key) for key,label in [('visit','访问'),('pdp','商品浏览'),('cart','加购'),('checkout','开始结算'),('paid','支付')]],10000,2,'2026年第二季度'))
    content('D08','03｜站内转化与购买体验','购买漏斗与损失位置')
    pg('P_visual_flow','visual','03｜站内转化与购买体验','购买路径示意',visual_kind='process',visual_title='从访问到支付：先定位掉队环节',visual_note='基于合成的移动端顺序会话口径绘制；箭头只表示路径顺序，不表示阶段流失可全部挽回。具体人数与比率见D08。',evidence_source_id='S02',steps=['访问 17.5万次','商品浏览 12.25万次','加购 1.75万次','开始结算 7,000次','完成支付 4,200单'],readouts=[dict(value='70.0%',label='商品浏览 / 访问：12.25万 / 17.5万次'),dict(value='14.3%',label='加购 / 商品浏览：1.75万 / 12.25万次'),dict(value='40.0%',label='结算 / 加购：7,000 / 1.75万次'),dict(value='60.0%',label='支付 / 结算：4,200 / 7,000次')],readout_summary='商品浏览后的加购率由基准的17.8%降至14.3%，是优先核查的环节；阶段比率本身不能证明原因。')
    sec('D09','03｜站内转化与购买体验','页面审查发现具体缺口，但尚未验证转化影响',[
        '高访问的24个商品页检查中，9页适配说明不完整、7页安装说明不完整、10页交付说明存在缺口，8页有待压缩或延后加载的重媒体。一个页面可能同时存在多个问题。',
        '移动端观测的主要内容显示耗时从3.8秒升至4.6秒、交互延迟从260毫秒升至340毫秒。性能与转化同时变差提供核查线索，不能据此认定性能解释了全部转化降幅。'],['S05','S10'],
        'A10可先修正已核实的说明错误；A02把需要产品改造的部分转为可对照的小范围试验，分别评估信息、性能与商品因素。',
        '目的性页面样本不能外推全站缺陷率；性能观测缺少同一访客级实验对照。本节没有宣称达到或未达到某外部技术标准。',
        ['审查主题','缺口页数／样本','可先采取的动作','效果验证'],[
        ['适配条件','9／24','核对车型、限制条件与变体提示','适配查询后的加购及退货护栏'],['安装说明','7／24','补齐缺失步骤、材料与工具信息','说明访问到购买路径'],['交付承诺','10／24','核对库存、发货和到货文案','咨询、取消及准时率'],['重媒体','8／24','定位资源与设备差异','性能改善与转化对照'],['站内搜索','未提供查询明细','补齐无结果词、改写与商品关联','不直接认定搜索引擎能力不足']])
    content('D09','03｜站内转化与购买体验','商品决策信息、搜索与性能')
    pg('P_visual_ui','visual','03｜站内转化与购买体验','合成商品页示意',visual_kind='synthetic_ui',visual_title='把适配、安装和交付信息放在决策位置',visual_note='合成界面示意，非店铺截图；仅演示如何标注问题位置。24页定向审查的9／24、7／24和10／24分别见D09，不能外推全站。',evidence_source_id='S05',readouts=[dict(value='9 / 24',label='适配说明不完整，定向审查样本'),dict(value='7 / 24',label='安装说明不完整，定向审查样本'),dict(value='10 / 24',label='交付信息存在缺口，定向审查样本')],readout_summary='一页可能同时存在多个缺口；三个计数不可相加为“受影响页面数”。')
    sec('D10','04｜商品、价格与库存','防护类占收入45%，其毛利率低于其他列示品类',[
        '防护与车身类贡献64.8万美元，占净销售额45.0%；对应毛利率45.0%，低于其他列示品类。销售集中在该类可以解释部分整体毛利结构，但不能独立证明应减少该类资源。',
        '本期Top20商品贡献93.6万美元，占65.0%，高于基准的50.0%。集中度上升意味着重点商品的可售性、内容与价格变化会影响更大范围，但不等于集中度本身必然有害。'],['S01','S03','S06'],
        'A03优先保障核心商品可售性；A05按品类与重点SKU审核贡献，而非用同一毛利目标管理全部商品。',
        '商品毛利未扣广告与履约；各品类复购价值、替代作用和获客作用尚未量化，不据此作简单优劣排名。',
        ['品类','本期净额（万美元）','收入占比','基准毛利率','本期毛利率'],[[label,cash('q2_'+k+'_sales'),pct('q2_'+k+'_share'),pct('q1_'+k+'_margin'),pct('q2_'+k+'_margin')] for k,label,*_ in cats],
        chart('hbar','图8｜本期品类净销售额','万美元',[dict(label=label,metric_id='q2_'+k+'_sales') for k,label,*_ in cats],10000,1,'2026年第二季度'))
    content('D10','04｜商品、价格与库存','品类结构与重点商品')
    sec('D11','04｜商品、价格与库存','折扣率升至15%，净客单价仍增长并不代表促销更有效',[
        '折前单均金额由205.88美元升至250.00美元；与此同时，每单折扣由20.59美元升至37.50美元，每单退款扣减由8.82美元升至12.50美元。净客单价最终由176.47美元升至200.00美元。',
        '客单价上升可能来自商品价格或组合，不必然来自成功加购；折扣率提高也不自动代表无效促销。要判断是否值得，需比较相同商品、活动人群和成本后的增量贡献。'],['S01','S03','S06'],
        'A05核对品类与促销人群中的折后贡献，明确优惠组合及例外审批；不能只用“客单价增长”验收促销。',
        '退款仍受观察窗影响；这里是金额桥，不提供单品价格弹性或折扣因果效果。',
        ['金额或比率','第一季度','第二季度','解释'],[
        ['折扣前金额（万美元）',cash('q1_gross'),cash('q2_gross'),'按本例有效订单行统计'],['折扣（万美元）',cash('q1_discount'),cash('q2_discount'),'净销售前扣减'],['折扣率',pct('q1_discount_rate'),pct('q2_discount_rate'),'分母为折扣前商品金额'],['退款（万美元）',cash('q1_refund'),cash('q2_refund'),'按订单季度归属、截至日累计'],['退款额／折后金额',pct('q1_refund_ratio',2),pct('q2_refund_ratio',2),'不是订单退货率'],['折前单均金额（美元）',cell('q1_gross_aov',1,2),cell('q2_gross_aov',1,2),'需拆价格与商品组合'],['净客单价（美元）',cell('q1_aov',1,2),cell('q2_aov',1,2),'不足以认证增量利润']])
    content('D11','04｜商品、价格与库存','价格、折扣与客单价')
    sec('D12','04｜商品、价格与库存','重点商品缺货与27万美元长库龄库存需要分开处理',[
        '本期末库存成本金额为90万美元，其中超过180天的库存27万美元，占30.0%，较基准的20.0%提高10个百分点。长库龄SKU为186个，不能仅用总库存增加判断供给充分。',
        '同期Top20商品中有5个在快照时点无可售库存。缺货、在途、页面上架和投放之间需要联动；库存充足的长尾商品不能替代有明确需求但无货的重点商品。'],['S06'],
        'A03分别交付重点SKU恢复／替代清单与长库龄分层处置清单；A12解决商品、供应链和投放的共同决策依赖。',
        '库存为成本金额，销售为净销售额，不可直接相除解释周转。没有逐日缺货暴露和反事实需求，不估计精确损失销售。',
        ['库存问题','现有证据','建议先核对','不应直接得出的结论'],[
        ['重点商品无货','5／20个重点SKU','可售、在途、补货周期、替代商品','5个SKU损失了25%销售'],['长库龄上升','15万→27万美元；占比20%→30%','成本、近期动销、可替代性、处置毛利','所有库存都应统一打折'],['库存规模增加','75万→90万美元','采购批次、季节性与交付计划','库存越多越安全'],['页面与投放联动','无逐SKU自动联动记录','无货时曝光、广告与订阅告知','现有投放全部浪费'],['现金与周转','缺完整采购付款和日均库存','采购账期、成本与销售成本口径','仅凭库存快照判断现金缺口']])
    content('D12','04｜商品、价格与库存','库存可售性与周转约束')
    sec('D13','05｜客户、订阅与邮件经营','非首单收入份额升至41.7%，不等于新客复购改善',[
        '首次购买客户由4,000增至4,200人，新增5.0%；期前已购买的老客从1,800增至1,900人。非首单订单由2,800增至3,000单，其净销售额从48万增至60万美元；该部分同时包含当季新客的追加购买。',
        '非首单销售占比由40.0%升至41.7%，订单占比由41.2%升至41.7%。这些季度结构说明重复购买订单的当期贡献，而新客是否更快产生第二单需要另看首购队列，不能混成同一个“复购率”。'],['S01','S07'],
        'A08同时跟踪非首单贡献与新客成熟队列；为不同购买阶段定义不同触达目标。',
        '非首单收入尚未进一步拆为当季新客追加单与期前老客订单，不能据此计算期前老客的平均收入。',
        ['客户或订单类型','第一季度','第二季度','正确用途'],[
        ['首次购买客户（人）',cell('q1_new_buyers'),cell('q2_new_buyers'),'获客规模'],['期前老客活跃人数（人）',cell('q1_return_buyers'),cell('q2_return_buyers'),'存量活跃规模'],['首单订单（单）',cell('q1_first_orders'),cell('q2_first_orders'),'首次成交'],['非首单订单（单）',cell('q1_return_orders'),cell('q2_return_orders'),'含当季新客追加单'],['非首单净销售额（万美元）',cash('q1_return_sales'),cash('q2_return_sales'),'重复购买订单贡献'],['非首单收入份额',pct('q1_return_sales_share'),pct('q2_return_sales_share'),'结构，不是队列复购'],['总购买客户（人）',cell('q1_buyers'),cell('q2_buyers'),'每季去重新老客合计']])
    content('D13','05｜客户、订阅与邮件经营','新老客户与价值结构')
    sec('D14','05｜客户、订阅与邮件经营','4—5月首购队列的30天复购率为7.36%，低于早期队列',[
        '1—3月首购的4,000人中，349人在30天内再次购买，复购率8.73%；4—5月首购的2,800人中，206人在30天内复购，复购率7.36%。绝对差异约1.37个百分点。',
        '不同队列的首购品类、渠道与季节可能不同，因此差异不能直接归为运营效果下降。6月30天、5月60天以及4月以后90天窗口尚未完全成熟，表中保留“待更新”。'],['S07'],
        'A08先按首购品类、可售后续商品与来源分层；A11预先定义成熟观察窗，避免用未成熟队列验收复购项目。',
        '没有给出统计区间或匹配比较，不宣称差异显著；短期复购不能替代长期客户价值。',
        ['首购月份','首购人数','30天复购率','60天复购率','90天复购率'],[[l,cell(k+'_cohort_n'),pct(k+'_rate30',2),pct(k+'_rate60',2),pct(k+'_rate90',2)] for (k,*_),l in zip(cohort,['1月','2月','3月','4月','5月','6月'])])
    content('D14','05｜客户、订阅与邮件经营','成熟队列与第二单')
    sec('D15','05｜客户、订阅与邮件经营','有效名单净增6,000人，价值验收仍应延伸到首购',[
        '本期新增有效订阅9,000人，扣除2,000人退订和1,000人抑制，名单由3.8万增至4.4万人，净增6,000人。合格曝光会话中的订阅率由5.0%升至6.0%。',
        '观察满30天的4月订阅3,000人中有300人首购，5月3,200人中有288人首购，合计588／6,200人，约9.48%。6月2,800人的窗口未成熟，不能作为无转化样本。'],['S08'],
        'A07把名单增长、可触达状态、首购和退订放在同一回收表；先验证欢迎路径和权益资格，不只提高弹窗提交率。',
        '未提供按来源与活动的完整订阅队列；不能把月度首购差异直接归因于优惠或文案。',
        ['名单项目','第一季度（人）','第二季度（人）','解释'],[
        ['期初有效名单',cell('q1_list_start'),cell('q2_list_start'),'具有可触达资格'],['新增有效订阅',cell('q1_signups'),cell('q2_signups'),'按邮箱去重'],['退订',cell('q1_unsubs'),cell('q2_unsubs'),'从有效名单移除'],['新增抑制',cell('q1_suppressed'),cell('q2_suppressed'),'不再作为可发送对象'],['净增有效名单',cell('q1_list_net'),cell('q2_list_net'),'新增减流出'],['期末有效名单',cell('q1_list_end'),cell('q2_list_end'),'期初加净增']])
    content('D15','05｜客户、订阅与邮件经营','订阅来源与首购转化')
    sec('D16','05｜客户、订阅与邮件经营','主动邮件收入增6.7%，每千次送达价值下降18.8%',[
        '主动邮件成功送达从105万增至138万次，增加31.4%；平台归因收入从21万增至22.4万美元，仅增6.7%。每千次送达归因收入由200.00美元降至162.32美元。',
        '全邮件点击记录率由1.50%降至1.00%，记录打开率却从30.0%升至35.0%。因此不宜以打开率上升单独判定内容改善，也不能未经分组就认定名单质量或频次是原因。'],['S01','S08','S09'],
        'A09按活动、来源、活跃度和购买阶段拆解单位价值；把退订、贡献和触达重叠作为护栏，而非只追求邮件归因GMV。',
        '本页平台邮件归因34.4万美元与统一渠道邮件归属19万美元不同口径，不能相加。打开、点击均为记录事件，不等于独立客户人数。',
        ['邮件指标','第一季度','第二季度','统计说明'],[
        ['成功送达（万次）',cell('q1_mail_delivered',10000,2),cell('q2_mail_delivered',10000,2),'主动活动＋自动化'],['送达率',pct('q1_mail_delivery_rate'),pct('q2_mail_delivery_rate'),'成功送达／发送'],['记录打开率',pct('q1_mail_opens_rate'),pct('q2_mail_opens_rate'),'不代表真实阅读比例'],['单封去重点击率',pct('q1_mail_clicks_rate',2),pct('q2_mail_clicks_rate',2),'跨发送可以重复'],['主动归因收入（万美元）',cash('q1_mail_campaign_rev'),cash('q2_mail_campaign_rev'),'平台固定口径'],['自动化归因收入（万美元）',cash('q1_mail_flow_rev'),cash('q2_mail_flow_rev'),'平台内部排重'],['统一渠道邮件收入（万美元）',cash('email_q1_sales'),cash('email_q2_sales'),'不可与平台归因相加']])
    content('D16','05｜客户、订阅与邮件经营','主动邮件与过程效率')
    sec('D17','05｜客户、订阅与邮件经营','自动化占平台邮件收入34.9%，购后覆盖仍只有28.6%',[
        '自动化归因收入从9万增至12万美元，增长33.3%，占邮件平台总归因收入34.9%；其成功送达仅占10.2%。这是不同触发场景的效率差异，不意味着可以将主动邮件全部替换成自动化。',
        '购后流程触达1,200名本期新客，占4,200名新客的28.6%。应先核查触发资格、签收时点、商品适配和触达排重，再决定扩大覆盖。'],['S07','S09'],
        'A08优先补齐首单后内容与关联推荐试点；A09协调主动活动和自动化排重，避免对同一批用户同时加频。',
        '弃购、欢迎、购后和召回的购买意图不同，每千次收入不可作为公平绩效排名。流程归因不等于因果净增量。',
        ['自动化流程','本期送达（次）','平台收入（万美元）','每千次送达收入（美元）','验证重点'],[[label,cell(k+'_delivered'),cash(k+'_rev'),cell(k+'_rpm',1,2),desc] for (k,label,*_),desc in zip(flows,['首购资格及订阅来源','触发时点和折扣侵蚀','签收后需求与第二单','沉默定义和退订护栏'])])
    content('D17','05｜客户、订阅与邮件经营','自动化与购后触达')
    sec('D18','06｜履约、反馈与测量','准时交付率降至89.7%，适配说明仍是高频反馈主题',[
        '有承诺日期且本期已签收的订单中，准时交付为6,100／6,800单，即89.7%，低于基准6,100／6,500单的93.8%。客服首响中位时间由10小时延长到16小时，需分开核查物流与服务承载。',
        '200条有效反馈中，65条涉及适配、42条涉及配送、31条涉及安装说明、18条涉及包装。一条反馈可以有多个主题；该分布只能提供优先调查线索。'],['S10'],
        'A10分别交付交付承诺、延迟告知和商品说明纠错；改善验收同时看可比样本、投诉类型和退货护栏。',
        '签收样本排除了尚未签收的订单，可能低估延迟；客服样本不代表所有客户，主题频次也不是影响收入的大小。',
        ['反馈主题','条目数','占200条有效反馈','对应核查'],[[label,cell(k),pct(k+'_share'),next_] for k,label,next_ in [('fitment','适配说明','商品、车型条件与入口'),('shipping','配送时效','承诺与实际签收'),('instructions','安装说明','内容缺口与使用阶段'),('packaging','包装','商品类型与运输破损')]],
        chart('hbar','图9｜客服反馈样本主题','条',[dict(label=l,metric_id=k) for k,l in [('fitment','适配说明'),('shipping','配送时效'),('instructions','安装说明'),('packaging','包装')]],1,0,'2026年第二季度；多主题样本n＝200'))
    content('D18','06｜履约、反馈与测量','履约与用户反馈')
    sec('D19','06｜履约、反馈与测量','统一指标后仍需补齐因果、长期价值和外部证据',[
        '本报告可以核对店铺净额、渠道归属、设备会话和列示成本；这些足以支持经营现状与验证顺序。但邮件平台归因、广告新客识别和长期客户价值属于不同测量层，不能拼成一个没有误差的总收益。',
        '数据工作应按决策影响排序：先解决会改变收入、贡献与验收结论的口径，再处理更细的自动化。不要因为有一个完美数据平台的设想，延迟能够安全执行的纠错。'],['S01','S02','S03','S09','S11','S13'],
        'A01形成统一字典，A11定义试验与去重规则；A12确保投放、商品、用户和研发共享同一版本的指标。',
        '现有程序校验能发现数值与引用错误，不能认证自然语言根因或外部来源真实性。真实报告仍需业务与数据双重复核。',
        ['测量问题','已具备部分','仍缺什么','影响的决策','对应行动'],[
        ['收入与贡献','统一净额及列示可变成本','固定成本与部分成本冲回核对','净利润判断','A01'],['渠道归因','互斥渠道分类','跨设备／平台归因匹配','增量预算分配','A04 / A11'],['移动根因','设备×渠道及顺序漏斗','逐访客商品与供给控制','全量改版','A02'],['客户价值','成熟短期队列','长期贡献及生命周期成本','长期获客上限','A01 / A11'],['竞争定位','自身搜索与页面证据','同口径外部样本','品牌投入与定位','A06'],['收益去重','共同人群与行动编号','试验效应及覆盖交集','项目组合ROI','A11']])
    content('D19','06｜履约、反馈与测量','测量、归因与数据治理')
    # Strategy section, pages 30-32.
    sec('T01','07｜策略选择与推进路线','优先选择“小范围修复与验证”，而不是直接全面扩张',[
        '现有证据支持先处理可核实的商品说明、可售性和成本口径，再通过有对照的试点判断增长动作。相比直接扩量，这种路径更符合当前贡献率下降且根因尚未识别的状态。',
        '这不是“停止增长”。基础投放、邮件与交付保持运行，但新增资源应按问题清晰度、验证成本、依赖和可逆性分批投入。任何重大预算调整仍须由实际决策人确认。'],['S03','S04','S06','S09','S11','S12'],
        'A12建议批准小范围试点与跨职能协作机制；A04、A07—A09在前置条件满足后分批启动，不同时启动全部动作。',
        '没有预算、团队容量和合同义务的真实输入，不能给出已承诺的资源分配；这里是可供决策的建议选项。',
        ['方案','潜在收益','主要风险','适用前提','本阶段建议'],[
        ['直接扩大流量与发送','可能较快增加账面收入','贡献率、触达疲劳与供给放大','边际贡献已验证、供给充足','暂不据当前数据普遍扩大'],['小范围修复与验证','澄清具体问题，保留可逆性','收益验证需要时间和样本','口径统一、可隔离试点','建议优先'],['全站体验重构','可能修复多个长期问题','成本高、归因难、范围易扩大','已证实结构性问题与能力约束','证据不足，不作为默认答案'],['全面促销清库存','可能加快部分库存出清','侵蚀贡献、影响主力供给策略','逐SKU处置收益已核对','只作分层方案，不全站套用']])
    content('T01','07｜策略选择与推进路线','方案比较与管理取舍')
    sec('T02','07｜策略选择与推进路线','移动端提升0.10个百分点，对应3.5万美元销售情景',[
        '仅以第二季度17.5万次移动会话测算，转化率提升0.10个百分点对应175单；净客单价保持200美元时，增加3.5万美元净销售额。不能用全站25万次会话放大移动端项目收益。',
        '以当前广告前单位贡献率约38.0%估算，中等情景对应约1.33万美元新增贡献，尚未扣新增实施、内容或营销成本。这个数是可供设定验证预算的条件量级，不是预计将获得的回报。'],['S01','S02','S03','S12'],
        'A11用实测效应和实际覆盖重算；移动体验、商品说明和购后等可能覆盖同一人群，未经去重不能把机会金额相加。',
        '广告前贡献率=(净销售额−商品成本−履约−支付费用)／净销售额；固定单价与成本结构可能不成立。三情景互斥，非置信区间、非预测、非净利润。',
        ['假设情景','移动转化率变化','新增订单（单）','新增净销售额（万美元）','新增广告前贡献（万美元）'],[[label,lift,cell(k+'_new_orders',1,1),cash(k+'_net_gain'),cell(k+'_contribution_gain',10000,2)] for k,label,lift in [('low','低幅情景','+0.05个百分点'),('base','中幅情景','+0.10个百分点'),('high','高幅情景','+0.20个百分点')]],claim='calculation')
    content('T02','07｜策略选择与推进路线','机会量级、成本与去重')
    sec('T03','07｜策略选择与推进路线','90天分阶段验收，以条件而非日历自动推进',[
        '推进路径分为口径与安全纠错、试点与观察、复核与扩大三个阶段。时间为建议窗口，是否进入下一阶段取决于输出、测量、样本与业务风险，而不是某一日期到来。',
        '每周用同一组结果、过程与护栏指标复核；每四周明确继续、调整或停止。尚未明确资源与权限的项目保留建议状态，不以表格上的日期制造已承诺交付。'],['S11','S12'],
        'A12组织周复核，A01负责基线版本，A11负责试验门槛；各职能仍对各自可控制的动作负责。',
        '低流量业务可能需要更长试验窗口；本例不规定统计样本量，也不把所有项目排成并行工作。',
        ['阶段','主要工作','可验收交付','进入下一阶段的条件'],[
        ['第1—2周：建立基线','A01／A03／A05；必要的A10纠错','口径差异清单、重点库存与促销规则','重要差异得到解释，责任与资源确认'],['第3—6周：小范围试点','A02／A04／A06／A07／A09，按容量选择','明确人群、变量、对照和护栏','测量稳定、互相干扰可控、样本计划可行'],['第6—10周：回收客户价值','A08／A11及持续观察','成熟队列、成本后效果与收益去重','效应与不确定性可解释，未突破护栏'],['第10—12周：决定扩大','A12主持取舍','继续／调整／停止记录与下一周期计划','经营贡献、资源与供给约束共同满足'],['每周持续','指标异常与依赖排查','单一版本的待办和决策日志','不改变既定实验指标以迎合结果']])
    content('T03','07｜策略选择与推进路线','90天路线与决策门槛')
    # Full action ledger, pages 36-39. Summary lists all, details preserve every field.
    for j in range(4):pg('P_actions_'+str(j+1),'actions','08｜完整行动台账','完整行动 '+actions[j*3]['id']+'—'+actions[j*3+2]['id'],action_ids=[a['id'] for a in actions[j*3:j*3+3]])
    sec('M01','09｜口径、复核与来源','明确分母与观察窗，避免跨模块结论互相矛盾',[
        '所有货币保留美元；正文按“万”展示，底层保留未舍入值。百分比用比例原值计算，率的变化写“个百分点”。同一指标在总览、图表和行动中来自同一数据文件。',
        '各项命名计算可复核，但不是所有自然语言都能自动校验。复核人员还需检查来源是否真实、替代解释是否遗漏，以及建议是否超出组织可执行范围。'],['S01','S02','S03','S07','S08','S09','S10','S11','S12'],
        '真实业务替换数据时，先重新核对字段与定义，再重写判断；不能保留示例的正负结论只替换数值。',
        '本报告为合成结构示例；页数、时期、角色和建议窗口均非咨询机构统一标准，也不代表真实企业决策。',
        ['指标／方法','定义或范围','容易误用的地方'],[
        ['净销售额','商品金额扣折扣、截至日退款；不含税运','不可混称GMV或会计收入'],['经营贡献额','净额扣本例列示可变成本与营销工具费','不是净利润'],['转化率','可比范围的支付订单／会话；本例一会话一单','不可平均分组比率'],['增长分解','依次替换流量、转化率、净客单价','顺序影响分项，非因果'],['渠道贡献','互斥统一渠道的净额变动','不与广告／邮件平台归因相加'],['客户复购','首购月队列内、完整观察窗的再次购买','非首单收入份额不等于队列复购率'],['订阅转化','有效订阅／合格曝光会话；首购另按订阅人群','不把原始名单数当可触达人数'],['邮件点击率','单封去重记录点击／成功送达次数','不是季度独立点击人数'],['准时交付率','已签收且有承诺日期订单中的准时占比','未签收订单不当作已准时'],['情景量级','覆盖人群×假设效应×单价／单位贡献','情景不加总、不等于净利润']])
    content('M01','09｜口径、复核与来源','指标定义与方法索引')
    for j,ids in enumerate([['S01','S02','S03'],['S04','S05','S06'],['S07','S08','S09'],['S10','S11','S12','S13']],1):pg('P_sources_'+str(j),'sources','09｜口径、复核与来源','来源与边界 '+str(j)+'／4',source_ids=ids)
    pg('P_back','back','封底','版本与使用边界')
    assert len(pages)==45,len(pages)
    report=dict(meta=dict(title='独立站经营现状诊断与策略建议',edition='中文专业报告 · 全面诊断示例 v3.2',period='2026年第二季度；季度比较另有注明',data_as_of='2026年7月7日',main_question='增长质量如何、瓶颈在哪里，未来90天应优先做什么？',scope='虚构装备零售独立站｜45页完整结构示例，全部业务数据为合成',language='zh-CN',synthetic=True,status='partial',depth='comprehensive',format_mode='full',audience='经营、产品与数据负责人',author='yesaze',report_date='2026年9月28日',confidentiality='公开合成示例'),
      sources=SS,metrics=M,
      summary=dict(bottom_line='净销售额由120万美元增至144万美元，增加24万美元（+20.0%）；经营贡献额由31.2万美元降至27.6万美元，减少3.6万美元（−11.5%）。现阶段应把贡献修复、主力商品可售性与购买路径验证前置，再以实测效果决定是否增加获客和触达投入。',findings=[
      dict(text='经营增长并不等于经营质量改善：收入144万美元（环比+24万美元／+20.0%），贡献额27.6万美元（环比−3.6万美元／−11.5%）；商品、履约和营销成本增长合计超过销售增量。',source_ids=['S01','S03']),
      dict(text='转化和客户价值需要分开诊断：移动端四渠道内转化均下降；成熟新客队列30天复购走弱，主动邮件单位送达价值也下降。',source_ids=['S02','S07','S09']),
      dict(text='建议保留基础经营、先做可核实纠错和小范围验证。完整总览列出12项发现、12项待办及13个覆盖模块，后文逐项论证。',source_ids=['S11','S12'])],next_step='优先确认贡献口径、重点库存和折扣边界；再按资源分批验证移动购买路径、付费获客、订阅首购及购后触达。第36—39页保留全部行动的交付、责任建议和推进门槛。',critical_limit='所有数据和安排为合成示例。部分商业判断缺外部市场样本、因果识别和长期队列；仅支持对应层级的阶段性判断，不以篇幅替代证据。'),
      kpis=[dict(label='本期净销售额',**cell('q2_net',10000,0,'万美元'),comparison='环比+24万美元／+20.0%；目标完成96.0%（144／150万美元）'),dict(label='经营贡献额',**cell('q2_contribution',10000,1,'万美元'),comparison='环比−3.6万美元／−11.5%；不是净利润'),dict(label='移动端转化率',**cell('q2_mobile_cvr',.01,2,'%'),comparison='4,200单／17.5万次会话；环比−0.60个百分点')],
      sections=sections,actions=actions,checks=checks,composition=dict(pages=pages),coverage=cover_objects)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--force',action='store_true');args=p.parse_args()
    r=make_comprehensive();res=validate(r)
    if not res['valid']:raise ValueError(json.dumps(res,ensure_ascii=False,indent=2))
    write_new(ROOT/'examples/comprehensive-report.json',json.dumps(r,ensure_ascii=False,indent=2)+'\n',args.force)
    write_new(ROOT/'examples/comprehensive-report.html',render(r),args.force)
    print(json.dumps(dict(**res,pages=len(r['composition']['pages']),metrics=len(r['metrics']),sections=len(r['sections']),actions=len(r['actions'])),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
