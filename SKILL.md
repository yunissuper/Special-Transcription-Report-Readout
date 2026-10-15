---
name: spatial-transcriptomics-report-readout
description: >-
  End-to-end Visium HD / Visium spatial-transcriptomics report-building skill.
  Turns Space Ranger outputs into a disease-aware cell-type annotation, then
  packages the result as a stakeholder-ready Chinese HTML report and a
  lobby/leader PPT deck. Covers QC vs industry ranges, cell segmentation QC,
  reference-based consensus annotation, 8 µm bin RCTD cross-validation,
  immune / TME composition, tumour-candidate evidence rules, descriptive
  two-sample comparison, and downstream-experiment recommendations (spatial
  proteomics first).
  触发词：空间转录组、空转、Visium HD、Space Ranger、细胞注释、注释报告、
  生信解读报告、单细胞空间、deconvolution、RCTD、PPT 报告、HTML 报告.
version: 1.0.0
author: yunis
tags: [spatial-transcriptomics, visium-hd, space-ranger, cell-annotation, rctd, reporting, ppt, html]
---

# 空间转录组解读报告 Skill

把一个 Visium HD / Visium 的空间转录组项目，从 **Space Ranger 结果** 一路做到
**面向客户 / 领导的 HTML 报告 + PPT**。核心价值不是“再跑一遍流程”，而是把生信结果
翻译成**非专业人士能看懂、能决策**的结论，并且**每个数字都可追溯**。

> 适用触发：用户给了 Space Ranger `outs/` 目录、或提到“空转/Visium/空间转录组”，
> 想要“注释一下 / 出个报告 / 做个 PPT 汇报”。

---

## 0. 这个 Skill 解决什么问题

空间转录组常规交付的两个痛点：

1. **注释口径不统一** —— 同一份数据，用不同参考、不同阈值，恶性判定天差地别。
   本 skill 用「疾病参考 + marker 程序 + UCell」三证据共识，并全程保留
   **候选（candidate）** 措辞，绝不把计算推断说成病理确诊。
2. **报告不好读** —— 生信图表直接堆给领导看不懂。本 skill 的 HTML/PPT 采用
   **结论优先**结构：每页先给结论，再给证据；先讲“能回答什么”，再讲“怎么做出来的”。

---

## 1. 完整能力地图（六段式流水线）

```
[1] 数据接入 & 审计        →  matrix / GeoJSON / Azimuth 对应率、UMI/基因 QC
        │
[2] 细胞级注释              →  疾病参考 mapping + UCell marker + 共识 + A/B/C 分级
        │
[3] 8 µm bin 独立验证        →  RCTD 去卷积，与 cell 注释大类一致率做闸门
        │
[4] 结果整合                →  单一 report_data.json（所有报告的唯一数据源）
        │
[5] 报告生成                →  中文 HTML（自包含单文件）+ PPT（结论优先）
        │
[6] 质量校验                →  数字可追溯、无禁用术语、无越界、无 CRC 残留
```

每个阶段的产物都落盘到项目目录，最终 HTML/PPT **只从 `report_data.json` 读数**，
避免“报告里的数字和图对不上”。

---

## 2. 推荐项目目录

```text
<project_root>/
├── inputs_readonly/            # 原始 FASTQ / 图像 / reference（只读符号链接）
├── baseline_readonly/          # Space Ranger outs / 下游结果（只读符号链接）
├── annotation/
│   ├── references/             # 公开参考图谱 + manifest.tsv（来源/版本/校验和）
│   ├── cell_level/             # cell-level 注释 + 可视化脚本
│   └── bin8um_rctd/            # RCTD pilot / full / 聚合脚本
├── results/
│   ├── tables/                 # 结构化结果（tsv/gz/json）
│   └── figures/                # 所有图（png）
├── report/
│   ├── collect_results.py      # ★ 汇总 → report_data_current.json
│   ├── build_leader_report.py  # ★ 生成单文件 HTML
│   └── report_leader.html
└── ppt/
    └── src/build_ppt_leader.py # ★ 生成 PPTX
```

本 skill 的脚本都支持 `--root <project_root>`，不假设任何固定路径。

---

## 3. 环境

