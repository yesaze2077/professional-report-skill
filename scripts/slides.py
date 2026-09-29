"""Offline 16:9 slide rendering from the reviewed shared report and slide plan."""
from __future__ import annotations

from itertools import groupby
from pathlib import Path

from report_tools import E, P, chart_svg, metric_text, number, table_html


def _metric_label(report: dict, mid: str) -> str:
    m = report["metrics"][mid]
    v = m["value"]
    if v is None:
        return {"missing": "未提供", "pending": "待更新", "not_applicable": "不适用"}.get(m["status"], "未提供")
    if m["unit"] == "比例": return number(v, .01, 1, "%")
    decimals = 1 if abs(v) < 100 else 0
    return number(v, 1, decimals, " " + m["unit"])


def _mini_matrix(section: dict, report: dict) -> str:
    table = section.get("table")
    if not table: return ""
    rows = table["rows"][:5]
    n = min(4, len(table["headers"]))
    fragment = {"headers": table["headers"][:n], "rows": [row[:n] for row in rows]}
    label = "主要证据矩阵" + (f" · 前{len(rows)}行；全部{len(table['rows'])}行见附录" if len(table["rows"]) > len(rows) else " · 全量见附录")
    return '<div class="matrix"><p class="visual-caption">'+E(label)+'</p>'+table_html(fragment, report)+'</div>'


def _evidence_visual(section: dict, report: dict) -> str:
    if "chart" in section:
        return '<div class="primary-visual">'+chart_svg(section["chart"], report, "slide-"+section["id"], dense=True)+'</div>'
    matrix = _mini_matrix(section, report)
    if matrix: return '<div class="primary-visual">'+matrix+'</div>'
    cards = []
    for point in section.get("evidence_points", []):
        for mid in point["metric_ids"][:2]:
            cards.append('<div class="metric-tile"><small>'+E(mid)+'</small><strong>'+E(_metric_label(report, mid))+'</strong></div>')
    return '<div class="metric-tiles">'+''.join(cards[:4])+'</div>'


def _evidence_list(section: dict, report: dict, chosen: list[str]) -> str:
    points = {p["id"]: p for p in section.get("evidence_points", [])}
    items = []
    for eid in chosen:
        point = points[eid]
        nums = ''.join('<span class="evidence-metric">'+E(_metric_label(report, mid))+'</span>' for mid in point["metric_ids"][:4])
        sources = '、'.join('<a href="#src-'+E(sid)+'">'+E(sid)+'</a>' for sid in point["source_ids"])
        items.append('<li><p>'+P(point["statement"] )+'</p><div>'+nums+'<span class="source-links">来源 '+sources+'</span></div></li>')
    return '<ol class="evidence-list">'+''.join(items)+'</ol>'


def _reasoning_visual(section: dict) -> str:
    steps = [
        ("证据支持", section["reasoning"]["interpretation"]),
        ("替代原因待排除", "；".join(section["reasoning"]["alternatives"])),
        ("业务含义", section["implication"]),
    ]
    parts = []
    for i, (label, text) in enumerate(steps, 1):
        parts.append('<div class="logic-step"><span class="logic-index">'+f'{i:02d}'+'</span><div><small>'+E(label)+'</small><p>'+P(text)+'</p></div></div>')
    return '<div class="logic-flow" role="img" aria-label="证据解释、替代原因与业务含义">'+''.join(parts)+'</div>'


