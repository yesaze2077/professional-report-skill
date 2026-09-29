"""Create an explicit, reviewable slide plan from the shared report objects.

The plan references section, evidence, action and source IDs. It never copies
metric values or source prose into a second presentation data set.
"""
from __future__ import annotations


def make_slide_plan(report: dict) -> dict:
    pages = report["composition"]["pages"]
    chapter_by_section = {
        sid: page["chapter"]
        for page in pages if page["kind"] == "content"
        for sid in page["section_ids"]
    }
    slides = [
        dict(id="SL_cover", kind="cover", chapter="封面", title=report["meta"]["title"]),
        dict(id="SL_toc", kind="toc", chapter="目录", title="阅读路径与章节索引"),
        dict(id="SL_summary", kind="summary", chapter="管理摘要", title="增长24万美元，经营贡献减少3.6万美元"),
    ]
    visual_pages = [page for page in pages if page["kind"] == "visual"]
    for section in report["sections"]:
        sid = section["id"]
        chapter = chapter_by_section[sid]
        for phase in ("evidence", "reasoning"):
            entry = dict(id=f"SL_{sid}_{phase}", kind="analysis", chapter=chapter,
                         title=section["headline"], section_id=sid, phase=phase)
            if phase == "evidence":
                entry["evidence_ids"] = [p["id"] for p in section["evidence_points"]]
            slides.append(entry)
        if sid in {"D08", "D09"}:
            for page in visual_pages:
                if (sid == "D08" and page["visual_kind"] == "process") or (sid == "D09" and page["visual_kind"] == "synthetic_ui"):
                    slides.append(dict(id=f"SL_{page['id']}", kind="visual", chapter=chapter,
                                       title=page["visual_title"], visual_page_id=page["id"]))
    action_ids = [action["id"] for action in report["actions"]]
    for start in range(0, len(action_ids), 3):
        ids = action_ids[start:start+3]
        slides.append(dict(id=f"SL_actions_{start//3+1}", kind="actions", chapter="行动与验收",
                           title=f"行动 {ids[0]}—{ids[-1]}：交付、责任与推进门槛", action_ids=ids))
    for section in report["sections"]:
        if "table" in section:
            rows = section["table"]["rows"]
            for start in range(0, len(rows), 9):
                part = start//9+1
                slides.append(dict(id=f"SL_appendix_{section['id']}"+(f"_{part}" if part>1 else ""),
                                   kind="appendix", chapter="数据附录",
                                   title=f"{section['id']}｜详细指标与口径"+(f"（{part}）" if part>1 else ""),
                                   section_id=section["id"], row_start=start, row_end=min(start+9,len(rows))))
    source_ids = [source["id"] for source in report["sources"]]
    for start in range(0, len(source_ids), 4):
        ids = source_ids[start:start+4]
        slides.append(dict(id=f"SL_sources_{start//4+1}", kind="sources", chapter="方法与来源",
                           title=f"来源索引 {ids[0]}—{ids[-1]}", source_ids=ids))
    slides.append(dict(id="SL_back", kind="back", chapter="封底", title="结束与使用边界"))
    return {"slides": slides}