| 用途 | 解释器 / 环境 |
|------|--------------|
| RCTD / spacexr | base 环境 `Rscript`（`library(spacexr)` 可加载即可） |
| SingleR / UCell | 独立 conda env（R 4.3.3，含 `scrapper`） |
| Python（报告/PPT） | 任意 3.9+，需 `pandas pillow jinja2 python-pptx matplotlib` |

> 两个 R 环境分开的原因：`spacexr` 依赖的 R 版本与 `scrapper`/`SingleR` 常常冲突。
> 用 `provenance/software_versions.tsv` 记录实际版本，不要写死在文档里。

安装 Python 依赖：
```bash
pip install pandas pillow jinja2 python-pptx matplotlib scipy
# PPT 渲染校验（可选）
sudo apt-get install -y libreoffice poppler-utils  # soffice + pdftoppm
```

---

## 4. 阶段详解

### 阶段 1 — 数据接入 & 审计

输入：Space Ranger `outs/`（含 `segmented_outputs/`、`binned_outputs/`、`spatial/`）。

必须核对的**对应率闸门**（任一 <99% 先解决映射，再往下走）：

- `filtered_feature_cell_matrix.h5` 的 barcode ↔ cell/nucleus GeoJSON
- matrix barcode ↔ Space Ranger Azimuth `cell_types.csv`
- 8 µm binned matrix ↔ 2 µm 坐标（用于后续密集投影）

产出 `results/tables/baseline_audit_summary.tsv`：每样本的 cells / genes /
median UMI / median genes / 低计数比例 / Azimuth 中位置信度。

同时从 `metrics_summary.csv` 抽取**测序层面**指标用于“数据质量 vs 行业范围”：
Valid Barcodes、Valid UMI、Q30、Reads Mapped to Probe Set、Sequencing Saturation、
Genes Detected。这些是给领导看“数据好不好”的硬指标。

### 阶段 2 — 细胞级注释（本 skill 的核心）

三级词典：`compartment → major_cell_type → subtype/state`。

**三证据**：

1. **疾病特异性参考**（reference mapping，SingleR / Seurat label transfer）
   - 选择与组织**疾病身份匹配**的参考。这是最容易出错的地方：
     肝原发肿瘤必须用肝癌参考（HCC/ICC），**不能**用 CRC/CRLM 参考，
     否则正常肝上皮会被投影成 “CRC malignant”。
   - 参考写入 `annotation/references/manifest.tsv`：来源、版本、accession、
     下载日期、许可证、校验和。
2. **UCell marker 程序**：~35 个 identity/state 程序（T/NK、B/Plasma、
   Macrophage、CAF、EMT、Hypoxia、Angiogenesis…）。按 top score 与 margin 分 A/B/C。
3. **共识**：reference major 需 compartment 一致且 margin 达阈值；
   恶性候选需**上皮支持 + 组织特异肿瘤身份 + ≥1 套疾病参考**，仅 EPCAM/KRT
   等泛上皮信号不足以判恶性。

**置信度分级**：

| 级别 | 条件 |
|------|------|
| Tier A | 主预测 ≥0.70 且第二证据一致，无强负 marker |
| Tier B | 预测 0.50–0.70，或仅一项独立证据 |
| Tier C / Unknown | 预测 <0.50、低 UMI、方法冲突或 marker 不支持 |

> **Unknown 不是失败**，是对低质量 / 证据冲突的保守保留。不要为提高注释率强制赋标签。

**恶性措辞红线**：无病理 ROI / CNV 时，一律表述为
“**组织名 + epithelium candidate**”（如 `liver cancer epithelium candidate`），
亚型（HCC vs ICC）未定时显式标注“待病理确认”。

### 阶段 3 — 8 µm bin RCTD 独立验证

RCTD（spacexr，doublet mode）作为**独立**去卷积方法交叉验证注释：

```bash
# pilot：小样本验证参考 / 基因交集 / 参数（务必显式给大核数！）
Rscript annotation/bin8um_rctd/run_rctd_pilot.R \
  <ref.rds> <bins8um.h5> <positions.tsv> <cell_type_col> <out_prefix> [n_bins] [seed] [umi_min] [max_cores]

# full：分块全量
Rscript annotation/bin8um_rctd/run_rctd_full_chunked.R \
  <pilot.rctd.rds> <bins8um.h5> <positions.tsv> <out_dir> <sample> [chunk_size] [max_cores] [umi_min]
```

