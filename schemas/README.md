# 报告数据契约

`report.schema.json`是参考渲染器的严格契约，不是所有业务报告必须输出的唯一格式。原始度量存于metrics，图表及数值表格只引用metric_id，避免图表和文字各抄一份数字。

比例原值使用0—1；百分比显示scale=0.01、suffix="%"。金额原值以基本货币单位存储；万美元显示scale=10000。百分点计算结果本身以百分点为单位，显示scale=1。各单位由作者明确定义，脚本不会猜测。

checks支持六种无代码执行的运算：sum、difference、ratio、relative_change、pp_change、multiply。`inputs`为数值ID，`result_metric`为应匹配的结果ID；`tolerance`为原始单位绝对容差。ratio的前两个输入为分子、分母；relative_change顺序为本期、基期；difference和pp_change顺序也是本期、基期。

来源是否真实、因果是否成立、自然语言中的数字是否都与数据对应仍需人工复核。校验器不会执行SQL、公式字符串、HTML、网页内容或任意Python。

图型目录中的“guidance_only”不是此schema可直接接受的图型；不要把尚未实现图型写入chart.type。人工或其他工具使用该方法不受此参考渲染器限制。

`unit="比例"`专指有界占比或转化率，原值必须处于0至1。相对增幅使用“相对变化率”，净增量贡献使用“净增量份额”，两者允许负数或大于1；显示百分比仍使用scale=0.01。单位名称及计算语义不得混淆。

## v3.2：两种成品模式与显式长报告结构（向后兼容）

`meta.depth`可为brief、standard、comprehensive；旧文件不带该值时沿用旧渲染。comprehensive必须包含`composition`与`coverage`。

`meta.format_mode` 可为 `brief` 或 `full`。完整版还需 `audience`、`author`、`report_date`、`confidentiality`；旧报告未提供 `format_mode` 时继续使用原摘要优先的校验路径。

`composition.pages` 为有序页面数组：id、kind、chapter、label 必填。kind 可为 cover、toc、summary、content、visual、actions、sources、back。完整版要求封面、目录开篇，目录后有唯一管理摘要，封底收尾；正文、行动和来源各须存在。content、actions、sources 分别通过 section_ids、action_ids、source_ids 选取原对象。视觉证据页提供 `visual_kind`、标题、说明及来源 ID；流程图提供 `steps`，可选 `readouts` 与解释。所有正文单元、行动详情与来源必须恰好被选取一次。总览内的短引用不是重复完整正文。页面总数由该数组决定，不固定页数。

`coverage`记录domain、status、section_ids、explanation、action_ids。status为covered、partial、missing、not_applicable。部分覆盖与已覆盖都需有正文位置；缺失或不适用仍要有解释。字段、引用和覆盖状态检查不等于专业判断已经充分。

参考渲染器将每个计划项作为一页，不自动猜测分页。若一项过多，增加计划项并拆分内容；打印后必须检查PDF页数、页脚及目录对应。没有composition的旧路径仍适用于简短示例，不适合直接承载大量行动和来源。
