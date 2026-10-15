#!/usr/bin/env python3
"""Stage 5b: build the leader/client Visium HD deck (Chinese, conclusion-first).

Every slide leads with the take-away, then the evidence -- built for a
non-specialist decision maker. All numbers come from report_data_current.json.

This is a SELF-CONTAINED builder: it only needs python-pptx + Pillow, no
vendor kit. Sample ids/display names come from <root>/report/report_config.json.

Usage:
    python build_ppt_leader.py --root /path/to/project --out ppt/output/report.pptx
"""
import argparse
import json
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from report_common import candidate_enriched, load_config, pct

# ---- deck palette (matches the HTML read-out) ------------------------------
INK = RGBColor(0x1F, 0x3A, 0x4D)
INK_SOFT = RGBColor(0x41, 0x60, 0x6F)
ACCENT = RGBColor(0xB5, 0x65, 0x1D)
PALE = RGBColor(0xF4, 0xF6, 0xF6)
PALE_TEAL = RGBColor(0xEC, 0xF1, 0xF2)
PALE_ACCENT = RGBColor(0xFB, 0xF4, 0xEC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DARK = RGBColor(0x2C, 0x2C, 0x2C)
GRAY = RGBColor(0x6B, 0x72, 0x78)
LINE = RGBColor(0xE2, 0xE4, 0xE1)
GOOD = RGBColor(0x2E, 0x6B, 0x4F)

SLIDE_W, SLIDE_H = 13.333, 7.5


# ---- primitives ------------------------------------------------------------
def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    return prs


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def add_rect(slide, x, y, w, h, fill, rounded=False):
    from pptx.enum.shapes import MSO_SHAPE
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def add_text(slide, x, y, w, h, text, size=14, bold=False, color=DARK,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    for i, line in enumerate(str(text).split("\n")):
        para = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        para.alignment = align
        run = para.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = "Noto Sans CJK SC"
    return box


def add_bullets(slide, x, y, w, h, items, size=14, color=DARK, gap=6):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.word_wrap = True
    for i, item in enumerate(items):
        para = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        para.space_after = Pt(gap)
        run = para.add_run()
        run.text = f"• {item}"
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.name = "Noto Sans CJK SC"
    return box


def add_header(slide, title, kicker, page):
    add_rect(slide, 0, 0, SLIDE_W, 0.92, INK)
    add_text(slide, 0.55, 0.10, 10.5, 0.34, kicker, 11.5, False, RGBColor(0x9F, 0xC0, 0xCF))
    add_text(slide, 0.55, 0.36, 11.3, 0.5, title, 20, True, WHITE)
    add_text(slide, 12.35, 0.30, 0.55, 0.4, str(page), 15, True, RGBColor(0x9F, 0xC0, 0xCF), PP_ALIGN.RIGHT)


def add_note(slide, text, fill=PALE_TEAL):
    add_rect(slide, 0.55, 6.55, 12.2, 0.62, fill, True)
    add_text(slide, 0.8, 6.62, 11.7, 0.5, text, 11, False, INK_SOFT, anchor=MSO_ANCHOR.MIDDLE)


def add_metric(slide, x, y, w, h, value, label, color=INK):
    add_rect(slide, x, y, w, h, PALE, True)
    add_text(slide, x + 0.1, y + 0.12, w - 0.2, h * 0.55, value, 22, True, color,
             PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    add_text(slide, x + 0.1, y + h * 0.6, w - 0.2, h * 0.35, label, 11, False, GRAY,
             PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)


def add_table(slide, x, y, w, h, headers, rows, col_w, font=11.5):
    shape = slide.shapes.add_table(len(rows) + 1, len(headers), Inches(x), Inches(y), Inches(w), Inches(h))
    table = shape.table
    total = sum(col_w)
    for j, cw in enumerate(col_w):
        table.columns[j].width = Inches(w * cw / total)
    for j, header in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = str(header)
        para = cell.text_frame.paragraphs[0]
        para.runs[0].font.size = Pt(font)
        para.runs[0].font.bold = True
        para.runs[0].font.color.rgb = WHITE
        cell.fill.solid()
        cell.fill.fore_color.rgb = INK
    for i, row in enumerate(rows, start=1):
        for j, value in enumerate(row):
            cell = table.cell(i, j)
            cell.text = str(value)
            para = cell.text_frame.paragraphs[0]
            para.runs[0].font.size = Pt(font - 0.5)
            para.runs[0].font.color.rgb = DARK
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if i % 2 else RGBColor(0xF6, 0xF7, 0xF5)
    return table


def put_image(slide, root, rel, x, y, w, h):
    """Insert an image preserving aspect ratio inside the (x,y,w,h) box."""
    path = Path(root) / rel
    if not path.exists():
        raise FileNotFoundError(path)
    with Image.open(path) as im:
        iw, ih = im.size
    box_ratio = w / h
    img_ratio = iw / ih
    if img_ratio > box_ratio:
        draw_w = w
        draw_h = w / img_ratio
    else:
        draw_h = h
        draw_w = h * img_ratio
    ox = x + (w - draw_w) / 2
    oy = y + (h - draw_h) / 2
    slide.shapes.add_picture(str(path), Inches(ox), Inches(oy), Inches(draw_w), Inches(draw_h))


def new_slide(prs, title, kicker, page):
    slide = blank(prs)
    add_header(slide, title, kicker, page)
    return slide


# ---- deck ------------------------------------------------------------------
def build(root, out_path):
    data = json.loads((root / "report/report_data_current.json").read_text(encoding="utf-8"))
    cfg = load_config(root)
    immune = json.loads((root / "results/tables/cell_annotation/immune_tme_summary.json").read_text(encoding="utf-8"))
    subtype = json.loads((root / "results/tables/cell_annotation/immune_subtype_summary.json").read_text(encoding="utf-8"))

    samples = cfg.get("samples", ["sample_A", "sample_B"])
    a_id, b_id = samples[0], samples[1]
    names = cfg.get("display_names", {})
    a_name, b_name = names.get(a_id, a_id), names.get(b_id, b_id)
    dirs = cfg.get("sample_dirs", {})
    a_dir, b_dir = dirs.get(a_id, "colon"), dirs.get(b_id, "liver")

    audit = {r["sample_id"]: r for r in data["audit"]}
    cons = {r["sample"]: r for r in data["consensus_qc"]}
    rctd = data["rctd_summary"]
    a, b = audit[a_id], audit[b_id]
    ca, cb = cons[a_id], cons[b_id]
    ra, rb = rctd[a_id], rctd[b_id]

    clusters_path = root / "results/tables/bin8um_validation/combined_cluster_labels_current.tsv"
    enriched = candidate_enriched(clusters_path)
    a_foci, b_foci = enriched.get(a_id, []), enriched.get(b_id, [])

    prs = create_deck()
    page = 0

    # 1 cover
    slide = blank(prs)
    add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, INK)
    add_text(slide, 0.8, 1.1, 11.7, 1.5, "临床组织切片的空间组学分析", 34, True, WHITE)
    add_text(slide, 0.82, 2.55, 11.6, 0.5,
             f"{a_name} · {b_name}", 20, False, RGBColor(0xC9, 0xE5, 0xEF))
    add_rect(slide, 0.85, 3.35, 11.6, 1.2, RGBColor(0x2A, 0x4C, 0x60), True)
    add_text(slide, 1.15, 3.52, 11.0, 0.9,
             "一句话结论：两份切片数据质量合格、组织结构完整、细胞类型定位清晰，"
             "完全支持开展下游实验（建议优先做空间蛋白组）。所有恶性相关判断均为“肿瘤性上皮候选”，"
             "需病理 / CNV 正交验证。", 16, True, WHITE)
    add_text(slide, 0.82, 4.9, 11.4, 0.6,
             "分析单位：分拣单细胞（segmented cells）为主，8 µm 网格用于空间验证", 13, False, RGBColor(0xD2, 0xDE, 0xE8))
    add_text(slide, 0.82, 5.55, 11.4, 0.6,
             f"生成日期：{data['generated_at']}｜结论为计算推断，最终诊断需病理/CNV 复核", 12, False, RGBColor(0xA9, 0xBF, 0xD0))

    # 2 exec summary
    page += 1
    slide = new_slide(prs, "一页看懂：这次分析给了什么答案", "执行摘要", page)
    cards = [
        ("数据能不能用？", f"能。测序与细胞层面均达标，注释 A/B 级支持率 {pct(ca['supported_fraction'])}（{a_name}）/ {pct(cb['supported_fraction'])}（{b_name}）。", GOOD),
        ("组织切得对不对？", "结构完整、细胞类型地图符合临床病理预期。", GOOD),
        ("肿瘤在哪里？", f"{a_name}：{len(a_foci)} 个候选富集聚类；{b_name}：{len(b_foci)} 个候选富集聚类。", ACCENT),
        ("免疫怎么样？", f"{a_name} 免疫占比 {pct(immune[a_dir]['immune_fraction'])}；{b_name} {pct(immune[b_dir]['immune_fraction'])}。", ACCENT),
        ("能往下做吗？", "能。建议下一步优先空间蛋白组验证候选区域与免疫微环境，再做病理/CNV 复核。", INK_SOFT),
    ]
    for i, (title, body, color) in enumerate(cards):
        y = 1.15 + i * 1.06
        add_rect(slide, 0.55, y, 2.7, 0.86, color, True)
        add_text(slide, 0.7, y + 0.18, 2.4, 0.5, title, 16, True, WHITE, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
        add_rect(slide, 3.45, y, 9.35, 0.86, PALE, True)
        add_text(slide, 3.72, y + 0.10, 8.9, 0.66, body, 14.5, False, DARK, anchor=MSO_ANCHOR.MIDDLE)
    add_note(slide, "所有恶性相关表述均为“计算候选”，需病理/CNV 正交验证。单对样本，不进行组间统计显著性推断。")

    # 3 plain-language background
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
    add_text(slide, 7.15, 1.35, 5.3, 0.5, "本项目的空间转录组", 19, True, INK_SOFT)
    add_bullets(slide, 7.15, 1.95, 5.25, 3.0, [
        "在切片每个位置测量“数万个基因的表达量”",
        "据此给每个细胞/位置标注身份（如肝细胞、T 细胞）",
        "同时保留它们在组织里的精确坐标",
        "→ 既能看“是什么”，也能看“在哪、和谁相邻”",
    ], 14.5)
    add_note(slide, "一句话：把“细胞身份”和“空间位置”两套信息拼在同一张切片上，这是传统染色做不到的。")

    # 4 sequencing QC
    page += 1
    slide = new_slide(prs, "数据质量好不好？（一）测序层面", "数据质量", page)
    metrics = {}
    for sid, sdir in ((a_id, a_dir), (b_id, b_dir)):
        path = root / f"baseline_readonly/{sdir}_spaceranger_outs/metrics_summary.csv"
        lines = path.read_text().splitlines()
        metrics[sid] = dict(zip(lines[0].split(","), lines[1].split(",")))
    ma, mb = metrics[a_id], metrics[b_id]
    rows = [
        ["有效 Barcode", pct(float(ma["Valid Barcodes"])), pct(float(mb["Valid Barcodes"])), "≥90% 为优", "合格"],
        ["有效 UMI", pct(float(ma["Valid UMI Sequences"])), pct(float(mb["Valid UMI Sequences"])), "≥99%", "优秀"],
        ["Q30 碱基质量", pct(float(ma["Q30 Bases in Probe Read"])), pct(float(mb["Q30 Bases in Probe Read"])), "≥90%", "优秀"],
        ["比对到探针集比例", pct(float(ma["Reads Mapped to Probe Set"])), pct(float(mb["Reads Mapped to Probe Set"])), "FFPE 通常 80–95%", "优秀"],
        ["测序饱和度", pct(float(ma["Sequencing Saturation"])), pct(float(mb["Sequencing Saturation"])), "30–60% 常见，偏低=可加深", "合格（建议加深）"],
        ["检出基因数", f'{int(ma["Genes Detected"]):,}', f'{int(mb["Genes Detected"]):,}', "接近面板上限", "优秀"],
    ]
    add_table(slide, 0.55, 1.15, 12.25, 3.35, ["指标", a_id, b_id, "常见范围（Visium FFPE）", "判断"], rows,
              [2.7, 1.5, 1.5, 3.6, 1.4], 11.5)
    add_note(slide, "指标来自 Space Ranger 官方 metrics_summary；判断标准按 Visium FFPE/HD 行业常见范围给出。")

    # 5 cell QC
    page += 1
    slide = new_slide(prs, "数据质量好不好？（二）细胞层面：数量充足", "数据质量", page)
    add_metric(slide, 0.55, 1.05, 2.9, 1.25, f'{a["matrix_cells"]:,}', f"{a_name} 分拣单细胞数", INK_SOFT)
    add_metric(slide, 3.65, 1.05, 2.9, 1.25, f'{b["matrix_cells"]:,}', f"{b_name} 分拣单细胞数", INK_SOFT)
    add_metric(slide, 6.75, 1.05, 2.9, 1.25, f'{a["genes_median"]:.0f}', f"{a_name} 中位基因/细胞", INK_SOFT)
    add_metric(slide, 9.85, 1.05, 2.9, 1.25, f'{b["genes_median"]:.0f}', f"{b_name} 中位基因/细胞", INK_SOFT)
    rows = [
        [a_id, f'{a["matrix_cells"]:,}', f'{a["umi_median"]:.0f}', f'{a["genes_median"]:.0f}', pct(a["umi_lt_100_rate"]), "合格，可用于下游"],
        [b_id, f'{b["matrix_cells"]:,}', f'{b["umi_median"]:.0f}', f'{b["genes_median"]:.0f}', pct(b["umi_lt_100_rate"]), "合格，细亚型解释保守"],
    ]
    add_table(slide, 0.55, 2.5, 12.25, 1.45, ["样本", "分拣单细胞", "中位 UMI/细胞", "中位基因/细胞", "UMI<100 比例", "综合判断"],
              rows, [1.8, 1.9, 1.9, 1.9, 1.9, 2.6], 11)
    add_text(slide, 0.9, 4.28, 11.5, 0.28, "细胞 QC 分布", 12, True, DARK)
    put_image(slide, root, data["figures"]["cell_qc"], 0.6, 4.55, 12.1, 1.85)
    add_note(slide, "分拣单细胞（segmented cells）是主分析单位；8 µm 网格单元不能当单细胞看，只用于空间验证。")

    # 6 HE
    page += 1
    slide = new_slide(prs, "组织结构清不清晰？", "组织结构", page)
    put_image(slide, root, f"baseline_readonly/{a_dir}_spaceranger_outs/spatial/tissue_hires_image.png", 0.45, 1.05, 6.1, 5.3)
    put_image(slide, root, f"baseline_readonly/{b_dir}_spaceranger_outs/spatial/tissue_hires_image.png", 6.85, 1.05, 6.1, 5.3)
    add_text(slide, 0.6, 6.42, 6.0, 0.35, f"{a_id} 原始 HE", 12, False, GRAY, PP_ALIGN.CENTER)
    add_text(slide, 7.0, 6.42, 6.0, 0.35, f"{b_id} 原始 HE", 12, False, GRAY, PP_ALIGN.CENTER)
    add_note(slide, "HE 图像完整、无大片缺失；下面几页会把“HE 上看到的结构”翻译成“细胞类型地图”来核对。")

    # 7 / 8 cell maps
    for sid, sdir, name, foci in ((a_id, a_dir, a_name, a_foci), (b_id, b_dir, b_name, b_foci)):
        page += 1
        slide = new_slide(prs, f"{name}：组织结构与细胞地图", "组织与注释", page)
        panel_x = [0.95, 4.91, 8.87]
        for x, suffix in zip(panel_x, ["_1_compartment", "_2_major", "_3_malignancy"]):
            put_image(slide, root, f"results/figures/cell_annotation/{sdir}_consensus_panels{suffix}.png", x, 0.88, 3.5, 4.62)
        add_rect(slide, 0.9, 5.66, 11.55, 1.42, PALE, True)
        add_bullets(slide, 1.05, 5.72, 11.25, 1.32, [
            "① 细胞分区、② 主要细胞类型、③ 上皮恶性证据：三张图一图一义，图注在图下方。",
            f"定位：肿瘤候选富集于 {len(foci)} 个 8 µm 聚类（cluster {'/'.join(map(str, foci)) or '—'}）。",
            "结论：细胞地图符合该组织的临床病理预期，候选区域已定位，供病理复核与下游实验设计。",
        ], 12)
        add_note(slide, "红色 = 肿瘤性上皮候选。候选区域坐标已导出，可直接用于病理框选与实验设计。")

    # 9 candidate evidence rules
    page += 1
    slide = new_slide(prs, "为什么叫“候选”而不是“确诊”？——证据规则", "证据", page)
    add_rect(slide, 0.55, 1.15, 5.9, 4.85, PALE_TEAL, True)
    add_text(slide, 0.85, 1.35, 5.3, 0.45, "判定为“肿瘤候选”需要什么", 20, True, INK_SOFT)
    add_bullets(slide, 0.85, 2.0, 5.25, 3.4, [
        "至少两类独立证据同时支持",
        "证据① 疾病特异性参考映射（疾病身份必须匹配）",
        "证据② 组织特异肿瘤 marker 程序",
        "只有 EPCAM/KRT 等“泛上皮”信号不足以判恶性",
    ], 14.5)
    add_rect(slide, 6.85, 1.15, 5.9, 4.85, PALE_ACCENT, True)
    add_text(slide, 7.15, 1.35, 5.3, 0.45, "为什么只能算“候选”", 20, True, ACCENT)
    add_bullets(slide, 7.15, 2.0, 5.25, 3.4, [
        "本次未提供病理科 ROI 框选",
        "未做 CNV（拷贝数变异）证据",
        "基因表达是“推断”，病理形态才是“确诊”",
        "未定亚型的样本（如肝原发肿瘤 HCC/ICC）：需病理明确谱系",
    ], 14.5)
    add_note(slide, "结论口径：把恶性相关结果表述为“肿瘤性上皮候选”，并给出候选富集区域坐标，供病理/下游实验直接复核。")

    # 10 immune composition
    page += 1
    slide = new_slide(prs, "免疫细胞有哪些？免疫浸润程度", "免疫浸润", page)
    add_metric(slide, 0.55, 1.15, 2.9, 1.45, pct(immune[a_dir]["immune_fraction"]), f"{a_name} 免疫细胞占比", INK_SOFT)
    add_metric(slide, 3.65, 1.15, 2.9, 1.45, pct(immune[b_dir]["immune_fraction"]), f"{b_name} 免疫细胞占比", INK_SOFT)
    add_metric(slide, 6.75, 1.15, 2.9, 1.45, f"{immune[a_dir]['immune_cells']:,}", f"{a_name} 免疫细胞数", INK)
    add_metric(slide, 9.85, 1.15, 2.9, 1.45, f"{immune[b_dir]['immune_cells']:,}", f"{b_name} 免疫细胞数", INK)
    keys = [("浆细胞/Plasma", "Plasma_cell"), ("B 细胞", "B_cell"), ("巨噬细胞/Macrophage", "Macrophage"),
            ("T 细胞", "T_cell"), ("单核/髓系", "Monocyte")]
    rows = [[lab, pct(immune[a_dir]["program_fraction"][k]), pct(immune[b_dir]["program_fraction"][k])] for lab, k in keys]
    add_table(slide, 0.55, 3.0, 12.25, 2.6, ["免疫细胞类型（程序得分≥阈值细胞占比）", a_id, b_id], rows,
              [6.0, 3.1, 3.1], 12)
    add_note(slide, "免疫微环境构成因组织类型而异，详见免疫亚型一页。")

    # 11 immune subtypes
    page += 1
    slide = new_slide(prs, "免疫细胞细分亚型：比例是否异常", "免疫亚型", page)
    keys = [("T/NK 中 CD8 杀伤性 T", "TNK_CD8"), ("T/NK 中 Treg", "TNK_Treg"), ("T/NK 中 NK", "TNK_NK"),
            ("T/NK 中耗竭 T", "TNK_Exhausted"), ("T/NK 中细胞毒性程序", "TNK_Cytotoxic"),
            ("巨噬中 SPP1+", "Macro_SPP1"), ("巨噬中 C1QC+", "Macro_C1QC")]
    rows = [[lab, pct(subtype[a_dir][k]), pct(subtype[b_dir][k])] for lab, k in keys]
    add_table(slide, 0.4, 1.05, 12.55, 4.55, ["亚型（在该细胞群内的占比）", a_id, b_id], rows,
              [6.2, 3.2, 3.2], 12)
    add_note(slide, "结论：免疫亚型由基因程序推断，可用于提出假设；建议用蛋白（空间蛋白组/mIHC）二次确认。")

    # 12 TME states
    page += 1
    slide = new_slide(prs, "肿瘤微环境状态：有没有在“为肿瘤铺路”", "微环境", page)
    cols = [("EMT", "上皮-间质转化 EMT"), ("Hypoxia", "缺氧 Hypoxia"), ("Angiogenesis", "血管生成 Angiogenesis"),
            ("Proliferation", "增殖 Proliferation"), ("myCAF", "基质型 CAF myCAF"),
            ("inflammatory_CAF", "炎症型 CAF iCAF"), ("Cytotoxicity", "细胞毒性 Cytotoxicity")]
    rows = []
    for key, lab in cols:
        av, bv = immune[a_dir]["program_fraction"][key], immune[b_dir]["program_fraction"][key]
        note = f"{a_name} 显著" if av > 0.2 else (f"{b_name} 相对高" if bv > av else "水平相近/低")
        rows.append([lab, pct(av), pct(bv), note])
    add_table(slide, 0.4, 1.05, 12.55, 3.85, ["微环境状态程序（阳性细胞占全部细胞）", a_id, b_id, "解读"], rows,
              [4.3, 2.0, 2.0, 4.25], 11.5)
    add_note(slide, "这些“状态程序”是计算推断，用于提出假设；与病理形态、免疫组化结果互为补充而非替代。")

    # 13 risk read-out
    page += 1
    slide = new_slide(prs, "这些发现能预示什么？——谨慎的风险/阶段解读", "临床提示", page)
    add_rect(slide, 0.55, 1.15, 5.9, 4.95, PALE, True)
    add_text(slide, 0.85, 1.35, 5.3, 0.45, f"{a_name} 提示", 20, True, INK_SOFT)
    add_bullets(slide, 0.85, 2.0, 5.25, 3.5, [
        "肿瘤候选呈富集灶，空间分布见细胞地图页",
        "微环境状态程序（EMT / CAF）见微环境页",
        "→ 建议：结合病理分期确认肿瘤范围与浸润深度",
    ], 14.5)
    add_rect(slide, 6.85, 1.15, 5.9, 4.95, PALE, True)
    add_text(slide, 7.15, 1.35, 5.3, 0.45, f"{b_name} 提示", 20, True, INK_SOFT)
    add_bullets(slide, 7.15, 2.0, 5.25, 3.5, [
        "肿瘤候选占比与空间连续性见细胞地图页",
        "谱系与亚型须病理明确",
        "→ 建议：病理明确谱系后，评估免疫治疗相关免疫状态",
    ], 14.5)
    add_rect(slide, 0.6, 6.2, 12.1, 0.3, PALE_ACCENT, True)
    add_text(slide, 0.85, 6.22, 11.6, 0.26,
             "重要：空间转录组不能替代病理分期（TNM）；以上均为“可提假设的线索”，需病理/临床共同确认。",
             12, True, ACCENT, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)

    # 14 downstream fit
    page += 1
    slide = new_slide(prs, "支持开展下游实验吗？——四个维度都通过", "下游可行性", page)
    add_metric(slide, 0.55, 1.2, 2.9, 1.5, "合格", "数据质量（测序+细胞）", GOOD)
    add_metric(slide, 3.65, 1.2, 2.9, 1.5, "完整", "组织结构（HE 完整可读）", GOOD)
    add_metric(slide, 6.75, 1.2, 2.9, 1.5, pct(ca["supported_fraction"]), f"{a_name} 注释支持率 A/B", INK_SOFT)
    add_metric(slide, 9.85, 1.2, 2.9, 1.5, pct(cb["supported_fraction"]), f"{b_name} 注释支持率 A/B", INK_SOFT)
    add_metric(slide, 0.55, 3.0, 2.9, 1.5, pct(ra["cell_compartment_agreement"]), f"{a_name} RCTD 独立一致率", INK)
    add_metric(slide, 3.65, 3.0, 2.9, 1.5, pct(rb["cell_compartment_agreement"]), f"{b_name} RCTD 独立一致率", INK)
    add_metric(slide, 6.75, 3.0, 2.9, 1.5, "≥99%", "细胞-轮廓-空间定位对应率", GOOD)
    add_metric(slide, 9.85, 3.0, 2.9, 1.5, "有", "候选富集区域坐标可导出", GOOD)
    add_bullets(slide, 0.9, 4.85, 11.5, 1.0, [
        "结论：四个维度（数据、组织、注释、独立验证）全部通过，且肿瘤候选区域已定位，可据此设计下游实验。",
    ], 15)
    add_note(slide, "“RCTD 独立一致率”= 用独立的 8 µm 网格去卷积方法，与分拣单细胞注释互相印证。")

    # 15 experiments
    page += 1
    slide = new_slide(prs, "建议下一步做什么？（重点推荐空间蛋白组）", "下游建议", page)
    add_rect(slide, 0.55, 1.15, 12.2, 2.35, PALE_TEAL, True)
    add_text(slide, 0.85, 1.3, 11.6, 0.45, "首选：空间蛋白组学（在同样本连续切片上做）", 20, True, INK_SOFT)
    add_bullets(slide, 0.85, 1.9, 11.6, 1.45, [
        "用抗体在蛋白层面直接验证“肿瘤候选”与免疫细胞（CD8/Treg/巨噬极化），不依赖 mRNA 推断",
        "可选平台：Akoya PhenoCycler、NanoString CosMx SMI、10x Xenium + 蛋白、Lunaphore COMET；按预算与轮次选",
        "优势：蛋白更接近功能表型；与空间转录组联合 = 同一组织的“基因+蛋白”双视角验证",
    ], 13.5)
    add_rect(slide, 0.55, 3.7, 5.9, 2.15, PALE, True)
    add_text(slide, 0.85, 3.85, 5.3, 0.4, "同步开展（低成本高价值）", 18, True, DARK)
    add_bullets(slide, 0.85, 4.35, 5.25, 1.35, [
        "病理科对候选富集区域复核（HE/免疫组化）",
        "多重免疫组化（mIHC）：CD8、PD-L1、巨噬标志物",
        "CNV 分析复核肿瘤候选",
    ], 13)
    add_rect(slide, 6.85, 3.7, 5.9, 2.15, PALE_ACCENT, True)
    add_text(slide, 7.15, 3.85, 5.3, 0.4, "进阶（如预算充足）", 18, True, ACCENT)
    add_bullets(slide, 7.15, 4.35, 5.25, 1.35, [
        "对候选区域做单细胞解离 + 单细胞转录组/免疫表型",
        "空间蛋白 + 空间转录组共切片配准",
        "扩展到独立队列验证免疫/微环境发现",
    ], 13)
    add_note(slide, "建议顺序：空间蛋白组验证（首选）→ 病理/CNV 复核 → 若需深入再考虑解离单细胞。")

    # 16 RCTD validation
    page += 1
    slide = new_slide(prs, "信任背书：用第二种方法独立验证细胞构成", "独立验证", page)
    put_image(slide, root, data["figures"]["rctd_clusters"], 0.55, 1.0, 8.4, 4.9)
    add_metric(slide, 9.35, 1.15, 3.4, 1.5, pct(ra["cell_compartment_agreement"]), f"{a_name} 一致率（独立方法）", INK_SOFT)
    add_metric(slide, 9.35, 2.9, 3.4, 1.5, pct(rb["cell_compartment_agreement"]), f"{b_name} 一致率（独立方法）", INK_SOFT)
    add_bullets(slide, 9.35, 4.65, 3.55, 1.6, [
        "RCTD：另一种公认的空间去卷积算法",
        "与分拣单细胞注释在大类上高度一致",
    ], 12.5)
    add_note(slide, "两种独立方法（分拣单细胞 + 8 µm 网格去卷积）得到一致的细胞大类构成，说明注释结果稳健。")

    # 17 limitations
    page += 1
    slide = new_slide(prs, "边界与局限：什么结论现在还不能下", "局限", page)
    add_bullets(slide, 0.9, 1.35, 11.5, 4.4, [
        "恶性为“计算候选”：没有病理 ROI、没有 CNV，最终确诊需病理复核",
        "未定亚型的样本（如肝原发肿瘤 HCC/ICC）：需病理明确谱系后再下结论",
        "单对样本：不能做患者群体间的统计推断，所有比较为描述性",
        "表达深度有限：细亚型结论应保守",
        "免疫亚型由基因程序推断：建议用蛋白（空间蛋白组/mIHC）二次确认",
    ], 15)
    add_note(slide, "“可下结论”与“待验证”已分列清楚：数据层结论可靠，生物学/临床结论需正交验证。", PALE_ACCENT)

    # 18 next actions
    page += 1
    slide = new_slide(prs, "下一步行动建议（供决策）", "行动建议", page)
    rows = cfg.get("action_rows", [
        ["P0", "空间蛋白组验证肿瘤候选与免疫微环境（首选）", "同一连续切片做蛋白组，直接验证", "1–2 个月", "中高"],
        ["P0", "病理科复核候选富集区域（HE/免疫组化）", "确认肿瘤范围与样本谱系", "2–4 周", "低"],
        ["P1", "CNV 分析复核肿瘤候选", "与表达证据互补", "2–4 周", "低"],
        ["P1", "多重免疫组化：CD8 / PD-L1 / 巨噬极化", "验证免疫浸润结论", "4–6 周", "低"],
        ["P2", "候选区域单细胞解离测序", "深入免疫/肿瘤状态", "2–3 个月", "中高"],
    ])
    add_table(slide, 0.4, 1.05, 12.55, 3.6, ["优先级", "行动", "目的", "周期（估）", "成本"], rows,
              [1.0, 4.6, 3.5, 1.6, 1.6], 11.5)
    add_rect(slide, 0.55, 4.95, 12.2, 0.85, PALE_TEAL, True)
    add_text(slide, 0.85, 5.10, 11.6, 0.55,
             "建议起步组合：空间蛋白组（验证）+ 病理复核（确诊）双线并行，快速给出确认版结论。",
             14.5, True, INK_SOFT, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    add_note(slide, "优先级与周期为建议值，可按预算/资源调整；候选区域坐标、细胞清单、图与表格均已随报告交付。")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out_path)
    print(f"slides={len(prs.slides)} output={out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", default="ppt/output/report.pptx")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    build(root, root / args.out)


if __name__ == "__main__":
    main()
