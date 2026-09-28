# Professional Report Skill v3.2.0

作者：**yesaze** · 许可证：[MIT](LICENSE)

一个独立的中文专业报告 Skill，用于生成、重构或审查经营诊断、市场与用户研究、实验复盘、项目风险等报告。默认以问题、证据和决策组织内容，保留来源、指标口径和结论边界。

## v3.2 能做什么

- **两种成品模式**：简报通常 5–12 页；完整版通常 20–60 页，适合跨模块经营现状诊断与策略建议。页数是规划参考，按证据增减，不凑页。旧文件的 `standard` 深度继续兼容。
- **完整报告版式**：完整版含封面、目录、管理摘要、正文、附录／方法与来源、封底。多页管理摘要呈现关键数据、全部重要发现、优先待办及影响判断的限制。
- **数值与比例双显**：关键百分比在分母有效时显示具体数量／基数；关键绝对值在结构或影响范围值得说明时补充同口径占比。可比变化说明基期、本期、绝对变化及相对变化；无效分母不强行计算。
- **图文编排**：按论点选择图表、经许可且脱敏的截图、流程图和重点框。页面有主旨、视觉重心、邻近解释和可追溯来源，避免文字与数字堆砌。
- **验证与渲染**：提供报告 JSON 契约、校验器、HTML 参考渲染器、可选 PDF 导出和合成示例。参考渲染器支持四类基础图表、合成界面示意和路径流程图；真实截图及其他图型需使用合适的编辑工具并完成授权、来源与隐私核对。

生成、重构、审查是工作模式；简报、完整版是成品模式。重构不发明分析，审查不擅自修改原件。证据缺口会标记为 `partial`，不会被版式掩盖。

## 安装到 Codex

将**整个仓库目录**复制或克隆到 Codex 的用户级 Skill 目录，目录名保持 `professional-report-skill`，然后在新对话中调用 `$professional-report-skill`。默认目录通常是 `~/.codex/skills/`；若设置了 `CODEX_HOME`，请使用其 `skills/` 子目录。安装前检查是否已有同名目录，先备份旧版，勿直接覆盖。确认 `SKILL.md`、`standards/`、`templates/`、`catalog/` 均可读取。具体客户端的安装规则以该客户端当前说明为准。

已有 v3.1 可保存在单独的备份目录。数据契约继续识别 `brief`、`standard`、`comprehensive`；制作新版完整报告时使用 `meta.depth=comprehensive`、`meta.format_mode=full`，并提供封面元信息、`composition.pages` 和 `coverage`。

单次任务也可直接提供 `专业报告规范_完整版.md`，要求按其中规则工作；这不等于永久安装。

## 示例与文档

- [SKILL.md](SKILL.md)：Agent 入口与按需阅读路径。
- [完整规范阅读版](专业报告规范_阅读版.html) 和 [Markdown 版](专业报告规范_完整版.md)：面向人的规范。
- [45 页完整版合成示例](examples/comprehensive-report.pdf) 与 [HTML 版](examples/comprehensive-report.html)：封面、目录、多页管理总览、章节诊断、视觉示意、行动、来源与封底。
- [简报合成示例](examples/demo-report.pdf) 与 [HTML 版](examples/demo-report.html)：较短的阅读路径。
- [交付检查表](qa/checklist.md)、[行为验收用例](qa/regression-cases.md) 与 [版本记录](CHANGELOG.md)。

所有示例经营数据与界面均为**合成内容**，不代表任何真实店铺或组织；合成截图不能被引用为真实业务证据。示例版式展示制作方法，不证明报告中的业务结论适用于其他项目。

## 本地验证与渲染

核心校验和 HTML 渲染需要 Python 3.10 或以上，仅依赖标准库，不需要 API、密钥或网络：

```bash
python scripts/report_tools.py validate examples/comprehensive-report.json
python scripts/report_tools.py render examples/comprehensive-report.json --output full-report.html
python -m unittest discover -s tests -v
```

在已有 Playwright 和 Chromium 的环境中，可将 HTML 导出 PDF；本仓库不自动下载浏览器：

```bash
python scripts/export_pdf.py full-report.html --output full-report.pdf
```

同名输出文件默认拒绝覆盖；确认是可替换的本次生成物后才使用脚本的 `--force` 选项。最终需人工核对来源、计算、论证和实际页面；自动检查通过不等于事实、因果或隐私审计通过。

## 隐私与发布边界

公开内容不得包含真实业务数据、个人信息、凭据、私有链接、本地路径或内部敏感材料。截图需核对使用权、采集时间、裁剪语境、隐藏信息和脱敏；PDF 属性、图片元数据、JSON、注释和仓库历史也属于检查范围。本包不上传用户材料，HTML 参考输出不依赖外部脚本或跟踪服务。使用者处理真实数据时应遵守其授权和适用的隐私要求。

本项目采用 [MIT 许可证](LICENSE)。第三方商标、字体和出版物不随包授权；本 Skill 与任何咨询机构无隶属或认证关系。
