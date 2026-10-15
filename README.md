# Special-Transcription-Report-Readout

把一份 Visium HD / Visium 空间转录组项目，从 **Space Ranger 结果** 一路做到
**面向客户 / 领导的中文 HTML 报告 + PPT**。

核心价值不是“再跑一遍流程”，而是把生信结果翻译成**非专业人士能看懂、能决策**
的结论，并且**每个数字都可追溯**。

> 触发场景：你拿到了 Space Ranger `outs/` 目录、或提到“空转 / Visium / 空间转录组”，
> 想“注释一下 / 出个报告 / 做个 PPT 汇报”。

---

## 它能做什么

| 阶段 | 产物 |
|------|------|
| 1 数据接入 & 审计 | matrix/GeoJSON/Azimuth 对应率、UMI/基因 QC、测序指标 vs 行业范围 |
| 2 细胞级注释 | 疾病参考映射 + UCell marker 程序 + 共识 + A/B/C 置信度分级 |
| 3 8 µm bin 独立验证 | RCTD 去卷积，与 cell 注释大类一致率做发布闸门 |
| 4 结果整合 | 单一 `report_data_current.json`（所有报告的唯一数据源） |
| 5 报告生成 | 中文 **单文件 HTML**（图片内嵌，可双击/发送）+ **PPT**（结论优先） |
| 6 质量校验 | 数字可追溯、无禁用术语、无参考错用、无形状越界 |

**一句话原则**：最终 HTML/PPT 只从 `report_data_current.json` 读数，
避免“报告里的数字和图对不上”。

---

## 六段式流水线

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

---

## 快速开始

### 0) 环境

```bash
pip install pandas pillow jinja2 python-pptx matplotlib scipy
# 可选：PPT 渲染校验
sudo apt-get install -y libreoffice poppler-utils   # soffice + pdftoppm
```

RCTD 与 SingleR/UCell 建议分环境：

| 用途 | 解释器 |
|------|--------|
| RCTD / spacexr | 能 `library(spacexr)` 的 Rscript |
| SingleR / UCell | 另一个 R 环境（R 4.3.3 + scrapper） |
| Python（报告/PPT） | 任意 3.9+，含上表依赖 |

> 两个 R 环境分开的原因：`spacexr` 依赖的 R 版本与 `scrapper`/`SingleR` 常常冲突。

### 1) 先跑一遍 demo（10 秒，验证环境）

```bash
python demo/make_demo_data.py --root demo/project
PYTHONPATH=scripts python scripts/collect_results.py   --root demo/project
PYTHONPATH=scripts python scripts/build_html_report.py --root demo/project --out report/report_leader.html
PYTHONPATH=scripts python scripts/build_ppt_leader.py  --root demo/project --out ppt/output/report.pptx
PYTHONPATH=scripts python scripts/validate_report.py   --root demo/project
```

（`validate_report.py` 退出码 0 = 全部闸门通过。）

### 2) 接你自己的项目

```bash
cp templates/report_config.example.json <project>/report/report_config.json   # 改样本名/路径/文案
PYTHONPATH=scripts python scripts/collect_results.py   --root <project>
PYTHONPATH=scripts python scripts/build_html_report.py --root <project> --out report/report_leader.html
PYTHONPATH=scripts python scripts/build_ppt_leader.py  --root <project> --out ppt/output/report.pptx
PYTHONPATH=scripts python scripts/validate_report.py   --root <project>
```

---

## 推荐项目目录

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
│   ├── report_config.json      # ★ 唯一的项目化配置
│   ├── collect_results.py      # ★ 汇总 → report_data_current.json
│   ├── build_html_report.py    # ★ 生成单文件 HTML
│   └── report_leader.html
└── ppt/
    └── src/build_ppt_leader.py # ★ 生成 PPTX
```

本仓库的脚本都支持 `--root <project_root>`，不假设任何固定路径。

---

## 仓库结构

```text
scripts/     collect_results.py / build_html_report.py / build_ppt_leader.py
             validate_report.py / plot_consensus_panels.py / report_common.py
templates/   report_config.example.json + 词典模板（ontology / gmt / params）
demo/        make_demo_data.py + 生成的最小可运行示例
SKILL.md     ★ 完整能力说明（阶段详解、报告结构模板、常见坑）
```

---

## 报告结构（结论优先）

领导版报告按“**这是什么 → 怎么看 → 可不可信 → 结果 → 单位与限制**”组织：

1. 封面：一句话结论　2. 执行摘要（5 问）　3. 技术背景（通俗）　4-5. 数据质量（测序/细胞）
6. 组织结构 HE　7. 细胞类型地图（一样本一页 3 图横排）　8. 肿瘤候选定位
9. 候选证据规则　10. 免疫浸润　11. 免疫亚型　12. 微环境状态　13. 风险解读
14. 下游可行性　15. 实验建议（空间蛋白组优先）　16. 独立验证（RCTD）　17. 局限　18. 下一步

---

## 常见坑（血泪总结）

| 坑 | 后果 | 规避 |
|----|------|------|
| **参考与疾病身份不匹配** | 肝组织被判成 CRC 恶性 | 先确认样本癌种，再选参考 |
| 图例用整句英文 | 图缩到 PPT 里看不清 | 图例改**短名**，放图**下方** |
| 把 8 µm bin 说成细胞 | 科学性错误 | 全文以 “segmented cell” 为主 |
| 无病理就下恶性结论 | 越界 | 一律 “candidate” |
| 单样本做显著性检验 | 统计错误 | 单对样本只做**描述性**比较 |
| PPT 数字与报告不符 | 可信度崩 | 全从 `report_data.json` 取数 |
| R 环境混用 | spacexr / SingleR 冲突 | 两个 Rscript 分开，记录版本 |

详细阶段说明见 **[SKILL.md](SKILL.md)**；开发说明见 **[DEVELOPMENT.md](DEVELOPMENT.md)**。

---

## License

MIT — 见 [LICENSE](LICENSE)。
