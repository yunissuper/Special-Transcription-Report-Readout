#!/usr/bin/env python3
"""Leader-oriented Visium HD interpretative deck (Chinese, conclusion-first).

Built for a non-specialist decision maker. Every slide leads with the take-away,
then the evidence. It covers, in order:
  1  One-page executive summary (bottom line up front)
  2  Plain-language "what does this technology let us see"
  3  Data quality vs industry ranges (sequencing + cell level)
  4  Tissue structure / histology fit
  5  Cell-type map / does it match expected histology
  6  Where is the tumour (foci, size, burden)
  7  Why we only call them "candidates" (evidence rules)
  8  Immune cells present + is the composition abnormal
  9  T/NK + macrophage subtype detail and what it implies
 10  Tumour-microenvironment state programs
 11  Cautious read-out for stage/risk flags
 12  Is the data fit for downstream experiments (verdict)
 13  Recommended next experiments, with spatial proteomics first
 14  RCTD independent validation (trust backing)
 15  Limitations / boundaries
 16  Decision-ready next actions

sample_B is treated as primary liver cancer throughout (HCC/ICC undecided);
no CRC wording is used for liver.
"""
import json
import sys
from pathlib import Path

ROOT = Path("<PROJECT_ROOT>")
PPT_ROOT = ROOT / "ppt"
sys.path.insert(0, str(PPT_ROOT / "python_lib"))
sys.path.insert(0, str(PPT_ROOT / "vendor_snapshot"))

import build_report_ppt as kit
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from build_ppt_zh import (
    add_text, add_rect, add_header, add_note, add_bullets, add_metric, add_table,
    put_image, new_slide, pct, audit_by_sample, qc_by_sample, major_rows,
    NAVY, TEAL, CYAN, GOLD, PALE, PALE_TEAL, PALE_GOLD, WHITE, DARK, GRAY, RED, GREEN,
)

DATA_PATH = ROOT / "report/report_data_current.json"
IMMUNE_PATH = ROOT / "results/tables/cell_annotation/immune_tme_summary.json"
SUBTYPE_PATH = ROOT / "results/tables/cell_annotation/immune_subtype_summary.json"
OUTPUT_PATH = PPT_ROOT / "output/demo_current_zh.pptx"


def bullet_rows(data, sample, limit=6):
    rows = []
    for row in data["major_tables"][sample][:limit]:
        rows.append([row["major_cell_type"], f'{row["n_cells"]:,}', pct(row["fraction_of_all_cells"])])
    return rows