def render_slides(report: dict) -> str:
    meta = report["meta"]
    plan = report["presentation"]["slides"]
    sections = {x["id"]: x for x in report["sections"]}
    actions = {x["id"]: x for x in report["actions"]}
    sources = {x["id"]: x for x in report["sources"]}
    visuals = {x["id"]: x for x in report["composition"]["pages"] if x["kind"] == "visual"}
    first_source_slide = next(x["id"] for x in plan if x["kind"] == "sources")
    total = len(plan)
    tag = "合成数据演示 · 非真实经营结论" if meta["synthetic"] else meta["confidentiality"]
    css = (Path(__file__).resolve().parents[1] / "assets/slides.css").read_text(encoding="utf-8")
    cards = []
    for i, slide in enumerate(plan, 1):
        kind = slide["kind"]
        sid = slide["id"]
        head = '<div class="slide-head"><span>'+E(slide["chapter"])+'</span><span>'+E(tag)+'</span></div>'
        title = '<h1>'+E(slide["title"] )+'</h1>'
        if kind == "cover":
            body = '<div class="cover-content"><p class="kicker">专业报告 · '+E(meta["edition"] )+'</p>'+title+'<p class="cover-question">'+E(meta["main_question"] )+'</p><div class="cover-rule"></div><p>'+E(meta["period"] )+' · '+E(meta["author"] )+' · '+E(meta["report_date"] )+'</p><p class="disclaimer">'+E(tag)+'；所有经营数据与界面均为合成示例。</p></div>'
        elif kind == "toc":
            entries = []
            for chapter, group in groupby(enumerate(plan,1), lambda x:x[1]["chapter"]):
                gg = list(group)
                if chapter in {"封面", "目录", "封底"}: continue
                start, end = gg[0][0], gg[-1][0]
                entries.append('<a class="toc-entry" href="#'+E(gg[0][1]["id"] )+'"><span>'+E(chapter)+'</span><b>'+f'{start:02d}—{end:02d}'+'</b></a>')
            body = title+'<p class="lede">先读管理摘要，再沿章节逐项查看证据、解释、行动与数据附录。按 ← → 翻页，点击页码可返回目录。</p><div class="toc-grid">'+''.join(entries)+'</div><p class="small-note">正文分析包含证据页与论证页；详细表格保留在可跳转附录。</p>'
        elif kind == "summary":
            kpis = ''.join('<div class="summary-kpi"><small>'+E(k["label"] )+'</small><strong>'+E(metric_text(report,k))+'</strong><p>'+E(k["comparison"] )+'</p></div>' for k in report.get("kpis", [])[:3])
            findings = ''.join('<li>'+P(x["text"] )+'</li>' for x in report["summary"]["findings"])
            body = title+'<p class="summary-line">'+P(report["summary"]["bottom_line"] )+'</p><div class="summary-kpis">'+kpis+'</div><div class="summary-bottom"><div><h2>关键发现</h2><ol>'+findings+'</ol></div><div><h2>优先决策</h2><p>'+P(report["summary"]["next_step"] )+'</p><p class="boundary">'+P(report["summary"]["critical_limit"] )+'</p></div></div>'
        elif kind == "analysis":
            section = sections[slide["section_id"]]
            phase = slide["phase"]
            appendix = 'SL_appendix_'+section["id"]
            badge = '<span class="section-badge">'+E(section["id"] )+' · '+('证据' if phase == 'evidence' else '解释与验证')+'</span>'
            if phase == "evidence":
                chosen = slide.get("evidence_ids", [p["id"] for p in section.get("evidence_points", [])])
                detail = '<a class="detail-link" href="#'+E(appendix)+'">查看详细指标表 →</a>' if "table" in section else ''
                body = badge+title+'<div class="analysis-grid"><div>'+_evidence_visual(section,report)+detail+'</div><div class="argument-panel"><h2>可追溯证据</h2>'+_evidence_list(section,report,chosen)+'<p class="scope-line">'+P(section["paragraphs"][0])+'</p></div></div>'
            else:
                narrative = ''.join('<p>'+P(x)+'</p>' for x in section["paragraphs"][1:])
                source_links = '、'.join('<a href="#src-'+E(x)+'">'+E(x)+'</a>' for x in section["source_ids"])
                body = badge+title+'<div class="analysis-grid reasoning-grid"><div>'+_reasoning_visual(section)+'</div><div class="argument-panel"><h2>判断如何形成</h2>'+narrative+'<div class="boundary"><b>适用边界</b><p>'+P(section["limitation"] )+'</p></div><p class="source-links">来源：'+source_links+'</p></div></div>'
        elif kind == "visual":
            page = visuals[slide["visual_page_id"]]
            if page["visual_kind"] == "process":
                visual = '<div class="process-flow">'+''.join('<div><b>'+f'{n:02d}'+'</b><span>'+E(step)+'</span></div>' for n,step in enumerate(page["steps"],1))+'</div>'
            else:
                visual = '<div class="synthetic-ui"><div class="ui-bar">合成商品详情页 · 页面结构示意</div><div class="ui-cols"><div class="ui-product">合成商品图占位</div><div class="ui-details"><h2>通用装备配件</h2><p>适配车型与年份</p><p>安装条件与步骤</p><p>可售状态与配送承诺</p><b>查看适配后选择</b></div></div></div>'
            readouts = ''.join('<div><strong>'+E(x["value"] )+'</strong><small>'+E(x["label"] )+'</small></div>' for x in page.get("readouts",[]))
            body = title+'<div class="visual-deck">'+visual+'<div class="readout-grid">'+readouts+'</div><p>'+P(page.get("readout_summary",page["visual_note"]))+'</p><p class="boundary">'+P(page["visual_note"] )+' 来源 <a href="#src-'+E(page["evidence_source_id"] )+'">'+E(page["evidence_source_id"] )+'</a>。</p></div>'
        elif kind == "actions":
            boxes=[]
            for aid in slide["action_ids"]:
                action = actions[aid]
                target = action["related_sections"][0]
                boxes.append('<article class="action-card" id="'+E(aid)+'"><small>'+E(aid)+' · 建议方案</small><h2>'+E(action["title"] )+'</h2><p>'+P(action["rationale"] )+'</p><dl><dt>交付 / 验收</dt><dd>'+P(action["success"] )+'</dd><dt>时间 / 责任</dt><dd>'+E(action["timing"] )+' · '+E(action["owner"] )+'</dd><dt>继续 / 停止</dt><dd>'+P(action["gate"] )+'</dd></dl><a href="#SL_'+E(target)+'_evidence">查看依据 '+E(target)+'</a></article>')
            body = title+'<div class="actions-grid">'+''.join(boxes)+'</div>'
        elif kind == "appendix":
            section = sections[slide["section_id"]]
            table=section["table"]
            fragment={"headers":table["headers"],"rows":table["rows"][slide["row_start"]:slide["row_end"]]}
            body = title+'<p class="lede">'+E(section["headline"] )+'。数值由同一份报告 JSON 中的指标 ID 渲染。</p><div class="appendix-table">'+table_html(fragment,report)+'</div><div class="appendix-foot"><p>来源：'+'、'.join('<a href="#src-'+E(x)+'">'+E(x)+'</a>' for x in section["source_ids"])+'</p><a href="#SL_'+E(section["id"] )+'_evidence">返回论证页</a></div>'
        elif kind == "sources":
            entries=[]
            for source_id in slide["source_ids"]:
                source=sources[source_id]
                entries.append('<article class="source-card" id="src-'+E(source_id)+'"><h2>'+E(source_id)+' · '+E(source["title"] )+'</h2><small>'+E(source["period"] )+'</small><p>'+P(source["note"] )+'</p><p>复核位置：'+E(source["locator"] )+'</p></article>')
            body=title+'<div class="source-grid">'+''.join(entries)+'</div>'
        elif kind == "back":
            body='<div class="back-content">'+title+'<h2>'+E(meta["title"] )+'</h2><p>'+P(report["summary"]["critical_limit"] )+'</p><div class="cover-rule"></div><p>'+E(meta["author"] )+' · '+E(meta["edition"] )+' · '+E(meta["report_date"] )+'</p><a href="#'+E(first_source_slide)+'">方法与来源</a></div>'
        else: raise ValueError('未知幻灯类型')
        footer = '<footer><a href="#SL_toc">目录</a><span>'+E(meta["period"] )+'</span><a href="#SL_toc" aria-label="返回目录">'+f'{i:02d} / {total:02d}'+'</a></footer>'
        cards.append('<section class="slide kind-'+E(kind)+'" id="'+E(sid)+'" data-index="'+str(i-1)+'">'+head+'<div class="slide-body">'+body+'</div>'+footer+'</section>')
    script = """(()=>{const slides=[...document.querySelectorAll('.slide')];let current=0;function show(i){current=Math.max(0,Math.min(slides.length-1,i));slides.forEach((s,n)=>{s.classList.toggle('active',n===current);s.setAttribute('aria-hidden',n===current?'false':'true')});document.title=(current+1)+' / '+slides.length+' · '+document.documentElement.dataset.title;}function target(){const raw=decodeURIComponent(location.hash.slice(1));if(!raw){show(0);return}const node=document.getElementById(raw);if(node){const slide=node.closest('.slide');if(slide)show(slides.indexOf(slide))}}window.addEventListener('hashchange',target);document.addEventListener('keydown',e=>{if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();location.hash=slides[Math.min(current+1,slides.length-1)].id}else if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();location.hash=slides[Math.max(current-1,0)].id}else if(e.key==='Home'){location.hash=slides[0].id}else if(e.key==='End'){location.hash=slides.at(-1).id}});target()})();"""
    # The inline script is fixed renderer code; all report content is escaped.
    return '<!doctype html><html lang="zh-CN" data-title="'+E(meta["title"] )+'"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; img-src data:; font-src \'none\'; base-uri \'none\'; form-action \'none\'"><title>'+E(meta["title"] )+'</title><style>'+css+'</style></head><body class="slides-report"><main class="deck">'+''.join(cards)+'</main><script>'+script+'</script></body></html>'
