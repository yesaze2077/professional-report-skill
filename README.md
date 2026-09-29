# Professional Report Skill v3.3.0

作者：**yesaze** · 许可证：[MIT](LICENSE)

独立的中文专业报告 Skill，适用于经营诊断、市场与用户研究、实验复盘及项目风险报告。以具体判断、可追溯证据和充分论证组织内容；同一份指标、口径与来源可生成适合连续阅读的 **A4 PDF 报告**及自包含的 **16:9 HTML 完整论证幻灯**。不依赖外部服务或密钥。

## 功能

- **两种成品深度：** 简报通常 5–12 页；完整版适用于 20–60 页级全面诊断，实际页数由内容决定。旧 `standard` 数据文件仍可读取。
- **完整结构：** 完整版包含封面、目录、管理摘要、分章正文、附录／方法与来源、封底。A4报告和幻灯采用独立页计划，不要求一页对应一页。
- **具体标题与论证：** 分析标题优先交代对象、变化、幅度和基准；每项重要判断保留证据、解释、实质性替代原因、业务含义与适用边界。证据不足时收窄判断，不补造数字。
- **共享证据：** 报告JSON中的指标、来源和可选证据点供两版引用，避免维护两套数值。编辑审查检查引用与部分写作缺口；程序无法认证来源真实性、因果关系或论证语义。
- **图文呈现：** A4版将关键图表、流程和解释放在对应论证位置；HTML幻灯按一个主要判断及视觉证据组织，覆盖全部重要分析单元，长表进入可跳转附录。支持目录跳转、键盘翻页、页码和16:9打印。截图须获得使用权并脱敏；合成界面明确标识。
- **数值与比例：** 关键百分比在分母有效时展示具体分子／分母，关键规模在有意义时补同口径占比；可比变化说明基期、本期、绝对变化和相对变化。

生成、重构、审查是工作模式；简报、完整版是成品深度。重构不发明分析，审查不擅自改动原件。证据缺口会标记为 `partial`。

## 安装到 Codex

将整个仓库复制或克隆到用户级 Skill 目录，目录名保持 `professional-report-skill`，然后在新对话中调用 `$professional-report-skill`。默认目录通常是 `~/.codex/skills/`；若设置了 `CODEX_HOME`，使用其 `skills/` 子目录。安装前检查同名目录并备份旧版，保留 `SKILL.md`、`standards/`、`templates/`、`catalog/`、`schemas/` 和 `scripts/`。具体客户端规则以其当前说明为准。

单次任务也可提供 [完整规范 Markdown 版](专业报告规范_完整版.md)；这不等于永久安装。

## 运行示例

核心校验和HTML渲染需要 Python 3.10 或以上，使用标准库，无需API、密钥或网络。先校验，再渲染：

```bash
python3 scripts/report_tools.py validate examples/comprehensive-report.json
python3 scripts/report_tools.py validate examples/comprehensive-report.json --editorial
python3 scripts/report_tools.py render examples/comprehensive-report.json --layout report --output full-report.html
python3 scripts/report_tools.py render examples/comprehensive-report.json --layout slides --output full-slides.html
python3 -m unittest discover -s tests -v
```

`--layout report` 是默认值，输出可打印的A4 HTML。若本机已有Playwright和Chromium，可导出PDF；仓库不自动下载浏览器：

```bash
python3 scripts/export_pdf.py full-report.html --output full-report.pdf
```

`--layout slides` 使用JSON中显式的 `presentation.slides`，生成单文件离线HTML；A4版使用 `composition.pages`。旧 v3.2 JSON 继续通过标准校验，但没有幻灯计划时不能生成幻灯。编辑审查是额外质量门槛，不改变旧文件的基础校验兼容性。同名输出文件默认拒绝覆盖；确认可替换时使用 `--force`。

## 示例与文档

- [SKILL.md](SKILL.md)：Agent入口与按需阅读路径。
- [完整规范阅读版](专业报告规范_阅读版.html) 和 [Markdown版](专业报告规范_完整版.md)。
- [完整版合成数据](examples/comprehensive-report.json)、[A4 PDF](examples/comprehensive-report.pdf)、[A4 HTML](examples/comprehensive-report.html) 与 [16:9 HTML幻灯](examples/comprehensive-slides.html)。示例展示同一套合成证据的两种完整成品。
- [简报合成示例](examples/demo-report.pdf) 和 [HTML版](examples/demo-report.html)。
- [交付检查表](qa/checklist.md)、[行为验收用例](qa/regression-cases.md) 和 [版本记录](CHANGELOG.md)。

所有示例经营数字、界面和组织均为**合成内容**，不代表任何真实店铺。模拟界面不能作为真实业务证据。参考渲染器的图型实现范围以 [图表目录](catalog/charts.json) 和实际程序为准；其他视觉形式须由合适工具制作并另行核对。

## 隐私与质量边界

公开内容不得包含真实业务数据、个人信息、凭据、私有链接、本地路径或内部敏感材料。发布前检查文本、JSON、HTML、PDF可复制文字及属性、图片和压缩包；截图须核对授权、时间、语境、遮盖效果及元数据。本包不上传用户材料，HTML参考输出不依赖远程脚本或跟踪服务。

结构校验、编辑审查、算术检查和隐私扫描均有边界；最终仍须人工逐项核对来源、口径、标题与论证，并逐页检查A4打印与全部幻灯在演示尺寸、窄屏下的可读性。

本项目采用 [MIT许可证](LICENSE)。第三方商标、字体和出版物不随包授权；本Skill与任何咨询机构无隶属或认证关系。
