# DEVELOPMENT

面向要改造这套脚本的人：数据契约、扩展点、渲染校验流程。

---

## 1. 数据契约（谁读什么）

```
Space Ranger outs ─┐
                   ├─► [下游分析] ─► results/tables/*.tsv ─┐
参考图谱 + UCell ──┘                                     │
                                                          ▼
                          report/report_data_current.json  ←── collect_results.py
                                     │
                        ┌────────────┴────────────┐
                        ▼                         ▼
              build_html_report.py        build_ppt_leader.py
                        │                         │
                        ▼                         ▼
              report_leader.html            report.pptx
                        └────────────┬────────────┘
                                     ▼
                            validate_report.py
```

**唯一真源**：`report/report_data_current.json`。
两个生成器都只读它（外加 immune/subtype 两个 JSON 与原始 metrics_summary）。
永远不要把数字硬编码进 HTML/PPT 模板。

---

## 2. `report_data_current.json` 顶层字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `report_version` | str | 报告版本串（配置或 `--version`） |
| `generated_at` | str | 生成日期 |
| `audit` | list | 每样本 cells/genes/median UMI/median genes/低计数率 |
| `consensus_qc` | list | 每样本 `supported_fraction`、`malignant_candidates` |
| `marker_qc` / `mapping_qc` | list | marker 命中、cell→cluster 对应率 |
| `reference_summary` / `reference_manifest` | list | 参考来源/版本/校验和 |
| `dryrun` | dict | Snakemake 空跑摘要 |
| `rctd_summary` | dict | `{sample: {cell_compartment_agreement, singlet_fraction, eligible_bins, reject_fraction}}` |
| `major_tables` / `status_tables` / `tier_tables` | dict | `{sample: [rows]}` 主要类型/恶性状态/置信度 |
| `highlighted_clusters` | list | 候选富集或高置信 cluster |
| `all_cluster_labels` | list | 全部 8 µm cluster 标签 |
| `figures` | dict | 逻辑名 → 项目内相对路径 |

生成器通过 `figures` 见证图路径，通过 `audit`/`rctd_summary` 证数字——
**校验器也是这么核对 PPT/HTML 的**，所以字段名改动要同步三方。

---

## 3. 扩展点

### 3.1 换病种 / 换组织

改两处，不动脚本逻辑：

1. `report/report_config.json`：
   - `samples` / `display_names` / `sample_dirs`
   - `tissue_vocab`：定义“某术语只在某组织页出现”的守卫规则
2. `scripts/plot_consensus_panels.py` 顶部的 `*_LABELS` 字典：
   按该项目的 ontology 改短名（**这是唯一需要手改的“文案映射”**）。

### 3.2 加一页 / 改一页报告

HTML 与 PPT 各有一处对应结构（HTML 的 `<section id="sN">`，PPT 的 `new_slide(...)`）。
新增章节时：数据先进 `report_data_current.json`，再在两边渲染，最后在
`validate_report.py` 加一条 `required_fragments`。

### 3.3 换配色

`scripts/report_common.py` 顶部的调色板常量是唯一来源；
HTML 的 CSS 变量与 PPT 的 `RGBColor` 都从这些语义色衍生。
**保持低饱和**：深青灰主色 + 单一陶土强调色 + 米白底。

---

## 4. 校验流程

```bash
python scripts/validate_report.py --root <project>
```

闸门（任一失败退出码 1）：

- PPT 页数/图数在预期范围；无形状越界；无空页
- PPT 文本不含无关模板残留词（`CUT&Tag` 等）
- PPT 的关键数字（cells、RCTD 一致率）确实存在于 `report_data_current.json`
- 组织隔离守卫：某组织专页不得出现另一组织的参考词汇
- HTML：图片数、章节数达标；`<div>` 配平；正文非空

### 渲染抽查（可选但推荐）

```bash
soffice --headless --convert-to pdf --outdir /tmp <pptx>
pdftoppm -png -r 90 /tmp/report.pdf /tmp/page
# 抽查全部页面，重点人工核对 5 页以上
```

HTML 直接浏览器打开；大文件用 viewport 截图而非整页截图。

---

## 5. 已知约束

- `collect_results.py` 默认要求 `rctd_full_summary.json` 存在（发布闸门）。
  若项目确实没做 RCTD，把它从 `tables.rctd_summary` 指到任一存在的 JSON，
  或在 `build_*` 前手动补一个最小 summary——**不要**默默删掉校验。
- `plot_consensus_panels.py` 的坐标对应率低于 99% 会直接报错，
  这是有意的：先解决 ID 映射，再谈精细注释。
- 8 µm bin 永远不等于单细胞；RCTD 权重只用于组成与一致性验证。
