#!/usr/bin/env python3
"""Per-sample 3-panel consensus figure: SHORT labels, legends BELOW each map.

Why this exists: putting a sentence-length legend to the RIGHT of a tissue map
squeezes the map into a sliver -- unreadable once it lands in a PPT. This
generator keeps the map on top and a compact two-column legend underneath, with
short bilingual labels, so each panel fills its frame.

Outputs, per sample, four images:
    <stem>_1_compartment.png   compartment (epithelial/immune/stromal/...)
    <stem>_2_major.png         top-N major cell types + other
    <stem>_3_malignancy.png    epithelial malignancy evidence
    <stem>.png                 wide composite of the three (for HTML)

Usage:
    python plot_consensus_panels.py \
        --consensus <sample>_disease_consensus_current.tsv.gz \
        --coordinates <sample>_cell_coordinates.tsv \
        --sample colon_D1 \
        --output results/figures/cell_annotation/colon_consensus_panels.png

The label/colour dictionaries below are the project-neutral defaults. Copy this
file into a project and edit the *_LABELS maps to match that project's ontology
-- that is the intended customisation point.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK JP", "Noto Sans CJK SC", "WenQuanYi Zen Hei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


COMPARTMENT_LABELS = {
    "Epithelial": "上皮 Epithelial", "Immune": "免疫 Immune", "Stromal": "间质 Stromal",
    "Endothelial": "内皮 Endothelial", "Unknown": "未知 Unknown",
}
COMPARTMENT_COLORS = {
    "Epithelial": "#d73027", "Immune": "#4575b4", "Stromal": "#66a61e",
    "Endothelial": "#984ea3", "Unknown": "#bdbdbd",
}

MAJOR_LABELS = {
    "Hepatocyte": "肝细胞 Hepatocyte", "Liver cancer epithelium candidate": "肝癌上皮候选",
    "Liver epithelium": "肝上皮 Liver epi.", "Cholangiocyte": "胆管细胞 Cholangio.",
    "Fibroblast": "成纤维 Fibroblast", "Hepatic stellate cell": "肝星状 HSC",
    "Myofibroblast": "肌成纤维 MyoFB", "Pericyte": "周细胞 Pericyte", "VSMC": "血管平滑肌 VSMC",
    "Endothelial": "内皮 Endothelial", "LSEC": "肝窦内皮 LSEC", "Macrophage": "巨噬 Macrophage",
    "Kupffer cell": "枯否 Kupffer", "Monocyte": "单核 Monocyte", "Myeloid": "髓系 Myeloid",
    "Dendritic cell": "树突 DC", "Neutrophil": "中性粒 Neutrophil", "Mast cell": "肥大 Mast",
    "Eosinophil": "嗜酸 Eosinophil", "Granulocyte": "粒细胞 Granulocyte", "ILC": "先天淋巴 ILC",
    "NK cell": "NK 细胞", "T cell": "T 细胞", "T/NK cell": "T/NK 细胞", "B cell": "B 细胞",
    "Plasma cell": "浆细胞 Plasma", "Red blood cell": "红细胞 RBC", "Schwann cell": "施万 Schwann",
    "Mesothelial cell": "间皮 Mesothelial", "Colon epithelium": "结肠上皮 Colon epi.",
    "Normal colon epithelium": "正常结肠上皮", "CRC malignant candidate": "结肠恶性上皮候选",
    "Goblet cell": "杯状细胞 Goblet", "Enterocyte": "肠上皮 Enterocyte",
    "Unknown": "未知/其他 Other", "Other/Unknown": "未知/其他 Other",
}

MALIGN_STATUS_LABELS = {
    "CRC malignant candidate - disease reference and CRC marker supported; pathology/CNV pending": "结肠恶性上皮候选（参考+marker支持，病理/CNV待定）",
    "Non-malignant colon epithelium supported": "非恶性结肠上皮（已支持）",
    "Indeterminate epithelial - insufficient malignant evidence": "上皮·待定（恶性证据不足）",
    "Indeterminate epithelial - pathology/CNV pending": "上皮·待定（病理/CNV待定）",
    "Liver cancer epithelium candidate - hepatocyte-lineage epithelial identity with liver-cancer reference support; HCC-vs-ICC subtype and pathology/CNV not resolved, spatial tumour boundary not established": "肝癌上皮候选（肝细胞谱系，HCC/ICC待定）",
    "Non-malignant hepatocyte supported": "非恶性肝细胞（已支持）",
    "Non-malignant cholangiocyte supported": "非恶性胆管细胞（已支持）",
    "Indeterminate liver epithelium - neoplastic signal without a hepatocyte/biliary identity program": "肝上皮·待定（有肿瘤信号，无肝细胞/胆管身份）",
    "Indeterminate epithelial - liver tumour subtype and pathology/CNV pending": "肝上皮·待定（亚型与病理/CNV待定）",
    "Not applicable - non-epithelial": "非上皮（不适用）",
    "Not assessed - compartment unresolved": "未评估（分区未定）",
}

MALIGN_COLORS = {
    "结肠恶性上皮候选（参考+marker支持，病理/CNV待定）": "#b2182b",
    "肝癌上皮候选（肝细胞谱系，HCC/ICC待定）": "#b2182b",
    "非恶性结肠上皮（已支持）": "#2166ac",
    "非恶性肝细胞（已支持）": "#1b7837",
    "非恶性胆管细胞（已支持）": "#238b45",
    "上皮·待定（恶性证据不足）": "#ef8a62",
    "上皮·待定（病理/CNV待定）": "#fddbc7",
    "肝上皮·待定（有肿瘤信号，无肝细胞/胆管身份）": "#ef8a62",
    "肝上皮·待定（亚型与病理/CNV待定）": "#fddbc7",
    "非上皮（不适用）": "#bdbdbd",
    "未评估（分区未定）": "#e6e6e6",
}

MAJOR_PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#17becf", "#bcbd22", "#7f7f7f",
]


def draw_panel(axis, frame, category_col, label_map, colors, top_n=None):
    counts = frame[category_col].value_counts()
    if top_n is not None and len(counts) > top_n:
        keep = counts.head(top_n).index
        frame = frame.copy()
        frame[category_col] = frame[category_col].where(frame[category_col].isin(keep), "Other/Unknown")
        counts = frame[category_col].value_counts()
    order = list(counts.index[::-1])  # rare first so frequent sit on top
    handles = []
    for label in order:
        subset = frame[frame[category_col].eq(label)]
        pretty = label_map.get(label, label)
        color = colors.get(pretty, colors.get(label, "#969696"))
        axis.scatter(subset["cell_x_pixel"], subset["cell_y_pixel"],
                     s=0.30, color=color, linewidths=0, rasterized=True)
        handles.append((color, f"{pretty} ({len(subset):,})"))
    axis.set_aspect("equal")
    axis.invert_yaxis()
    axis.axis("off")
    return handles


def add_legend_below(axis, handles, ncol=2, fontsize=7.5):
    import matplotlib.patches as mpatches
    proxies = [mpatches.Patch(color=color, label=txt) for color, txt in handles]
    axis.legend(handles=proxies, loc="upper center", bbox_to_anchor=(0.5, -0.01),
                ncol=ncol, frameon=False, fontsize=fontsize, handlelength=1.1,
                handleheight=0.9, columnspacing=1.0, labelspacing=0.35, borderaxespad=0.0)


def make_panel(frame, column, label_map, colors, title, out_path,
               legend_ncol=2, legend_font=8.0, top_n=None):
    import matplotlib.patches as mpatches
    figure = plt.figure(figsize=(5.0, 6.0))
    grid = figure.add_gridspec(2, 1, height_ratios=[5.6, 1.7], hspace=0.02)
    axis = figure.add_subplot(grid[0])
    legend_axis = figure.add_subplot(grid[1])
    legend_axis.axis("off")
    handles = draw_panel(axis, frame, column, label_map, colors, top_n=top_n)
    axis.set_title(title, fontsize=12.5, pad=6)
    proxies = [mpatches.Patch(color=color, label=txt) for color, txt in handles]
    legend_axis.legend(handles=proxies, loc="upper center", ncol=legend_ncol, frameon=False,
                       fontsize=legend_font, handlelength=1.1, handleheight=0.9,
                       columnspacing=1.0, labelspacing=0.4, borderaxespad=0.0)
    figure.savefig(out_path, dpi=250, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--consensus", required=True)
    parser.add_argument("--coordinates", required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--malign-column", default="malignant_status")
    args = parser.parse_args()

    consensus = pd.read_csv(
        args.consensus, sep="\t",
        usecols=["barcode", "consensus_compartment", "consensus_major_cell_type", args.malign_column],
    )
    coordinates = pd.read_csv(args.coordinates, sep="\t", usecols=["barcode", "cell_x_pixel", "cell_y_pixel"])
    frame = consensus.merge(coordinates, on="barcode", how="left", validate="one_to_one")
    rate = frame[["cell_x_pixel", "cell_y_pixel"]].notna().all(axis=1).mean()
    if rate < 0.99:
        raise ValueError(f"Coordinate match rate below 99%: {rate:.4f}")
    frame = frame.dropna(subset=["cell_x_pixel", "cell_y_pixel"])

    supported = frame["consensus_compartment"].ne("Unknown")
    major_counts = frame.loc[supported, "consensus_major_cell_type"].value_counts()
    top_major = list(major_counts.head(9).index)
    frame["major_plot"] = frame["consensus_major_cell_type"].where(
        frame["consensus_major_cell_type"].isin(top_major), "Other/Unknown")
    major_colors = {MAJOR_LABELS.get(l, l): MAJOR_PALETTE[i % len(MAJOR_PALETTE)] for i, l in enumerate(top_major)}
    major_colors[MAJOR_LABELS["Other/Unknown"]] = "#d9d9d9"

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stem = out_path.with_suffix("")

    make_panel(frame, "consensus_compartment", COMPARTMENT_LABELS, COMPARTMENT_COLORS,
               "① 细胞分区 Compartment", f"{stem}_1_compartment.png", legend_ncol=2)
    make_panel(frame, "major_plot", MAJOR_LABELS, major_colors,
               "② 主要细胞类型 Major cell type", f"{stem}_2_major.png", legend_ncol=2)
    make_panel(frame, args.malign_column, MALIGN_STATUS_LABELS, MALIGN_COLORS,
               "③ 上皮恶性证据 Epithelial malignancy", f"{stem}_3_malignancy.png",
               legend_ncol=1, legend_font=7.5)

    figure, axes = plt.subplots(1, 3, figsize=(16.5, 6.6))
    h0 = draw_panel(axes[0], frame, "consensus_compartment", COMPARTMENT_LABELS, COMPARTMENT_COLORS)
    axes[0].set_title("① 细胞分区 Compartment", fontsize=13, pad=6)
    add_legend_below(axes[0], h0, ncol=2)
    h1 = draw_panel(axes[1], frame, "major_plot", MAJOR_LABELS, major_colors)
    axes[1].set_title("② 主要细胞类型 Major cell type", fontsize=13, pad=6)
    add_legend_below(axes[1], h1, ncol=2)
    h2 = draw_panel(axes[2], frame, args.malign_column, MALIGN_STATUS_LABELS, MALIGN_COLORS)
    axes[2].set_title("③ 上皮恶性证据 Epithelial malignancy evidence", fontsize=13, pad=6)
    add_legend_below(axes[2], h2, ncol=1, fontsize=7.0)
    figure.suptitle(f"{args.sample}：分拣单细胞疾病共识（疾病参考 + marker + UCell）", fontsize=15, y=1.0)
    figure.subplots_adjust(left=0.01, right=0.99, top=0.90, bottom=0.20, wspace=0.05)
    figure.savefig(args.output, dpi=250, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    print(f"cells={len(frame)} coordinate_rate={rate:.4f} output={args.output} (+3 panels)")


if __name__ == "__main__":
    main()
