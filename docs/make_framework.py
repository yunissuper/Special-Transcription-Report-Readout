#!/usr/bin/env python3
"""Render the pipeline + report-structure framework diagram (no project data).

Output: docs/images/framework.png
Run:  python docs/make_framework.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK JP", "Noto Sans CJK SC", "WenQuanYi Zen Hei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

INK = "#1F3A4D"
INK_SOFT = "#41606F"
ACCENT = "#B5651D"
PALE = "#F4F6F6"
PALE_T = "#ECF1F2"
PALE_A = "#FBF4EC"
LINE = "#C9D2D6"
TEXT = "#2C2C2C"


def box(ax, x, y, w, h, title, body, fc, ec=LINE, tc=INK):
    ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                         fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h - 0.22, title, ha="center", va="top", fontsize=11, fontweight="bold", color=tc)
    if body:
        ax.text(x + w / 2, y + h - 0.55, body, ha="center", va="top", fontsize=8.3, color=INK_SOFT, linespacing=1.5)


def arrow(ax, x1, y1, x2, y2, color=INK_SOFT):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=13,
                                 lw=1.4, color=color, shrinkA=2, shrinkB=2))


def main():
    fig, ax = plt.subplots(figsize=(13.5, 9.0))
    ax.set_xlim(0, 13.5); ax.set_ylim(0, 9.0); ax.axis("off")
    ax.text(0.35, 8.62, "空间转录组解读报告 · 完整流水线", fontsize=16, fontweight="bold", color=INK)
    ax.text(0.35, 8.28, "Space Ranger 结果 → 疾病感知细胞注释 → 独立验证 → 自包含 HTML + 结论优先 PPT",
            fontsize=10, color=INK_SOFT)

    # ---- stage row (6 stages) ----
    stages = [
        ("1 数据接入 & 审计", "matrix / GeoJSON /\nAzimuth 对应率、\nUMI·基因 QC", PALE_T),
        ("2 细胞级注释", "疾病参考 mapping\n+ UCell marker\n+ 共识 + A/B/C", PALE),
        ("3 8 µm 独立验证", "RCTD 去卷积\n与 cell 注释\n大类一致率闸门", PALE),
        ("4 结果整合", "单一\nreport_data\n_current.json", PALE_A),
        ("5 报告生成", "中文自包含 HTML\n+ 结论优先 PPT", PALE_T),
        ("6 质量校验", "数字可追溯\n无禁用术语\n无参考错用", PALE),
    ]
    x = 0.35; w = 2.0; gap = 0.13; y, h = 6.62, 1.5
    for i, (title, body, fc) in enumerate(stages):
        box(ax, x, y, w, h, title, body, fc)
        if i < len(stages) - 1:
            arrow(ax, x + w, y + h / 2, x + w + gap, y + h / 2)
        x += w + gap

    # ---- data source bar ----
    ax.add_patch(mpatches.FancyBboxPatch((0.35, 5.62), 6.15, 0.72,
                 boxstyle="round,pad=0.02,rounding_size=0.05", fc="#FFFFFF", ec=LINE, lw=1.2))
    ax.text(0.55, 5.98, "只读输入", fontsize=9.5, fontweight="bold", color=ACCENT, va="center")
    ax.text(2.05, 5.98, "Space Ranger outs · 公开参考图谱(CRC/肝癌) · 探针集 · 原始 HE",
            fontsize=9, color=TEXT, va="center")

    ax.add_patch(mpatches.FancyBboxPatch((6.75, 5.62), 6.4, 0.72,
                 boxstyle="round,pad=0.02,rounding_size=0.05", fc="#FFFFFF", ec=LINE, lw=1.2))
    ax.text(6.95, 5.98, "唯一真源", fontsize=9.5, fontweight="bold", color=ACCENT, va="center")
    ax.text(8.25, 5.98, "report_data_current.json —— 报告与 PPT 都只从这里读数",
            fontsize=9, color=TEXT, va="center")

    # ---- report structure (18 sections in 3 columns) ----
    ax.text(0.35, 5.18, "领导版报告结构（结论优先）", fontsize=12, fontweight="bold", color=INK)
    col_titles = ["① 是什么 / 怎么看", "② 可不可信 / 结果", "③ 单位 / 限制 / 行动"]
    cols = [
        ["1 封面：一句话结论", "2 执行摘要（5 问）", "3 技术背景（通俗）",
         "4 数据质量·测序", "5 数据质量·细胞", "6 组织结构 HE", "7 细胞类型地图"],
        ["8 肿瘤候选定位", "9 候选证据规则", "10 免疫浸润", "11 免疫亚型",
         "12 微环境状态", "13 风险解读", "14 下游可行性"],
        ["15 实验建议（空间蛋白组）", "16 独立验证 RCTD", "17 局限", "18 下一步行动"],
    ]
    cx = 0.35
    cw = 4.2
    for ct, items in zip(col_titles, cols):
        ax.text(cx + cw / 2, 4.82, ct, ha="center", fontsize=10.5, fontweight="bold", color=INK_SOFT)
        bh = 0.30
        step = 0.345
        top = 4.42
        for i, it in enumerate(items):
            yy = top - i * step
            fc = PALE_T if i % 2 == 0 else "#FFFFFF"
            ax.add_patch(mpatches.FancyBboxPatch((cx, yy), cw, bh,
                         boxstyle="round,pad=0.006,rounding_size=0.03", fc=fc, ec=LINE, lw=0.8))
            ax.text(cx + 0.14, yy + bh / 2, it, fontsize=8.6, color=TEXT, va="center")
        cx += cw + 0.28

    # ---- legend / principles ----
    ax.add_patch(mpatches.FancyBboxPatch((0.35, 1.35), 12.8, 1.05,
                 boxstyle="round,pad=0.02,rounding_size=0.05", fc=PALE_A, ec=ACCENT, lw=1.2))
    ax.text(0.6, 2.14, "贯穿全程的四条红线", fontsize=10, fontweight="bold", color=ACCENT, va="top")
    ax.text(0.6, 1.78,
            "① 参考必须与疾病身份匹配（肝组织不能用结直肠参考）　② 8 µm bin ≠ 单细胞，仅用于空间验证\n"
            "③ 无病理/CNV 时恶性一律写“候选”　④ 单对样本只做描述性比较，不做组间显著性",
            fontsize=8.8, color=TEXT, va="top", linespacing=1.7)

    out = Path(__file__).resolve().parent / "images" / "framework.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