**发布闸门**：

- reject > **30%** → 不发布细粒度 RCTD 结论，回退 major compartment / Unknown；
- 与 segmented-cell compartment 一致率 < **70%** → 同上。

保存 singlet/doublet/reject、first/second type、weights、confidence。
**8 µm bin 永远不等于单细胞**，RCTD 权重只用于组成与一致性验证。

### 阶段 4 — 结果整合

`scripts/collect_results.py --root <project_root>` 汇总上述所有 tsV/JSON 到
**唯一** `report/report_data_current.json`。报告与 PPT 都只读这个文件。

### 阶段 5 — 报告生成

- **HTML**：`scripts/build_html_report.py` → 单文件自包含（图片 base64 内嵌），
  学术冷静配色，适合双击查看 / 微信发送 / 网站托管。
- **PPT**：`scripts/build_ppt_leader.py` → 16:9，结论优先，每页“先答案后证据”。

两份报告结构一致（见第 5 节模板），保证口径统一。

### 阶段 6 — 质量校验

`scripts/validate_report.py` 自动检查：

- 页数 / 图数在预期范围；
- 所有数字与 `report_data.json` 一致；
- 无禁用残留术语（模板项目自带的、与本项目无关的板块）；
- **肝脏页面不得出现 CRC 系词汇**（防“参考用错”复发）；
- 无形状越界 / 空页。

---

## 5. 报告结构模板（结论优先）

领导版报告按“**这是什么 → 怎么看 → 可不可信 → 结果 → 单位与限制**”组织：

1. 封面：一句话结论（数据质量 + 候选数 + 建议）
2. 一页执行摘要：5 个关键问题（能不能用 / 切得对不对 / 肿瘤在哪 / 免疫怎样 / 能否往下做）
3. 技术背景（通俗版）：传统病理 vs 空间转录组
4. 数据质量（一）测序层：各项 vs 行业常见范围
5. 数据质量（二）细胞层：细胞数 / 中位基因 / 对应率 + QC 分布图
6. 组织结构：HE 原图
7. 细胞类型地图：**一样本一页，3 图横排**（分区 / 主要类型 / 恶性证据），图例短名放图下
8. 肿瘤候选定位：8 µm 聚类组成图 + 富集区域
9. 候选证据规则：为什么只能叫“候选”
10. 免疫浸润：免疫占比 + 主要免疫类型
11. 免疫亚型：CD8 / Treg / NK / 耗竭 / 巨噬极化
12. 微环境状态：EMT / Hypoxia / CAF / 增殖
13. 风险 / 阶段谨慎解读
14. 下游可行性：四维验收
15. **实验建议：空间蛋白组优先**
16. 独立验证（RCTD）
17. 局限
18. 下一步行动

---

## 6. 常见坑（血泪总结）

| 坑 | 后果 | 规避 |
|----|------|------|
| **参考与疾病身份不匹配** | 肝组织被判成 CRC 恶性 | 先确认样本是原发还是转移、什么癌种，再选参考 |
| 图例用整句英文 | 图缩到 PPT 里看不清 | 图例改**短名**，放图**下方**，每张图单独出图 |
| 把 8 µm bin 说成细胞 | 科学性错误 | 全文统一“segmented cell”为主，“8 µm bin”仅验证 |
| 无病理就下恶性结论 | 越界 | 一律 “candidate”，亚型未定显式标注 |
| 单样本做显著性检验 | 统计错误 | 单对样本只做**描述性**比较 |
| PPT 数字与报告不符 | 可信度崩 | 全从 `report_data.json` 取数 |
| R 环境混用 | spacexr / SingleR 冲突 | 两个 Rscript 分开，记录版本 |

---

## 7. 快速开始

```bash
# 1. 汇总结果
python scripts/collect_results.py --root /path/to/project

# 2. 生成单文件 HTML 报告
python scripts/build_html_report.py --root /path/to/project --out report/report_leader.html

# 3. 生成 PPT
python scripts/build_ppt_leader.py --root /path/to/project --out ppt/output/report.pptx

# 4. 校验
python scripts/validate_report.py --root /path/to/project
```

`demo/` 目录含最小可运行示例，`templates/` 含报告配色与文案模板。
详细开发说明见 `DEVELOPMENT.md`。
