#!/usr/bin/env python3
"""Validate and render the bounded Chinese report contract using the standard library.

This validates structure, references and declared calculations, not source truth or causality.
All input text is escaped. No formula strings, SQL, JavaScript or shell commands are run.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 4_000_000
EMPTY = {"missing": "未提供", "pending": "待更新", "not_applicable": "不适用"}


def read_json(path: Path) -> dict:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("数据文件超过4 MB参考实现限制")
    def no_constants(value: str) -> None:
        raise ValueError(f"不允许非有限数值：{value}")
    def no_duplicate(pairs: list) -> dict:
        out: dict = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"重复JSON字段：{key}")
            out[key] = value
        return out
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=no_constants,
                      object_pairs_hook=no_duplicate)


def schema_errors(value: Any, spec: dict, path: str = "$") -> list[str]:
    """Validate the JSON Schema subset used by the bundled, reference-free schema."""
    errors: list[str] = []
    if "anyOf" in spec:
        if not any(not schema_errors(value, choice, path) for choice in spec["anyOf"]):
            return [f"{path}：不符合任何允许的类型"]
        return []
    if "const" in spec and value != spec["const"]:
        errors.append(f"{path}：必须为 {spec['const']!r}")
    if "enum" in spec and value not in spec["enum"]:
        errors.append(f"{path}：值不在允许范围内")
    types = spec.get("type")
    if types is not None:
        types = types if isinstance(types, list) else [types]
        valid = {"object": isinstance(value, dict), "array": isinstance(value, list),
                 "string": isinstance(value, str), "boolean": isinstance(value, bool),
                 "number": isinstance(value, (int, float)) and not isinstance(value, bool),
                 "integer": isinstance(value, int) and not isinstance(value, bool),
                 "null": value is None}
        if not any(valid.get(t, False) for t in types):
            return errors + [f"{path}：需要类型 {'/'.join(types)}"]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            return errors + [f"{path}：数值必须有限"]
        for k, predicate in (("minimum", lambda a, b: a < b),
                             ("maximum", lambda a, b: a > b),
                             ("exclusiveMinimum", lambda a, b: a <= b)):
            if k in spec and predicate(value, spec[k]):
                errors.append(f"{path}：违反 {k}={spec[k]}")
    if isinstance(value, str) and len(value.strip()) < spec.get("minLength", 0):
        errors.append(f"{path}：文本不能为空")
    if isinstance(value, list):
        if len(value) < spec.get("minItems", 0) or len(value) > spec.get("maxItems", math.inf):
            errors.append(f"{path}：条目数超出范围")
        if spec.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            errors.append(f"{path}：存在重复项")
        for i, item in enumerate(value):
            errors.extend(schema_errors(item, spec.get("items", {}), f"{path}[{i}]"))
    if isinstance(value, dict):
        if len(value) < spec.get("minProperties", 0):
            errors.append(f"{path}：字段数量不足")
        for k in spec.get("required", []):
            if k not in value:
                errors.append(f"{path}.{k}：缺少必填字段")
        for k, val in value.items():
            properties = spec.get("properties", {})
            if k in properties:
                errors.extend(schema_errors(val, properties[k], f"{path}.{k}"))
            else:
                extra = spec.get("additionalProperties", True)
                if extra is False:
                    errors.append(f"{path}.{k}：不允许未知字段")
                elif isinstance(extra, dict):
                    errors.extend(schema_errors(val, extra, f"{path}.{k}"))
    return errors


def calculate(op: str, values: list[float]) -> float:
    if not values or any(v is None or not math.isfinite(v) for v in values):
        raise ValueError("计算需要完整的有限数值")
    if op in {"difference", "ratio", "relative_change", "pp_change"} and len(values) != 2:
        raise ValueError("该计算必须恰好有两个输入")
    if op == "sum": return math.fsum(values)
    if op == "multiply": return math.prod(values)
    a, b = values[0], values[1]
    if op == "difference": return a - b
    if op == "ratio":
        if b == 0: raise ValueError("分母不能为0")
        return a / b
    if op == "relative_change":
        if b <= 0: raise ValueError("相对增幅要求正基期；零或负基期请改用绝对变化")
        return (a - b) / b
    if op == "pp_change":
        if not all(0 <= x <= 1 for x in values):
            raise ValueError("百分点计算的原始比例必须在0至1之间")
        return (a - b) * 100
    raise ValueError("未知计算类型")


def safe_locator(s: str) -> bool:
    u = urlsplit(s)
    if u.scheme:
        return u.scheme in {"http", "https"} and bool(u.netloc) and not u.username and not u.password
    return not (s.startswith(("/", "\\")) or ".." in Path(s).parts or "\\" in s)


def validate(report: dict, editorial: bool = False) -> dict:
    spec = json.loads((ROOT / "schemas/report.schema.json").read_text(encoding="utf-8"))
    errors = schema_errors(report, spec)
    warnings: list[str] = []
    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings, "calculations_checked": 0}
    sources = {s["id"] for s in report["sources"]}
    sections = {s["id"] for s in report["sections"]}
    metrics = report["metrics"]
    for collection in ("sources", "sections", "actions", "checks"):
        ids = [x["id"] for x in report[collection]]
        if len(ids) != len(set(ids)):
            errors.append(f"{collection}：ID重复")
        if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", i) for i in ids):
            errors.append(f"{collection}：ID须为字母开头的字母、数字、下划线或连字符")
    for s in report["sources"]:
        if not safe_locator(s["locator"]): errors.append(f"来源{s['id']}：禁止危险链接、凭据URL或机器绝对路径")
    for mid, m in metrics.items():
        if m["source_id"] not in sources: errors.append(f"指标{mid}：来源不存在")
        if (m["status"] in EMPTY) != (m["value"] is None):
            errors.append(f"指标{mid}：缺失状态与null数值不一致")
        if m["unit"] == "比例" and m["value"] is not None and not 0 <= m["value"] <= 1:
            errors.append(f"指标{mid}：比例必须使用0至1原值")
    def refs(values: list[str], allowed: set, ctx: str) -> None:
        for x in values:
            if x not in allowed: errors.append(f"{ctx}：引用不存在的ID {x}")
    for f in report["summary"]["findings"]: refs(f["source_ids"], sources, "摘要")
    for k in report.get("kpis", []): refs([k["metric_id"]], set(metrics), "指标卡")
    for s in report["sections"]:
        refs(s["source_ids"], sources, s["id"])
        points = s.get("evidence_points", [])
        point_ids = [point["id"] for point in points]
        if len(point_ids) != len(set(point_ids)):
            errors.append(f"{s['id']}：证据点ID重复")
        for point in points:
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", point["id"]):
                errors.append(f"{s['id']}：证据点ID格式错误")
            refs(point["metric_ids"], set(metrics), s["id"]+"证据点")
            refs(point["source_ids"], sources, s["id"]+"证据点")
            for mid in point["metric_ids"]:
                if mid in metrics and metrics[mid]["source_id"] not in point["source_ids"]:
                    errors.append(f"{s['id']}：证据点缺少指标{mid}的来源")
            if not set(point["source_ids"]).issubset(s["source_ids"]):
                errors.append(f"{s['id']}：证据点来源须包含在分析单元来源中")
            if not point["metric_ids"] and not point["source_ids"]:
                errors.append(f"{s['id']}：证据点缺少指标与来源")
        if editorial:
            if not points: errors.append(f"{s['id']}：编辑审查缺少证据点")
            if "reasoning" not in s: errors.append(f"{s['id']}：编辑审查缺少解释和替代原因")
            if re.search(r"并不代表|不等于|不能说明|无法证明|不一定|不能直接", s["headline"]):
                errors.append(f"{s['id']}：标题含含糊否定表达；请把边界移至解释")
            if re.search(r"\d[^，；。]*?(?:%|美元|万元|百分点|万次|万单|万条)", s["headline"]) and not any(x["metric_ids"] for x in points):
                errors.append(f"{s['id']}：量化标题缺少指标证据引用")
        if s["claim_type"] == "causal": warnings.append(f"{s['id']}：因果判断需要人工复核识别设计，程序无法认证")
        if "table" in s:
            t = s["table"]
            for row in t["rows"]:
                if len(row) != len(t["headers"]): errors.append(f"{s['id']}：表格列数不匹配")
                for cell in row:
                    if isinstance(cell, dict):
                        refs([cell["metric_id"]], set(metrics), s["id"]+"表格")
                        if cell["metric_id"] in metrics and metrics[cell["metric_id"]]["source_id"] not in s["source_ids"]:
                            errors.append(f"{s['id']}：表格缺少所用指标来源")
        if "chart" not in s: continue
        c = s["chart"]; typ = c["type"]; rows = c["rows"]
        refs(c["source_ids"], sources, s["id"]+"图表")
        if not set(c["source_ids"]).issubset(s["source_ids"]): errors.append(f"{s['id']}：图表来源应包含于章节来源")
        expected = {"label", "before", "after"} if typ == "dumbbell" else {"label", "metric_id"}
        if typ == "waterfall": expected.add("role")
        if typ == "dumbbell" and "series_labels" not in c: errors.append(f"{s['id']}：哑铃图缺少两个时期名称")
        if typ != "dumbbell" and "series_labels" in c: errors.append(f"{s['id']}：该图型不接受series_labels")
        values = []
        for row in rows:
            if set(row) != expected:
                errors.append(f"{s['id']}：{typ}图行字段必须为{sorted(expected)}")
                continue
            mids = [row[k] for k in ("before", "after")] if typ == "dumbbell" else [row["metric_id"]]
            refs(mids, set(metrics), s["id"]+"图表")
            for mid in mids:
                if mid not in metrics: continue
                m = metrics[mid]; values.append(m["value"])
                if m["source_id"] not in c["source_ids"]: errors.append(f"{s['id']}：图表来源未覆盖指标{mid}")
        if typ == "waterfall":
            roles = [r.get("role") for r in rows]
            if len(rows) < 3 or roles != ["start"] + ["delta"] * (len(rows)-2) + ["total"]:
                errors.append(f"{s['id']}：瀑布图必须是起点、变化分项、终点")
            if len(values) == len(rows) and all(v is not None for v in values):
                if not math.isclose(math.fsum(values[:-1]), values[-1], abs_tol=1e-7, rel_tol=1e-10):
                    errors.append(f"{s['id']}：瀑布图起点＋变化分项不等于终点")
            else: errors.append(f"{s['id']}：瀑布图不能含缺失数值")
        if typ == "line" and len(rows) < 3: errors.append(f"{s['id']}：折线图至少需要三个有序时期")
        finite = [v / c["scale"] for v in values if v is not None]
        if not finite: errors.append(f"{s['id']}：图表没有可呈现数值")
        lo, hi = c.get("y_min"), c.get("y_max")
        if lo is not None and hi is not None and lo >= hi: errors.append(f"{s['id']}：坐标上界须大于下界")
        if finite and ((lo is not None and lo > min(finite)) or (hi is not None and hi < max(finite))):
            errors.append(f"{s['id']}：坐标范围截掉实际数值")
        if typ in {"hbar", "waterfall"} and ((lo is not None and lo > 0) or (hi is not None and hi < 0)):
            errors.append(f"{s['id']}：条形及瀑布图必须包含零基线")
        if typ in {"hbar", "waterfall"} and any(k in c for k in ("y_min", "y_max")):
            errors.append(f"{s['id']}：此参考实现的条形及瀑布图使用自动零基线，不接受手动轴界")
    for a in report["actions"]: refs(a["related_sections"], sections, a["id"]+"行动")
    mode = report["meta"].get("format_mode")
    if mode == "full":
        for field in ("audience", "author", "report_date", "confidentiality"):
            if not report["meta"].get(field): errors.append(f"完整版封面缺少{field}")
        if "composition" not in report: errors.append("完整版须提供封面、目录、摘要、正文、附录与封底的篇章编排")
    if report["meta"].get("depth") == "comprehensive":
        if "composition" not in report: errors.append("全面诊断须提供可审查的篇章编排composition")
        if "coverage" not in report: errors.append("全面诊断须提供范围覆盖台账coverage")
    if "composition" in report:
        pp = report["composition"]["pages"]
        pids = [p["id"] for p in pp]
        if len(pids) != len(set(pids)): errors.append("篇章页ID重复")
        if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", i) for i in pids): errors.append("篇章页ID格式错误")
        kinds = [p["kind"] for p in pp]
        if mode == "full":
            if len(pp) < 5 or kinds[0:2] != ["cover", "toc"] or kinds[-1] != "back":
                errors.append("完整版须按封面、目录开篇并以封底结束")
            if kinds.count("summary") != 1 or ("summary" in kinds and kinds.index("summary") < 2):
                errors.append("完整版目录后必须有唯一管理摘要")
            if not {"content", "actions", "sources"}.issubset(kinds):
                errors.append("完整版须包含正文、行动与方法来源")
            if kinds.count("cover") != 1 or kinds.count("toc") != 1 or kinds.count("back") != 1:
                errors.append("完整版封面、目录、封底必须各一页")
        elif kinds[0] != "summary" or kinds.count("summary") != 1:
            errors.append("篇章编排必须以唯一核心摘要开始")
        dom_ids=pids+list(sections)+[a["id"] for a in report["actions"]]+["src-"+x for x in sources]
        if len(dom_ids)!=len(set(dom_ids)): errors.append("篇章、正文、行动或来源的HTML锚点ID冲突")
        used_sections=[]; used_actions=[]; used_sources=[]
        action_set={a["id"] for a in report["actions"]}
        for p in pp:
            allowed={"content":"section_ids","actions":"action_ids","sources":"source_ids"}.get(p["kind"])
            for field in ("section_ids","action_ids","source_ids"):
                if field == allowed and field not in p: errors.append(f"{p['id']}：缺少{field}")
                if field != allowed and field in p: errors.append(f"{p['id']}：页类型不接受{field}")
            refs(p.get("section_ids",[]),sections,p["id"])
            refs(p.get("action_ids",[]),action_set,p["id"])
            refs(p.get("source_ids",[]),sources,p["id"])
            visual_fields = ("visual_kind", "visual_title", "visual_note", "evidence_source_id", "steps", "readouts", "readout_summary")
            if p["kind"] == "visual":
                for field in visual_fields[:4]:
                    if field not in p: errors.append(f"{p['id']}：视觉证据页缺少{field}")
                if p.get("visual_kind") == "process" and "steps" not in p:
                    errors.append(f"{p['id']}：流程图缺少steps")
                if p.get("visual_kind") == "synthetic_ui" and "steps" in p:
                    errors.append(f"{p['id']}：合成界面页不接受steps")
                refs([p["evidence_source_id"]],sources,p["id"]+"视觉证据") if "evidence_source_id" in p else None
            elif any(field in p for field in visual_fields):
                errors.append(f"{p['id']}：非视觉证据页不接受视觉字段")
            used_sections.extend(p.get("section_ids",[]));used_actions.extend(p.get("action_ids",[]));used_sources.extend(p.get("source_ids",[]))
        for label,used,expected in [("分析单元",used_sections,sections),("完整行动",used_actions,action_set),("来源",used_sources,sources)]:
            if set(used)!=expected: errors.append(f"篇章编排遗漏{label}或引用不存在对象")
            if len(used)!=len(set(used)): errors.append(f"篇章编排重复呈现{label}；概览请用交叉引用而非重复全文")
    if "presentation" in report:
        slides = report["presentation"]["slides"]
        slide_ids = [slide["id"] for slide in slides]
        if len(slide_ids) != len(set(slide_ids)): errors.append("幻灯ID重复")
        if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", sid) for sid in slide_ids):
            errors.append("幻灯ID格式错误")
        kinds = [slide["kind"] for slide in slides]
        if kinds[:2] != ["cover", "toc"] or kinds[-1:] != ["back"]:
            errors.append("幻灯须以封面、目录开篇并以封底结束")
        if not {"summary", "analysis", "actions", "sources", "appendix"}.issubset(kinds):
            errors.append("完整论证幻灯须包含摘要、分析、行动、来源和附录")
        analyzed = []
        appendix = []
        appendix_rows: dict[str, list[int]] = {}
        shown_actions = []
        shown_sources = []
        visual_ids = {page["id"] for page in report.get("composition", {}).get("pages", []) if page["kind"] == "visual"}
        for slide in slides:
            kind = slide["kind"]
            allowed = {"analysis": {"section_id", "evidence_ids", "phase"}, "appendix": {"section_id", "row_start", "row_end"},
                       "visual": {"visual_page_id"}, "actions": {"action_ids"},
                       "sources": {"source_ids"}}.get(kind, set())
            used = set(slide) - {"id", "kind", "chapter", "title"}
            if not used <= allowed: errors.append(f"{slide['id']}：幻灯类型不接受{sorted(used-allowed)}")
            required = {"analysis": "section_id", "appendix": "section_id", "visual": "visual_page_id",
                        "actions": "action_ids", "sources": "source_ids"}.get(kind)
            if required and required not in slide: errors.append(f"{slide['id']}：缺少{required}")
            if kind == "appendix" and ("row_start" not in slide or "row_end" not in slide):
                errors.append(f"{slide['id']}：附录缺少行范围")
            if kind == "analysis" and "phase" not in slide: errors.append(f"{slide['id']}：分析幻灯缺少phase")
            sid = slide.get("section_id")
            if sid:
                refs([sid], sections, slide["id"])
                if kind == "analysis": analyzed.append((sid, slide.get("phase")))
                if kind == "appendix":
                    appendix.append(sid)
                    if "row_start" in slide and "row_end" in slide:
                        appendix_rows.setdefault(sid, []).extend(range(slide["row_start"], slide["row_end"]))
                        if slide["row_start"] >= slide["row_end"]:
                            errors.append(f"{slide['id']}：附录行范围为空")
            if "evidence_ids" in slide and sid in sections:
                allowed_points = {x["id"] for x in next(s for s in report["sections"] if s["id"] == sid).get("evidence_points", [])}
                refs(slide["evidence_ids"], allowed_points, slide["id"]+"证据点")
            if "visual_page_id" in slide: refs([slide["visual_page_id"]], visual_ids, slide["id"]+"视觉页")
            if "action_ids" in slide:
                refs(slide["action_ids"], {a["id"] for a in report["actions"]}, slide["id"])
                shown_actions.extend(slide["action_ids"])
            if "source_ids" in slide:
                refs(slide["source_ids"], sources, slide["id"])
                shown_sources.extend(slide["source_ids"])
        required_analysis = {(sid, phase) for sid in sections for phase in ("evidence", "reasoning")}
        if set(analyzed) != required_analysis or len(analyzed) != len(required_analysis):
            errors.append("幻灯计划须以证据页和论证页恰好覆盖全部分析单元")
        tables = {s["id"] for s in report["sections"] if "table" in s}
        if not tables <= set(appendix): errors.append("幻灯附录遗漏正文详细表格")
        for section in report["sections"]:
            sid=section["id"]
            if "table" in section and sorted(appendix_rows.get(sid, [])) != list(range(len(section["table"]["rows"]))):
                errors.append(f"{sid}：幻灯附录表格行遗漏或重复")
        if set(shown_actions) != {a["id"] for a in report["actions"]} or len(shown_actions) != len(set(shown_actions)):
            errors.append("幻灯行动页须恰好覆盖全部行动")
        if set(shown_sources) != sources or len(shown_sources) != len(set(shown_sources)):
            errors.append("幻灯来源页须恰好覆盖全部来源")
        if editorial:
            for slide in slides:
                if re.search(r"并不代表|不等于|不能说明|无法证明|不一定|不能直接", slide["title"]):
                    errors.append(f"{slide['id']}：幻灯标题含含糊否定表达")
    elif editorial and report["meta"].get("format_mode") == "full":
        warnings.append("未提供幻灯计划；只审查A4报告")
    domains=[c["domain"] for c in report.get("coverage",[])]
    if len(domains)!=len(set(domains)): errors.append("覆盖台账模块重复")
    for cov in report.get("coverage",[]):
        refs(cov["section_ids"],sections,"范围覆盖")
        refs(cov["action_ids"],{a["id"] for a in report["actions"]},"范围覆盖")
        if cov["status"] in {"covered","partial"} and not cov["section_ids"]:
            errors.append("已覆盖或部分覆盖的模块必须指向正文")
        if cov["status"] == "missing" and not cov["action_ids"]:
            warnings.append(cov["domain"]+"：缺失模块未关联补证行动")
    checked = 0
    for check in report["checks"]:
        ids = check["inputs"] + [check["result_metric"]]
        refs(ids, set(metrics), check["id"])
        if any(i not in metrics for i in ids): continue
        try:
            actual = calculate(check["op"], [metrics[i]["value"] for i in check["inputs"]])
            expected_val = metrics[check["result_metric"]]["value"]
            if expected_val is None or not math.isfinite(actual) or not math.isclose(actual, expected_val, rel_tol=0, abs_tol=check["tolerance"]):
                errors.append(f"{check['id']}：计算结果与指标不一致")
            checked += 1
        except (ValueError, TypeError, OverflowError) as e:
            errors.append(f"{check['id']}：{e}")
    text = json.dumps(report, ensure_ascii=False)
    # Targeted screen only, not a guarantee that all PII or confidential facts are absent.
    sensitive = [r"\bsk-[A-Za-z0-9_-]{20,}", r"\bgh[pousr]_[A-Za-z0-9]{20,}",
                 r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"]
    if any(re.search(pattern, text) for pattern in sensitive): errors.append("检测到疑似密钥、私钥或邮箱；请先脱敏，不在错误信息回显原值")
    if not report["checks"]: warnings.append("未声明计算检查；不能据此认定数字已验证")
    return {"valid": not errors, "errors": errors, "warnings": warnings, "calculations_checked": checked}


def number(value: float | None, scale: float = 1, decimals: int = 1, suffix: str = "", status: str = "observed") -> str:
    if value is None: return EMPTY.get(status, "未提供")
    if not math.isfinite(value) or not math.isfinite(scale) or scale <= 0:
        raise ValueError("数值及比例尺必须有效")
    q = (Decimal(str(value)) / Decimal(str(scale))).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    if q == 0: q = abs(q)
    return f"{q:,.{decimals}f}" + suffix


def E(value: Any) -> str: return html.escape(str(value), quote=True)


def P(value: Any) -> str:
    """Keep short quantitative expressions together without accepting input markup."""
    escaped = E(value)
    pattern = r"(?<![A-Za-z0-9])[-+−]?\d[\d,]*(?:\.\d+)?(?:个?百分点|万美元|亿美元|美元|亿元|万元|%|万次|次|万人|人|万单|单|万条|条|份)"
    return re.sub(pattern, lambda m: '<span class="nowrap">'+m.group(0)+'</span>', escaped)


def metric_text(report: dict, cell: dict) -> str:
    m = report["metrics"][cell["metric_id"]]
    return number(m["value"], cell.get("scale", 1), cell.get("decimals", 1), cell.get("suffix", ""), m["status"])


def source_refs(ids: list[str]) -> str:
    return "、".join(f'<a href="#src-{E(s)}">{E(s)}</a>' for s in ids)


def table_html(t: dict, report: dict, caption: str = "") -> str:
    header = "".join(f'<th scope="col">{E(x)}</th>' for x in t["headers"])
    rows = []
    for row in t["rows"]:
        cells = []
        for x in row:
            cells.append(f'<td class="num">{E(metric_text(report,x))}</td>' if isinstance(x,dict) else f'<td>{E(x)}</td>')
        rows.append('<tr>'+''.join(cells)+'</tr>')
    cap = f'<caption>{E(caption)}</caption>' if caption else ''
    return f'<div class="table-scroll" tabindex="0"><table>{cap}<thead><tr>{header}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def chart_svg(c: dict, report: dict, cid: str, dense: bool = False) -> str:
    """Four deliberately simple chart families, with direct labels and accessible data."""
    typ = c["type"]; rows = c["rows"]; metrics = report["metrics"]
    def raw(mid: str) -> float | None: return metrics[mid]["value"]
    def val(mid: str) -> float | None:
        v = raw(mid); return None if v is None else v / c["scale"]
    def txt(x: float, signed=False) -> str:
        return ("+" if signed and x > 0 else "")+number(x,1,c["decimals"])
    W=720; H=330 if typ in {"waterfall","line"} else (max(225,85+60*len(rows)) if typ=="dumbbell" else max(225,85+(40 if dense else 55)*len(rows)))
    pieces=[f'<svg class="chart-svg" viewBox="0 0 {W} {H}" role="img" aria-labelledby="{cid}-t {cid}-d" xmlns="http://www.w3.org/2000/svg">',
            f'<title id="{cid}-t">{E(c["title"])}</title><desc id="{cid}-d">{E(c["alt"])}</desc>']
    def text(x,y,s,cls="tick",anchor="start"):
        pieces.append(f'<text x="{x:.2f}" y="{y:.2f}" class="{cls}" text-anchor="{anchor}">{E(s)}</text>')
    def line(x1,y1,x2,y2,cls="grid"):
        pieces.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" class="{cls}"/>')
    def circle(x,y,r,cls): pieces.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" class="{cls}"/>')
    def rect(x,y,w,h,cls): pieces.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(0,w):.2f}" height="{max(0,h):.2f}" class="{cls}"/>')
    if typ == "hbar":
        vv=[val(r["metric_id"]) for r in rows]; known=[v for v in vv if v is not None]
        low=min(0,min(known)); high=max(0,max(known)); span=high-low or 1
        left,right=170,632; x=lambda v:left+(v-low)/span*(right-left)
        line(x(0),25,x(0),H-28,"axis")
        for i,(r,v) in enumerate(zip(rows,vv)):
            y=42+i*(40 if dense else 55);text(152,y+5,r["label"],"category","end")
            if v is None: text(left,y+5,"未提供","value");continue
            rect(min(x(0),x(v)),y-14,abs(x(v)-x(0)),27,"bar-accent" if i==0 else "bar-neutral")
            text(685,y+5,txt(v),"value","end")
        text(170,H-8,"零基线；条形长度表示数量","small")
    elif typ == "dumbbell":
        known=[val(r[k]) for r in rows for k in ("before","after") if val(r[k]) is not None]
        low=c.get("y_min",min(0,min(known)));high=c.get("y_max",max(known)*1.15 or 1)
        left,right=146,626;x=lambda v:left+(v-low)/(high-low)*(right-left)
        for i in range(5):
            v=low+(high-low)*i/4;xx=x(v);line(xx,62,xx,H-40);text(xx,H-15,txt(v),"tick","middle")
        circle(164,25,6,"dot-before");text(178,30,c["series_labels"][0],"tick")
        circle(323,25,6,"dot-after");text(337,30,c["series_labels"][1],"tick")
        for i,r in enumerate(rows):
            a,b=val(r["before"]),val(r["after"]);y=91+i*60
            text(128,y+5,r["label"],"category","end")
            if a is None or b is None:text(155,y+5,"存在未提供值，不连线","value");continue
            line(x(a),y,x(b),y,"connector");circle(x(a),y,7,"dot-before");circle(x(b),y,5.5,"dot-after")
            if abs(a-b)<1e-12:text(x(a),y-17,txt(a),"value","middle")
            else:
                text(x(a),y-17,txt(a),"value","middle");text(x(b),y+28,txt(b),"value","middle")
    elif typ == "waterfall":
        vs=[val(r["metric_id"]) for r in rows]; start=0; ends=[]
        for r,v in zip(rows,vs):
            a=0 if r["role"] in {"start","total"} else start;b=a+v;ends.append((a,b));start=b
        low=min(0,min(min(a,b) for a,b in ends));high=max(0,max(max(a,b) for a,b in ends));span=high-low or 1
        top,bottom,left,right=38,H-64,54,697;y=lambda v:bottom-(v-low)/span*(bottom-top)
        for i in range(5):
            v=low+span*i/4;line(left,y(v),right,y(v));text(left-9,y(v)+5,number(v,1,0),"tick","end")
        step=(right-left)/len(rows);bw=min(64,step*.65)
        for i,(r,v,(a,b)) in enumerate(zip(rows,vs,ends)):
            xx=left+step*(i+.5);rect(xx-bw/2,min(y(a),y(b)),bw,max(1,abs(y(a)-y(b))),"bar-accent" if r["role"] in {"start","total"} else "bar-neutral")
            text(xx,min(y(a),y(b))-9,txt(v,r["role"]=="delta"),"value","middle")
            text(xx,H-35,r["label"],"category","middle")
            if i<len(rows)-1 and rows[i+1]["role"]=="delta":line(xx+bw/2,y(b),xx+step-bw/2,y(b),"bridge")
        text(54,H-5,"期初＋各项变化＝期末；此分解不证明因果","small")
    else:
        vs=[val(r["metric_id"]) for r in rows];known=[v for v in vs if v is not None]
        low=c.get("y_min",min(0,min(known)));high=c.get("y_max",max(known)*1.12 or 1)
        if high==low:high=low+1
        left,right,top,bottom=60,685,38,H-52
        x=lambda i:left+i*(right-left)/(len(rows)-1);y=lambda v:bottom-(v-low)/(high-low)*(bottom-top)
        for i in range(5):
            v=low+(high-low)*i/4;line(left,y(v),right,y(v));text(left-9,y(v)+5,txt(v),"tick","end")
        prev=None
        for i,(r,v) in enumerate(zip(rows,vs)):
            if len(rows)<=8 or i in {0,len(rows)-1}:text(x(i),H-23,r["label"],"tick","middle")
            if v is None:prev=None;continue
            if prev is not None:line(x(prev),y(vs[prev]),x(i),y(v),"trend")
            circle(x(i),y(v),4,"dot-after");text(x(i),y(v)-12,txt(v),"value","middle");prev=i
    pieces.append('</svg>')
    dataheaders=["项目",*c["series_labels"]] if typ=="dumbbell" else ["项目",f'数值（{c["unit"]}）']
    datarows=[]
    for row in rows:
        mids=[row[k] for k in ("before","after")] if typ=="dumbbell" else [row["metric_id"]]
        datarows.append([row["label"]]+[dict(metric_id=m,scale=c["scale"],decimals=c["decimals"],suffix="") for m in mids])
    detail=table_html({"headers":dataheaders,"rows":datarows},report)
    return f'<figure><figcaption><b>{E(c["title"])}</b><span>{E(c["period"])} · 单位：{E(c["unit"])}</span></figcaption><div class="chart-scroll" tabindex="0">{"".join(pieces)}</div><details class="chart-data"><summary>查看图表数据</summary>{detail}</details></figure>'


def render(report: dict, layout: str = "report") -> str:
    result=validate(report)
    if not result["valid"]:raise ValueError("数据校验失败："+"；".join(result["errors"]))
    if layout == "slides":
        if "presentation" not in report: raise ValueError("幻灯渲染需要显式presentation.slides计划")
        from slides import render_slides
        return render_slides(report)
    if layout != "report": raise ValueError("未知版式")
    if "composition" in report:
        from longform import render_composed
        return render_composed(report)
    m=report["meta"];summary=report["summary"]
    css=(ROOT/"assets/report.css").read_text(encoding="utf-8")
    tag="合成数据演示｜非真实经营结论" if m["synthetic"] else "内部报告"
    if m["status"]=="partial":tag+="｜阶段性结果"
    def page(content: str, index: int, total: int) -> str:
        return f'<section class="report-page"><header class="running"><span>{E(m["edition"])}</span><span>{E(tag)}</span></header>{content}<footer><span>{E(m["period"])}</span><span>{index:02d} / {total:02d}</span></footer></section>'
    total=len(report["sections"])+2+(1 if report["actions"] else 0)
    findings="".join(f'<div class="finding"><span class="finding-no">{i:02d}</span><p>{P(f["text"])} <sup>{source_refs(f["source_ids"])}</sup></p></div>' for i,f in enumerate(summary["findings"],1))
    cards="".join(f'<div class="kpi"><div>{E(k["label"])}</div><strong>{E(metric_text(report,k))}</strong><p>{E(k["comparison"])}</p></div>' for k in report.get("kpis",[]))
    first=f'<p class="eyebrow">管理摘要</p><h1>{E(m["title"])}</h1><p class="meta">{E(m["scope"])}<br>分析期间：{E(m["period"])}；数据截至：{E(m["data_as_of"])}</p><p class="question">本报告回答：{E(m["main_question"])}</p><div class="bottom-line"><h2>核心判断</h2><p>{P(summary["bottom_line"])}</p></div><div class="findings">{findings}</div><div class="decision"><h2>优先行动</h2><p>{P(summary["next_step"])}</p></div><p class="caveat"><b>判断边界：</b>{P(summary["critical_limit"])}</p><div class="kpis">{cards}</div>'
    pages=[page(first,1,total)]
    for index,s in enumerate(report["sections"],2):
        paras=''.join(f'<p>{P(p)}</p>' for p in s['paragraphs'])
        fig=chart_svg(s['chart'],report,s['id']) if 'chart' in s else ''
        tb=table_html(s['table'],report) if 'table' in s else ''
        content=f'<div id="{E(s["id"])}"><p class="eyebrow">{E(s["eyebrow"])}</p><h2 class="section-title">{E(s["headline"])}</h2><div class="narrative">{paras}</div>{fig}{tb}<p class="implication"><b>业务含义：</b>{P(s["implication"])}</p><p class="caveat"><b>解读边界：</b>{P(s["limitation"])}</p><p class="source">资料来源：{source_refs(s["source_ids"])}。口径及合成数据说明见末页。</p></div>'
        pages.append(page(content,index,total))
    if report['actions']:
        cards=[]
        for i,a in enumerate(report['actions'],1):
            st="建议方案，尚未批准" if a["status"]=="proposed" else "已批准"
            cards.append(f'<article class="action"><p class="action-status">行动 {i:02d} · {st}</p><h3>{E(a["title"])}</h3><p>{E(a["rationale"])}</p><dl><dt>责任／时间</dt><dd>{E(a["owner"])}；{E(a["timing"])}</dd><dt>验证指标</dt><dd>{E(a["success"])}</dd><dt>推进门槛</dt><dd>{E(a["gate"])}</dd><dt>关键依赖</dt><dd>{E(a["dependencies"])}</dd></dl></article>')
        intro = '下列动作为合成案例演示，不代表真实组织的承诺、预算或批准。' if m['synthetic'] else '建议与已批准事项分别标注；执行前确认责任、资源、验证指标与推进条件。'
        pages.append(page('<p class="eyebrow">实施安排</p><h2 class="section-title">优先行动与推进条件</h2><p>'+E(intro)+'</p>'+''.join(cards),len(pages)+1,total))
    entries=''.join(f'<article class="source-entry" id="src-{E(s["id"])}"><h3>{E(s["id"])}　{E(s["title"])}</h3><p>{E(s["period"])}<br>{E(s["note"])}</p><p class="source">复核位置：{E(s["locator"])}</p></article>' for s in report['sources'])
    methods='<h3>计算与使用边界</h3><p>各图表和表格中的单位、期间与限定条件属于解读前提。详细来源与定义以上述记录为准；未提供、待更新与零值分别处理。</p><p>程序检查仅覆盖数据契约、来源引用与已声明的算式，不认证来源真实性、自然语言论证或因果关系。建议不等于已批准事项。</p>'
    pages.append(page('<p class="eyebrow">复核说明</p><h2 class="section-title">数据、口径与适用范围</h2>'+entries+methods,len(pages)+1,total))
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:; font-src \'none\'; base-uri \'none\'; form-action \'none\'"><title>'+E(m['title'])+'</title><style>'+css+'</style></head><body><main>'+''.join(pages)+'</main></body></html>'


def write_new(path: Path, content: str, force: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not force:
        with path.open('x',encoding='utf-8') as f:f.write(content)
    else:
        temp=path.with_name(path.name+'.tmp')
        with temp.open('x',encoding='utf-8') as f:f.write(content)
        temp.replace(path)


def main() -> int:
    p=argparse.ArgumentParser(description="中文报告数据校验及离线HTML渲染")
    sub=p.add_subparsers(dest='command',required=True)
    v=sub.add_parser('validate');v.add_argument('input',type=Path);v.add_argument('--editorial',action='store_true')
    r=sub.add_parser('render');r.add_argument('input',type=Path);r.add_argument('--output',required=True,type=Path);r.add_argument('--force',action='store_true');r.add_argument('--layout',choices=['report','slides'],default='report')
    args=p.parse_args()
    try:
        data=read_json(args.input);result=validate(data,getattr(args,'editorial',False))
        if not result['valid']:
            print(json.dumps(result,ensure_ascii=False,indent=2));return 2
        if args.command=='render':
            write_new(args.output,render(data,args.layout),args.force);result['output']=str(args.output)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (OSError,ValueError,TypeError,KeyError) as e:
        print(f'失败：{e}',file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
