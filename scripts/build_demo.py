#!/usr/bin/env python3
"""Rebuild the deterministic synthetic Chinese report; no real business data or network."""
from pathlib import Path
import json
import argparse
from report_tools import ROOT, validate, write_new


def make_demo() -> dict:
    metrics={};checks=[]
    def m(mid,value,unit,source,status='synthetic'):
        metrics[mid]=dict(value=value,unit=unit,status=status,source_id=source);return mid
    def calc(mid,value,unit,source,op,inputs,tol=1e-8,status='calculated'):
        m(mid,value,unit,source,status)
        checks.append(dict(id='check_'+mid,op=op,inputs=inputs,result_metric=mid,tolerance=tol));return mid
    def cell(mid,scale=1,decimals=0,suffix=''):
        return dict(metric_id=mid,scale=scale,decimals=decimals,suffix=suffix)
    for name,a,b in [('paid',600000,780000),('organic',300000,330000),('email',180000,190000),('direct',120000,140000)]:
        m(name+'_q1',a,'美元','S1');m(name+'_q2',b,'美元','S1')
        calc(name+'_delta',b-a,'美元','S1','difference',[name+'_q2',name+'_q1'])
    calc('sales_q1',1200000,'美元','S1','sum',[k+'_q1' for k in ['paid','organic','email','direct']])
    calc('sales_q2',1440000,'美元','S1','sum',[k+'_q2' for k in ['paid','organic','email','direct']])
    calc('sales_delta',240000,'美元','S1','difference',['sales_q2','sales_q1'])
    calc('sales_growth',.2,'相对变化率','S1','relative_change',['sales_q2','sales_q1'])
    calc('paid_contribution',.75,'净增量份额','S1','ratio',['paid_delta','sales_delta'])
    m('target',1500000,'美元','S1')
    calc('achievement',.96,'比例','S1','ratio',['sales_q2','target'])
    calc('target_gap',-60000,'美元','S1','difference',['sales_q2','target'])
    for dev,p,s,o in [('mobile','q1',120000,3600),('desktop','q1',80000,3200),('mobile','q2',175000,4200),('desktop','q2',75000,3000)]:
        base=dev+'_'+p;m(base+'_sessions',s,'次','S2');m(base+'_orders',o,'单','S2')
        calc(base+'_cvr',o/s,'比例','S2','ratio',[base+'_orders',base+'_sessions'])
    for p in ['q1','q2']:
        ss=sum(metrics[d+'_'+p+'_sessions']['value'] for d in ['mobile','desktop'])
        oo=sum(metrics[d+'_'+p+'_orders']['value'] for d in ['mobile','desktop'])
        calc('total_'+p+'_sessions',ss,'次','S2','sum',[d+'_'+p+'_sessions' for d in ['mobile','desktop']])
        calc('total_'+p+'_orders',oo,'单','S2','sum',[d+'_'+p+'_orders' for d in ['mobile','desktop']])
        calc('total_'+p+'_cvr',oo/ss,'比例','S2','ratio',['total_'+p+'_orders','total_'+p+'_sessions'])
    calc('total_cvr_change',-.52,'个百分点','S2','pp_change',['total_q2_cvr','total_q1_cvr'])
    calc('mobile_cvr_change',-.6,'个百分点','S2','pp_change',['mobile_q2_cvr','mobile_q1_cvr'])
    calc('desktop_cvr_change',0,'个百分点','S2','pp_change',['desktop_q2_cvr','desktop_q1_cvr'])
    m('feedback_n',200,'条','S3')
    for mid,v in [('fitment',65),('shipping',42),('instructions',31),('packaging',18)]:
        m(mid,v,'条','S3');calc(mid+'_share',v/200,'比例','S3','ratio',[mid,'feedback_n'])
    # Explicit whole-site arithmetic scenarios, not a forecast or intervention effect.
    m('scenario_aov',200,'美元／单','S4')
    for mid,d in [('low',.001),('base',.002),('high',.003)]:
        m(mid+'_cvr_lift',d,'比例','S4','estimated')
        calc(mid+'_orders',250000*d,'单','S4','multiply',['total_q2_sessions',mid+'_cvr_lift'],status='estimated')
        calc(mid+'_sales',250000*d*200,'美元','S4','multiply',[mid+'_orders','scenario_aov'],status='estimated')
    report={
      'meta':dict(title='收入增长20%，转化率降至2.88%',edition='中文专业报告简报示例 · v3.2',period='2026年第二季度（对比第一季度）',data_as_of='2026年7月7日',main_question='增长来自哪里，下一阶段应优先验证什么？',scope='虚构零售业务｜统一口径净销售额、会话与反馈样本',language='zh-CN',synthetic=True,status='final',depth='brief',format_mode='brief'),
      'sources':[
        dict(id='S1',title='合成渠道净销售额',period='2026年第一、第二季度',locator='demo-report.json → metrics / sales_*、paid_*等',note='各渠道为互斥示例分类；净销售额不含税费、运费，已扣折扣及退款。目标150万美元也是合成示例。渠道归属用于算术分解，不等于因果增量。'),
        dict(id='S2',title='合成设备会话与订单',period='2026年第一、第二季度',locator='demo-report.json → metrics / mobile_*、desktop_*、total_*',note='订单数／会话数为本例转化率定义；合计先加总分子与分母再相除。假设订单归属与会话统计使用相同期间，未提供价格、库存、页面速度或实验数据。'),
        dict(id='S3',title='合成用户反馈主题',period='2026年第二季度；200条有效反馈',locator='demo-report.json → metrics / feedback_n、fitment等',note='每条反馈可包含多个主题。这里展示4类主题的条目数，不是互斥构成；样本来自假想反馈渠道，不能代表全部购买者。没有使用真实用户引语或身份信息。'),
        dict(id='S4',title='固定参数的合成情景假设',period='按一个季度估算',locator='demo-report.json → metrics / low_*、base_*、high_*；checks',note='以S2第二季度25万次会话为流量基线，假设客单价200美元保持不变。新增净销售额＝会话数×转化率提升幅度×客单价。三个情景互斥，不可相加；不含实施成本、促销侵蚀及额外退款，不是利润或预测。')],
      'metrics':metrics,
      'summary':dict(bottom_line='第二季度净销售额为144万美元，环比增长20%；付费渠道贡献了账面增量的75%。同期全站转化率下降0.52个百分点，现有资料不足以判断增长是否带来更高利润，也不能据此确定转化下滑的原因。',
        findings=[dict(text='净销售额增加24万美元，其中付费渠道增加18万美元；这一分解说明增量的账面归属，不证明广告的增量效果。',source_ids=['S1']),dict(text='移动端转化率由3.00%降至2.40%，桌面端维持4.00%；应先核对分群与路径，再决定改动页面还是调整流量。',source_ids=['S2']),dict(text='200条反馈中，65条涉及适配信息不清楚；这提示可验证的问题，不代表32.5%的全部客户都存在同样困难。',source_ids=['S3'])],
        next_step='先核对移动端人群、商品与路径差异；再针对证据支持的具体问题设计小范围验证。暂不把情景收入作为预算回报承诺。',
        critical_limit='缺少营销成本、毛利及对照实验，当前只支持结果描述与验证优先级，不支持利润改善或因果判断。'),
      'kpis':[dict(label='净销售额',**cell('sales_q2',10000,0,'万美元'),comparison='环比增加24万美元（+20%）'),dict(label='目标完成率',**cell('achievement',.01,1,'%'),comparison='示例目标150万美元；差额6万美元'),dict(label='全站转化率',**cell('total_q2_cvr',.01,2,'%'),comparison='第一季度3.40%；下降0.52个百分点')],
      'sections':[
        dict(id='channel',eyebrow='01｜增长来源',headline='新增24万美元中，18万美元归属于付费渠道',paragraphs=['净销售额从120万美元增至144万美元。付费渠道、自然搜索、邮件和直接访问分别增加18万、3万、1万和2万美元，分项与总增量一致。','75%表示付费渠道在本例净增量中的账面占比，而不是广告带来的因果贡献，也不能据此认定自然搜索没有增长机会。'],claim_type='calculation',source_ids=['S1'],limitation='本例采用互斥的统一渠道分类。真实报告应先排除平台归因重叠，再讨论贡献；投放回报还需要成本和增量识别。',implication='先核实付费渠道的利润与增量效果，再决定是否增加预算；仅凭收入归属不宜扩大投放。',chart=dict(type='waterfall',title='图1　净销售额变化分解',unit='万美元',period='2026年第一季度至第二季度',alt='起点120，加18、3、1和2，终点144；付费渠道为最大账面增量项。',source_ids=['S1'],scale=10000,decimals=0,rows=[dict(label='第一季度',metric_id='sales_q1',role='start'),dict(label='付费渠道',metric_id='paid_delta',role='delta'),dict(label='自然搜索',metric_id='organic_delta',role='delta'),dict(label='邮件',metric_id='email_delta',role='delta'),dict(label='直接访问',metric_id='direct_delta',role='delta'),dict(label='第二季度',metric_id='sales_q2',role='total')])),
        dict(id='device',eyebrow='02｜转化表现',headline='移动端转化率下降0.60个百分点，桌面端未变',paragraphs=['移动端会话从12万次增至17.5万次，订单从3,600单增至4,200单；订单增长慢于会话增长，转化率从3.00%降至2.40%。','全站转化率按总订单／总会话计算，从3.40%降至2.88%。设备占比也发生变化，因此不能直接平均两个设备的转化率，或把全站降幅全部归因于某个页面。'],claim_type='calculation',source_ids=['S2'],limitation='没有流量质量、商品结构、库存和页面性能数据。该对比定位了变化位置，但没有识别根因。',implication='后续核对优先覆盖移动端的人群与商品构成，再检查浏览、加购和结算阶段的损失。',chart=dict(type='dumbbell',title='图2　分设备转化率对比',unit='%',period='2026年第一季度与第二季度',alt='移动端3.00%下降到2.40%，桌面端两期均4.00%；全站3.40%下降到2.88%。',source_ids=['S2'],scale=.01,decimals=2,series_labels=['第一季度','第二季度'],y_min=0,y_max=4.8,rows=[dict(label='移动端',before='mobile_q1_cvr',after='mobile_q2_cvr'),dict(label='桌面端',before='desktop_q1_cvr',after='desktop_q2_cvr'),dict(label='全站',before='total_q1_cvr',after='total_q2_cvr')]),table=dict(headers=['设备','一季度会话（次）','一季度订单（单）','二季度会话（次）','二季度订单（单）'],rows=[[label,cell(k+'_q1_sessions'),cell(k+'_q1_orders'),cell(k+'_q2_sessions'),cell(k+'_q2_orders')] for label,k in [('移动端','mobile'),('桌面端','desktop'),('合计','total')]])),
        dict(id='feedback',eyebrow='03｜用户反馈',headline='适配信息是样本中最常被提及的问题',paragraphs=['200条有效反馈中，65条涉及适配信息不清楚，约占样本的32.5%；配送时效、安装说明和包装分别被42条、31条和18条反馈提及。','频次用于发现线索，不能单独代表问题严重性或改善收益。更重要的验证是：适配困惑出现在哪些商品、用户和购买阶段，是否真实阻碍成交。'],claim_type='interpretation',source_ids=['S3'],limitation='同一条反馈允许多个主题；上述类别不是互斥构成。样本比例不可外推为总体客户比例，未展示的其他主题也不能视为不存在。',implication='先核查高频适配问题的商品与路径，再决定是补充说明、改进选型入口，还是维持现状。',chart=dict(type='hbar',title='图3　反馈主题的样本频次',unit='条',period='2026年第二季度；有效反馈n=200',alt='适配信息65条、配送时效42条、安装说明31条、包装18条；多主题计数。',source_ids=['S3'],scale=1,decimals=0,rows=[dict(label=l,metric_id=k) for l,k in [('适配信息不清楚','fitment'),('配送时效','shipping'),('安装说明','instructions'),('包装','packaging')]]),table=dict(headers=['主题','反馈条目数','占有效样本'],rows=[[l,cell(k),cell(k+'_share',.01,1,'%')] for l,k in [('适配信息不清楚','fitment'),('配送时效','shipping'),('安装说明','instructions'),('包装','packaging')]])),
        dict(id='scenario',eyebrow='04｜机会测算',headline='每提升0.1个百分点，季度收入情景增加5万美元',paragraphs=['在季度会话数固定为25万次、客单价固定为200美元的假设下，全站转化率每提升0.1个百分点，对应增加250单、5万美元净销售额。','下表比较三种条件，不为其分配发生概率。它用于判断验证是否值得开展，不表示优化一定有效，更不是收益承诺。'],claim_type='calculation',source_ids=['S2','S4'],limitation='此处是全站提升情景，不能直接用于只覆盖移动端的改动。实施成本、毛利、促销与退款变化均未计入；三个情景不可相加。',implication='先通过有对照的验证估计真实效果，再结合覆盖流量、成本与利润决定是否扩大。',table=dict(headers=['假设情景','转化率提升','新增订单（单）','新增净销售额'],rows=[[label,f'{d:.1f}个百分点',cell(k+'_orders'),cell(k+'_sales',10000,0,'万美元')] for label,k,d in [('低幅提升','low',.1),('中幅提升','base',.2),('高幅提升','high',.3)]]))],
      'actions':[
        dict(id='A1',title='核对移动端的分群、商品与转化路径',rationale='对应转化率下滑，先区分结构变化与具体路径问题；不能直接把改页面作为默认答案。',owner='责任主体待明确',timing='建议作为首个验证步骤；完成日期待确认',success='完成同口径分群与阶段转化核对，给出支持或推翻现有解释的证据',gate='关键口径无法对齐时，先修复数据，不进入收益判断',dependencies='会话、订单、商品、渠道与路径数据',related_sections=['device'],status='proposed'),
        dict(id='A2',title='对已确认的问题开展小范围验证',rationale='适配反馈提供了研究线索；只对证据支持的问题提出改动，并保留未改动对照。',owner='执行与决策责任主体待明确',timing='在问题核实后启动；观察窗口按样本需求确定',success='预先定义主指标、退款等护栏及最小有意义改善幅度',gate='效果不确定、护栏恶化或成本超过收益时，不扩大；门槛需试验前约定',dependencies='稳定测量、足够样本及可隔离的实施范围',related_sections=['feedback','device'],status='proposed'),
        dict(id='A3',title='使用实测效果重算收益与投入上限',rationale='情景测算只提供量级参考，预算决策需要增量效果、覆盖流量、毛利和成本。',owner='业务及财务责任主体待明确',timing='在效果验证与成本核实后',success='保留公式、情景、净收益与主要敏感参数',gate='无法确认利润改善时，不将销售额情景作为投资回报承诺',dependencies='实验结果、毛利、实施成本、退款变化',related_sections=['channel','scenario'],status='proposed')],
      'checks':checks}
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--force',action='store_true');args=parser.parse_args()
    r=make_demo();v=validate(r)
    if not v['valid']:raise ValueError(v)
    write_new(ROOT/'examples/demo-report.json',json.dumps(r,ensure_ascii=False,indent=2)+'\n',args.force)
    print(json.dumps(v,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