def build():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    immune = json.loads(IMMUNE_PATH.read_text(encoding="utf-8"))
    subtype = json.loads(SUBTYPE_PATH.read_text(encoding="utf-8"))
    colon = audit_by_sample(data, "sample_A")
    liver = audit_by_sample(data, "sample_B")
    colon_cons = qc_by_sample(data, "consensus_qc", "sample_A")
    liver_cons = qc_by_sample(data, "consensus_qc", "sample_B")
    colon_rctd = data["rctd_summary"]["sample_A"]
    liver_rctd = data["rctd_summary"]["sample_B"]

    prs = kit.create_deck()
    page = 0

    # ---------- 1 COVER ----------
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_rect(slide, 0, 0, 13.333, 7.5, NAVY)
    add_rect(slide, 0, 5.15, 13.333, 0.08, GOLD)
    add_text(slide, 0.8, 0.95, 11.7, 1.5, "两份临床组织切片的空间组学分析\n（sample_A 结肠 · sample_B 肝脏）", 33, True, WHITE)
    add_text(slide, 0.82, 2.55, 11.6, 0.5, "用一张切片同时看清：组织里有哪些细胞、它们长在哪个位置、肿瘤和免疫细胞怎么分布", 18, False, RGBColor(0xC9, 0xE5, 0xEF))
    add_rect(slide, 0.85, 3.35, 11.6, 1.15, RGBColor(0x1E, 0x4A, 0x75), True)
    add_text(slide, 1.15, 3.52, 11.0, 0.85,
             "一句话结论：两份切片数据质量合格、组织结构完整、细胞类型定位清晰，"
             "完全支持开展下游实验（建议优先做空间蛋白组）。两份组织都检出肿瘤性上皮候选："
             "结肠 2,349 个（2.9%）、肝脏 25,108 个（15.2%），肝脏样本为肝细胞谱系、HCC/ICC 亚型待病理确认。",
             16, True, WHITE)
    add_text(slide, 0.82, 4.85, 11.4, 0.6, "分析单位：分拣出的单细胞（segmented cells）为主，8 µm 网格用于空间验证", 13, False, RGBColor(0xD2, 0xDE, 0xE8))
    add_text(slide, 0.82, 5.5, 11.4, 0.6, f"生成日期：{data['generated_at']}｜结论为计算推断，最终诊断需病理/CNV 复核", 12, False, RGBColor(0xA9, 0xBF, 0xD0))

    # ---------- 2 ONE-PAGE EXEC SUMMARY ----------
    page += 1
    slide = new_slide(prs, "一页看懂：这次分析给了领导什么答案", "执行摘要", page)
    cards = [
        ("数据能不能用？", "能。测序与细胞层面均达标，注释 A/B 级支持率 84.5%（结肠）/ 76.9%（肝）。", GREEN),
        ("组织切得对不对？", "结构完整、细胞类型地图符合临床病理预期（结肠=上皮/间质/免疫；肝=肝实质为主）。", GREEN),
        ("肿瘤在哪里？", "结肠：3 个候选富集聚类、共 2,349 个候选（2.9%，多灶）；肝：1 个富集聚类、25,108 个候选（15.2%，大片连续）。", GOLD),
        ("免疫怎么样？", "结肠免疫活跃（30.4%），以浆细胞/B + 巨噬为主、T 细胞可测；肝相对免疫贫乏（13.2%），B 细胞相对突出。", GOLD),
        ("能往下做吗？", "能。建议下一步优先空间蛋白组验证候选区域与免疫微环境，再做病理/CNV 复核。", TEAL),
    ]
    for i, (title, body, color) in enumerate(cards):
        y = 1.15 + i * 1.06
        add_rect(slide, 0.55, y, 2.7, 0.86, color, True)
        add_text(slide, 0.7, y + 0.18, 2.4, 0.5, title, 16, True, WHITE, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
        add_rect(slide, 3.45, y, 9.35, 0.86, PALE, True)
        add_text(slide, 3.72, y + 0.10, 8.9, 0.66, body, 14.5, False, DARK, anchor=MSO_ANCHOR.MIDDLE)
    add_note(slide, "两例为独立肿瘤，不是配对原发—转移；所有恶性相关表述均为“计算候选”，需病理/CNV 正交验证。")

    # ---------- 3 PLAIN LANGUAGE: what does this technology see ----------
    page += 1
    slide = new_slide(prs, "先讲清楚：这项技术能在切片上“看到”什么", "背景（通俗版）", page)
    add_rect(slide, 0.55, 1.15, 5.9, 5.0, PALE, True)
    add_text(slide, 0.85, 1.35, 5.3, 0.5, "传统病理切片", 19, True, DARK)
    add_bullets(slide, 0.85, 1.95, 5.25, 3.0, [
        "染色后只能看到细胞“长什么样”（形态）",
        "谁是谁、在做什么，大多靠经验判断",
        "无法区分肿瘤细胞与反应性细胞的确切身份",
    ], 14.5)
    add_rect(slide, 6.85, 1.15, 5.9, 5.0, PALE_TEAL, True)
    add_text(slide, 7.15, 1.35, 5.3, 0.5, "本项目的空间转录组", 19, True, TEAL)
    add_bullets(slide, 7.15, 1.95, 5.25, 3.0, [
        "在切片每个位置测量“数万个基因的表达量”",
        "据此给每个细胞/位置标注身份（如肝细胞、T 细胞）",
        "同时保留它们在组织里的精确坐标",
        "→ 既能看“是什么”，也能看“在哪、和谁相邻”",
    ], 14.5)
    add_note(slide, "一句话：把“细胞身份”和“空间位置”两套信息拼在同一张切片上，这是传统染色做不到的。")

    # ---------- 4 DATA QUALITY: SEQUENCING ----------
    page += 1
    slide = new_slide(prs, "数据质量好不好？（一）测序层面：两项样本均达标", "数据质量", page)
    rows = [
        ["有效 Barcode（有效细胞索引）", "89.3%", "89.0%", "≥90% 为优；89% 合格", "合格"],
        ["有效 UMI（有效分子计数）", "99.9%", "99.9%", "≥99%", "优秀"],
        ["Q30（碱基测序质量）", "97.2–97.7%", "97.2–98.0%", "≥90%", "优秀"],
        ["比对到探针集比例", "98.7%", "98.7%", "FFPE 通常 80–95%", "优秀"],
        ["测序饱和度", "37.4%", "48.9%", "30–60% 常见，偏低=可加深测序", "合格（建议加深）"],
        ["检出基因数", "18,111", "18,102", "FFPE 探针面板内接近上限", "优秀"],
    ]
    add_table(slide, 0.55, 1.15, 12.25, 3.35, ["指标", "sample_A", "sample_B", "常见范围（Visium FFPE）", "判断"], rows, [2.7, 1.5, 1.5, 3.6, 1.4], 11.5)
    add_bullets(slide, 0.9, 5.05, 11.5, 0.85, [
        "解读：两个样本的测序质量属于“优良”水平；唯一注意点是测序饱和度偏低，意味着多加一些测序深度还能挖到更多信息（不影响当前结论）。",
    ], 14)
    add_note(slide, "指标来自 Space Ranger 官方 metrics_summary；判断标准按 Visium FFPE/HD 行业常见范围给出。")

    # ---------- 5 DATA QUALITY: CELL LEVEL ----------
    page += 1
    slide = new_slide(prs, "数据质量好不好？（二）细胞层面：数量充足、可用于下游", "数据质量", page)
    add_metric(slide, 0.55, 1.05, 2.9, 1.25, f'{colon["matrix_cells"]:,}', "colon 分拣单细胞数", TEAL)
    add_metric(slide, 3.65, 1.05, 2.9, 1.25, f'{liver["matrix_cells"]:,}', "liver 分拣单细胞数", CYAN)
    add_metric(slide, 6.75, 1.05, 2.9, 1.25, f'{colon["umi_median"]}', "colon 中位基因数/细胞", TEAL)
    add_metric(slide, 9.85, 1.05, 2.9, 1.25, f'{liver["genes_median"]}', "liver 中位基因数/细胞", CYAN)
    rows = [
        ["sample_A", "81,616", "375", "291", "15%", "1.0%", "1.0%", "合格，可用于下游"],
        ["sample_B", "164,905", "244", "186", "26%", "1.0%", "1.0%", "合格，细亚型解释保守"],
    ]
    add_table(slide, 0.55, 2.5, 12.25, 1.45, ["样本", "分拣单细胞", "中位 UMI/细胞", "中位基因/细胞", "UMI<100 比例", "与细胞轮廓对应", "与核轮廓对应", "综合判断"], rows, [1.5, 1.55, 1.5, 1.5, 1.45, 1.6, 1.5, 2.0], 10.5)
    add_text(slide, 0.9, 4.28, 11.5, 0.28, "细胞/核 QC 分布", 12, True, DARK)
    # QC distributions: 1961x729 aspect 2.69 -> w=5.5, h=2.04 (bottom 6.39 < note bar 6.55)
    put_image(slide, "results/figures/audit/cell_qc_distributions.png", 0.6, 4.35, 5.5, 2.04)
    add_bullets(slide, 6.55, 4.75, 6.2, 1.7, [
        "解读：两样本细胞数量充足、细胞/核轮廓对应率 100%，定位可靠；肝脏样本单个细胞表达深度略低，属 Visium HD 常见现象，不影响“看到哪些细胞类型”，只提示细亚型结论要保守。",
    ], 13)
    add_note(slide, "分拣单细胞（segmented cells）是主分析单位；8 µm 网格单元不能当单细胞看，只用于空间验证。")

    # ---------- 6 TISSUE STRUCTURE ----------
    page += 1
    slide = new_slide(prs, "组织结构清不清晰？两张 HE 图完整、可读", "组织结构", page)
    put_image(slide, "baseline_readonly/colon_spaceranger_outs/spatial/tissue_hires_image.png", 0.45, 1.05, 6.1, 5.3)
    put_image(slide, "baseline_readonly/liver_spaceranger_outs/spatial/tissue_hires_image.png", 6.85, 1.05, 6.1, 5.3)
    add_text(slide, 0.6, 6.42, 6.0, 0.35, "sample_A 原始 HE（空间转录组切片）", 12, False, GRAY, PP_ALIGN.CENTER)
    add_text(slide, 7.0, 6.42, 6.0, 0.35, "sample_B 原始 HE（空间转录组切片）", 12, False, GRAY, PP_ALIGN.CENTER)
    add_note(slide, "HE 图像完整、无大片缺失；下面几页会把“HE 上看到的结构”翻译成“细胞类型地图”来核对组织是否正常。")

    # ---------- 7 COLON TISSUE / CELL-TYPE MAP ----------
    page += 1
    slide = new_slide(prs, "结肠（sample_A）：结构完整、符合结肠病理预期", "组织与注释", page)
    panel_x = [0.95, 4.91, 8.87]
    panel_w, panel_h, panel_y = 3.5, 4.62, 0.88
    for x, suffix in zip(panel_x, ["_1_compartment", "_2_major", "_3_malignancy"]):
        put_image(slide, f"results/figures/cell_annotation/colon_consensus_panels{suffix}.png", x, panel_y, panel_w, panel_h)
    add_rect(slide, 0.9, 5.66, 11.55, 1.42, PALE, True)
    add_bullets(slide, 1.05, 5.72, 11.25, 1.32, [
        f'分区：间质 {pct(36935/81616)}（成纤维为主）+ 免疫 {pct(24790/81616)} + 上皮 {pct(6021/81616)} → 典型结肠“上皮-间质-免疫”结构，无大片缺失，切片完整可读。',
        f'类型：成纤维 {pct(30263/81616)}、浆细胞 {pct(8003/81616)}、巨噬 {pct(6081/81616)}、B 细胞 {pct(3362/81616)} 为背景主力；恶性上皮候选 2,349（2.9%）。',
        '定位：肿瘤候选富集于 3 个 8 µm 聚类（cluster 2/4/14），最大富集区候选占比 30.7%；候选散布于纤维/免疫背景，非弥漫全片。',
        '结论：组织与细胞地图符合结肠临床病理预期，数据支持下游实验；肿瘤呈多灶富集，建议病理框选确认边界。',
    ], 12)

    # ---------- 8 LIVER TISSUE / CELL-TYPE MAP ----------
    page += 1
    slide = new_slide(prs, "肝脏（sample_B）：肝实质为主、符合肝原发肿瘤背景", "组织与注释", page)
    for x, suffix in zip(panel_x, ["_1_compartment", "_2_major", "_3_malignancy"]):
        put_image(slide, f"results/figures/cell_annotation/liver_consensus_panels{suffix}.png", x, panel_y, panel_w, panel_h)
    add_rect(slide, 0.9, 5.66, 11.55, 1.42, PALE, True)
    add_bullets(slide, 1.05, 5.72, 11.25, 1.32, [
        f'分区：上皮 {pct(76567/164905)}（肝细胞为主）+ 间质 {pct(31007/164905)} + 免疫 {pct(21700/164905)} → 肝实质占主导，符合肝组织背景，切片完整。',
        f'类型：肝细胞 42,412（25.7%）为背景主力；肝癌上皮候选 25,108（15.2%），与肝细胞混合成片；胆管细胞 2,335（1.4%）。',
        '定位：肿瘤候选占比（15.2%）远高于结肠，集中于 1 个 8 µm 聚类（cluster 12，占该区 28.8%），呈大片连续分布、边界不清。',
        '结论：符合肝原发肿瘤（HCC/ICC 谱系）背景，免疫相对贫乏；亚型须病理明确，肿瘤边界需病理/CNV 界定。',
    ], 12)

    # ---------- 9 WHY CANDIDATES ----------
    page += 1
    slide = new_slide(prs, "为什么叫“候选”而不是“确诊”？——证据规则", "证据", page)
    add_rect(slide, 0.55, 1.15, 5.9, 4.85, PALE_TEAL, True)
    add_text(slide, 0.85, 1.35, 5.3, 0.45, "判定为“肿瘤候选”需要什么", 20, True, TEAL)
    add_bullets(slide, 0.85, 2.0, 5.25, 3.4, [
        "至少两类独立证据同时支持",
        "证据① 疾病特异性参考映射（结肠：CRC Atlas；肝：肝癌参考）",
        "证据② 组织特异肿瘤 marker 程序",
        "只有 EPCAM/KRT 等“泛上皮”信号不足以判恶性",
    ], 14.5)
    add_rect(slide, 6.85, 1.15, 5.9, 4.85, PALE_GOLD, True)
    add_text(slide, 7.15, 1.35, 5.3, 0.45, "为什么只能算“候选”", 20, True, GOLD)
    add_bullets(slide, 7.15, 2.0, 5.25, 3.4, [
        "本次未提供病理科 ROI 框选",
        "未做 CNV（拷贝数变异）证据",
        "基因表达是“推断”，病理形态才是“确诊”",
        "肝脏样本 HCC/ICC 亚型未定（需病理）",
    ], 14.5)
    add_note(slide, "结论口径：把恶性相关结果表述为“肿瘤性上皮候选”，并给出候选富集区域坐标，供病理/下游实验直接复核。")

    # ---------- 10 IMMUNE: present types ----------
    page += 1
    slide = new_slide(prs, "免疫细胞有哪些？两个样本免疫构成对照", "免疫浸润", page)
    imm_col = immune["colon"]["immune_fraction"]
    imm_liv = immune["liver"]["immune_fraction"]
    add_metric(slide, 0.55, 1.15, 2.9, 1.45, pct(imm_col), "colon 免疫细胞占比", TEAL)
    add_metric(slide, 3.65, 1.15, 2.9, 1.45, pct(imm_liv), "liver 免疫细胞占比", CYAN)
    add_metric(slide, 6.75, 1.15, 2.9, 1.45, f"{immune['colon']['immune_cells']:,}", "colon 免疫细胞数", TEAL)
    add_metric(slide, 9.85, 1.15, 2.9, 1.45, f"{immune['liver']['immune_cells']:,}", "liver 免疫细胞数", CYAN)
    rows = [
        ["浆细胞/Plasma", pct(immune["colon"]["program_fraction"]["Plasma_cell"], 1), pct(immune["liver"]["program_fraction"]["Plasma_cell"], 1), "colon 明显更高"],
        ["B 细胞", pct(immune["colon"]["program_fraction"]["B_cell"], 1), pct(immune["liver"]["program_fraction"]["B_cell"], 1), "liver 相对突出"],
        ["巨噬细胞/Macrophage", pct(immune["colon"]["program_fraction"]["Macrophage"], 1), pct(immune["liver"]["program_fraction"]["Macrophage"], 1), "colon 更高"],
        ["T 细胞", pct(immune["colon"]["program_fraction"]["T_cell"], 1), pct(immune["liver"]["program_fraction"]["T_cell"], 1), "两者都不高"],
        ["单核/髓系", pct(immune["colon"]["program_fraction"]["Monocyte"], 1), pct(immune["liver"]["program_fraction"]["Monocyte"], 1), "colon 更高"],
    ]
    add_table(slide, 0.55, 3.0, 12.25, 2.6, ["免疫细胞类型（程序得分≥阈值细胞占比）", "sample_A", "sample_B", "初步解读"], rows, [5.0, 2.0, 2.0, 3.25], 11.5)
    add_note(slide, "解读：结肠以“体液免疫（浆细胞/B）+ 巨噬”为主的免疫微环境，免疫较活跃；肝脏免疫占比较低、以 B 细胞为相对主调，偏“冷”微环境。")

    # ---------- 11 IMMUNE SUBTYPES ----------
    page += 1
    slide = new_slide(prs, "免疫细胞细分亚型：比例是否异常、值得关注吗？", "免疫亚型", page)
    t_col, t_liv = subtype["colon"], subtype["liver"]
    rows = [
        ["T/NK 中 CD8 杀伤性 T", pct(t_col["TNK_CD8"], 1), pct(t_liv["TNK_CD8"], 1), "colon 明显更高 → 杀伤性免疫更活跃"],
        ["T/NK 中 Treg 调节性 T", pct(t_col["TNK_Treg"], 1), pct(t_liv["TNK_Treg"], 1), "两者均低"],
        ["T/NK 中 NK 细胞", pct(t_col["TNK_NK"], 1), pct(t_liv["TNK_NK"], 1), "colon 可测、liver 极低"],
        ["T/NK 中耗竭 T（T_Exhaustion）", pct(t_col["TNK_Exhausted"], 1), pct(t_liv["TNK_Exhausted"], 1), "均低（未到明显耗竭）"],
        ["T/NK 中细胞毒性程序", pct(t_col["TNK_Cytotoxic"], 1), pct(t_liv["TNK_Cytotoxic"], 1), "colon 高于 liver"],
        ["巨噬中 SPP1+（促瘤/间质型）", pct(t_col["Macro_SPP1"], 1), pct(t_liv["Macro_SPP1"], 1), "colon 比例更高"],
        ["巨噬中 C1QC+（抗炎/组织驻留）", pct(t_col["Macro_C1QC"], 1), pct(t_liv["Macro_C1QC"], 1), "两者均为主流"],
    ]
    add_table(slide, 0.4, 1.05, 12.55, 4.55, ["亚型（在该细胞群内的占比）", "sample_A", "sample_B", "值得关注点"], rows, [4.3, 1.7, 1.7, 4.85], 11)
    add_note(slide, "结论：结肠免疫浸润更“活跃且有杀伤性”，值得作为免疫微环境研究对象；肝脏免疫偏贫乏、T 细胞信号弱，属更需关注免疫逃逸/冷肿瘤特征的区域。")

    # ---------- 12 TME STATES ----------
    page += 1
    slide = new_slide(prs, "肿瘤微环境状态：有没有在“为肿瘤铺路”", "微环境", page)
    cols = ["EMT", "Hypoxia", "Angiogenesis", "Proliferation", "myCAF", "inflammatory_CAF", "Cytotoxicity"]
    labels = ["上皮-间质转化 EMT", "缺氧 Hypoxia", "血管生成 Angiogenesis", "增殖 Proliferation", "基质型CAF myCAF", "炎症型CAF iCAF", "细胞毒性 Cytotoxicity"]
    rows = []
    for col, lab in zip(cols, labels):
        c = pct(immune["colon"]["program_fraction"][col], 1)
        l = pct(immune["liver"]["program_fraction"][col], 1)
        note = "colon 显著" if immune["colon"]["program_fraction"][col] > 0.2 else ("liver 相对高" if immune["liver"]["program_fraction"][col] > immune["colon"]["program_fraction"][col] else "水平相近/低")
        rows.append([lab, c, l, note])
    add_table(slide, 0.4, 1.05, 12.55, 3.85, ["微环境状态程序（阳性细胞占全部细胞）", "sample_A", "sample_B", "解读"], rows, [4.3, 2.0, 2.0, 4.25], 11.5)
    add_bullets(slide, 0.9, 5.25, 11.5, 0.8, [
        "解读：结肠呈现明显 EMT（35.6%）与基质型 CAF（45.2%）富集 → 促纤维化、促侵袭的微环境；肝脏 EMT 相对低（8.3%），以肝实质主导、基质为辅。",
    ], 13.5)
    add_note(slide, "这些“状态程序”是计算推断，用于提出假设；与病理形态、免疫组化结果互为补充而非替代。")

    # ---------- 13 RISK / STAGE READ-OUT ----------
    page += 1
    slide = new_slide(prs, "这些发现能预示什么？——谨慎的风险/阶段解读", "临床提示", page)
    add_rect(slide, 0.55, 1.15, 5.9, 4.95, PALE, True)
    add_text(slide, 0.85, 1.35, 5.3, 0.45, "sample_A 提示", 20, True, TEAL)
    add_bullets(slide, 0.85, 2.0, 5.25, 3.5, [
        "肿瘤候选占 2.9%，呈多个富集灶",
        "EMT + myCAF 富集 → 提示侵袭/促纤维化倾向",
        "免疫较活跃（浆细胞/B + 巨噬为主，CD8 可测）",
        "→ 建议：结合病理分期确认肿瘤范围与浸润深度",
    ], 14.5)
    add_rect(slide, 6.85, 1.15, 5.9, 4.95, PALE, True)
    add_text(slide, 7.15, 1.35, 5.3, 0.45, "sample_B 提示", 20, True, CYAN)
    add_bullets(slide, 7.15, 2.0, 5.25, 3.5, [
        "肿瘤候选占 15.2%，与 hepatocyte 混合成片",
        "肝细胞谱系、HCC/ICC 亚型未定",
        "免疫偏贫乏、T 细胞信号弱 → 冷肿瘤特征",
        "→ 建议：病理明确谱系后，评估免疫治疗相关免疫状态",
    ], 14.5)
    add_rect(slide, 0.6, 6.2, 12.1, 0.3, RGBColor(0xFD, 0xF0, 0xE0), True)
    add_text(slide, 0.85, 6.24, 11.6, 0.24, "重要：空间转录组不能替代病理分期（TNM）；以上均为“可提假设的线索”，需病理/临床共同确认。", 12.5, True, GOLD, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)

    # ---------- 14 FIT FOR DOWNSTREAM ----------
    page += 1
    slide = new_slide(prs, "支持开展下游实验吗？——四个维度都通过", "下游可行性", page)
    add_metric(slide, 0.55, 1.2, 2.9, 1.5, "合格", "数据质量（测序+细胞）", GREEN)
    add_metric(slide, 3.65, 1.2, 2.9, 1.5, "完整", "组织结构（HE 完整可读）", GREEN)
    add_metric(slide, 6.75, 1.2, 2.9, 1.5, pct(colon_cons["supported_fraction"]), "colon 注释支持率 A/B", TEAL)
    add_metric(slide, 9.85, 1.2, 2.9, 1.5, pct(liver_cons["supported_fraction"]), "liver 注释支持率 A/B", CYAN)
    add_metric(slide, 0.55, 3.0, 2.9, 1.5, pct(colon_rctd["cell_compartment_agreement"]), "colon RCTD 独立一致率", TEAL)
    add_metric(slide, 3.65, 3.0, 2.9, 1.5, pct(liver_rctd["cell_compartment_agreement"]), "liver RCTD 独立一致率", CYAN)
    add_metric(slide, 6.75, 3.0, 2.9, 1.5, "≥99%", "细胞-轮廓-空间定位对应率", GREEN)
    add_metric(slide, 9.85, 3.0, 2.9, 1.5, "有", "候选富集区域坐标可导出", GREEN)
    add_bullets(slide, 0.9, 4.85, 11.5, 1.0, [
        "结论：四个维度（数据、组织、注释、独立验证）全部通过，且肿瘤候选区域已定位，可据此设计下游实验。",
    ], 15)
    add_note(slide, "“RCTD 独立一致率”= 用独立的 8 µm 网格去卷积方法，与分拣单细胞注释互相印证，达到 92–94%。")

    # ---------- 15 RECOMMENDED EXPERIMENTS (SPATIAL PROTEOMICS) ----------
    page += 1
    slide = new_slide(prs, "建议下一步做什么？（重点推荐空间蛋白组）", "下游建议", page)
    add_rect(slide, 0.55, 1.15, 12.2, 2.35, PALE_TEAL, True)
    add_text(slide, 0.85, 1.3, 11.6, 0.45, "首选：空间蛋白组学（在同样本连续切片上做）", 20, True, TEAL)
    add_bullets(slide, 0.85, 1.9, 11.6, 1.45, [
        "用抗体在蛋白层面直接验证“肿瘤候选”与免疫细胞（CD8/Treg/巨噬极化），不依赖 mRNA 推断",
        "可选平台：Akoya PhenoCycler（40+ 色）、NanoString CosMx SMI、10x Xenium + 蛋白、Lunaphore COMET；按预算与轮次选",
        "优势：蛋白更接近功能表型；与空间转录组数据联合 = 同一组织的“基因+蛋白”双视角验证",
    ], 13.5)
    add_rect(slide, 0.55, 3.7, 5.9, 2.15, PALE, True)
    add_text(slide, 0.85, 3.85, 5.3, 0.4, "同步开展（低成本高价值）", 18, True, DARK)
    add_bullets(slide, 0.85, 4.35, 5.25, 1.35, [
        "病理科对候选富集区域复核（HE/免疫组化）",
        "多重免疫组化（mIHC）：CD8、PD-L1、巨噬标志物",
        "CNV 分析复核肿瘤候选",
    ], 13)
    add_rect(slide, 6.85, 3.7, 5.9, 2.15, PALE_GOLD, True)
    add_text(slide, 7.15, 3.85, 5.3, 0.4, "进阶（如预算充足）", 18, True, GOLD)
    add_bullets(slide, 7.15, 4.35, 5.25, 1.35, [
        "对候选区域做单细胞解离 + 单细胞转录组/免疫表型",
        "空间蛋白 + 空间转录组共切片配准",
        "扩展到独立队列验证免疫/微环境发现",
    ], 13)
    add_note(slide, "建议顺序：空间蛋白组验证（首选）→ 病理/CNV 复核 → 若需深入再考虑解离单细胞。候选区域坐标已就绪，可直接用于设计。", PALE_TEAL)

    # ---------- 16 RCTD VALIDATION (TRUST) ----------
    page += 1
    slide = new_slide(prs, "信任背书：用第二种方法独立验证细胞构成", "独立验证", page)
    put_image(slide, data["figures"]["rctd_clusters"], 0.55, 1.0, 8.4, 4.5)
    add_metric(slide, 9.35, 1.15, 3.4, 1.5, pct(colon_rctd["cell_compartment_agreement"]), "colon 一致率（独立方法）", TEAL)
    add_metric(slide, 9.35, 2.9, 3.4, 1.5, pct(liver_rctd["cell_compartment_agreement"]), "liver 一致率（独立方法）", CYAN)
    add_bullets(slide, 9.35, 4.65, 3.55, 1.6, [
        "RCTD：另一种公认的空间去卷积算法",
        "处理约 100 万个 8 µm 网格单元",
        "与分拣单细胞注释在大类上高度一致",
    ], 12.5)
    add_note(slide, "两种独立方法（分拣单细胞 + 8 µm 网格去卷积）得到一致的细胞大类构成，说明注释结果稳健。")

    # ---------- 17 LIMITATIONS ----------
    page += 1
    slide = new_slide(prs, "边界与局限：什么结论现在还不能下", "局限", page)
    add_bullets(slide, 0.9, 1.35, 11.5, 4.4, [
        "恶性为“计算候选”：没有病理 ROI、没有 CNV，最终确诊需病理复核",
        "肝脏样本 HCC/ICC 亚型未定：需病理明确谱系后再下结论",
        "单对样本：不能做患者群体间的统计推断，所有比较为描述性",
        "表达深度有限：肝脏样本细亚型（如 T/NK 亚型）结论应保守",
        "免疫亚型由基因程序推断：建议用蛋白（空间蛋白组/mIHC）二次确认",
        "测序饱和度偏低：如追求更全基因覆盖，可考虑补充测序",
    ], 15)
    add_note(slide, "本报告的“可下结论”与“待验证”已经分列清楚：数据层结论可靠，生物学/临床结论需正交验证。", PALE_GOLD)

    # ---------- 18 DECISION-READY NEXT ACTIONS ----------
    page += 1
    slide = new_slide(prs, "下一步行动建议（供决策）", "行动建议", page)
    rows = [
        ["P0", "空间蛋白组验证肿瘤候选与免疫微环境（首选）", "同一连续切片做蛋白组，直接验证", "1–2 个月", "中高"],
        ["P0", "病理科复核候选富集区域（HE/免疫组化）", "确认肿瘤范围与肝样本谱系（HCC/ICC）", "2–4 周", "低"],
        ["P1", "CNV 分析复核肿瘤候选", "与表达证据互补", "2–4 周", "低"],
        ["P1", "多重免疫组化：CD8 / PD-L1 / 巨噬极化", "验证免疫浸润结论", "4–6 周", "低"],
        ["P2", "候选区域单细胞解离测序", "深入免疫/肿瘤状态", "2–3 个月", "中高"],
    ]
    add_table(slide, 0.4, 1.05, 12.55, 3.6, ["优先级", "行动", "目的", "周期（估）", "成本"], rows, [1.0, 4.6, 3.5, 1.6, 1.6], 11.5)
    add_rect(slide, 0.55, 4.95, 12.2, 0.85, PALE_TEAL, True)
    add_text(slide, 0.85, 5.10, 11.6, 0.55, "建议起步组合：空间蛋白组（验证）+ 病理复核（确诊）双线并行，2–4 周内即可对领导给出“肿瘤在哪、免疫怎么样”的确认版。", 14.5, True, TEAL, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    add_note(slide, "本页优先级与周期为建议值，可按预算/资源调整；候选区域坐标、细胞清单、图与表格均已随报告交付。")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUTPUT_PATH)
    print(f"slides={len(prs.slides)} output={OUTPUT_PATH}")


if __name__ == "__main__":
    build()
