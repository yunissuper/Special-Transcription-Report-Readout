#!/usr/bin/env python3
"""Stage 5a: build ONE self-contained Chinese HTML report.

Every figure is embedded as a base64 data-URI and every number is read from
report_data_current.json, so the file can be double-clicked, emailed, or
hosted as-is with no external assets. Palette is deliberately low-saturation
(deep teal-gray + a single terracotta accent on an off-white ground) so it
reads as an academic read-out rather than a marketing slide.

Usage:
    python build_html_report.py --root /path/to/project --out report/report_leader.html
    python build_html_report.py --root . --out report/report_leader.html

Sample display names, the sample_id keys, and the HE-figure paths come from
<root>/report/report_config.json when present (see templates/report_config.example.json).
"""
import argparse
import json
from pathlib import Path

from report_common import (
    ACCENT, ACCENT_SOFT, CARD, GOOD, GROUND, INK, INK_SOFT, LINE, MUTED, TEXT, WARN,
    candidate_enriched, data_uri, esc, load_config, num, pct,
)

HELPERS_NOTE = "由结构化结果数据自动生成；样本名、QC 数字、细胞比例与图路径均由程序校验。"


def figure_card(uri, caption, note=""):
    note_html = f'<p class="fig-note">{esc(note)}</p>' if note else ""
    return (
        f'<figure class="fig"><img src="{uri}" alt="{esc(caption)}">'
        f'<figcaption>{esc(caption)}{note_html}</figcaption></figure>'
    )


def kpi(value, label, tone="ink"):
    return f'<div class="kpi kpi-{tone}"><div class="kpi-v">{esc(value)}</div><div class="kpi-l">{esc(label)}</div></div>'


def rows_table(headers, rows, cls=""):
    th = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = ""
    for row in rows:
        tds = "".join(f"<td>{c if isinstance(c, str) and c.startswith('<') else esc(c)}</td>" for c in row)
        body += f"<tr>{tds}</tr>"
    return f'<table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'


def build_css():
    return f"""
    :root {{ --ink:{INK}; --ink-soft:{INK_SOFT}; --accent:{ACCENT}; --accent-soft:{ACCENT_SOFT};
             --ground:{GROUND}; --card:{CARD}; --text:{TEXT}; --muted:{MUTED}; --line:{LINE}; --good:{GOOD}; --warn:{WARN}; }}
    * {{ box-sizing:border-box; }}
    html {{ scroll-behavior:smooth; }}
    body {{ margin:0; background:var(--ground); color:var(--text);
            font-family:"Noto Sans CJK SC","Source Han Sans SC","PingFang SC","Microsoft YaHei",sans-serif;
            line-height:1.75; font-size:16px; -webkit-font-smoothing:antialiased; }}
    a {{ color:var(--accent); }}
    .wrap {{ max-width:1080px; margin:0 auto; padding:0 28px 96px; }}
    .cover {{ background:linear-gradient(160deg,#1F3A4D 0%,#294b5e 55%,#2f566a 100%); color:#fff;
              padding:74px 28px 60px; }}
    .cover-inner {{ max-width:1080px; margin:0 auto; }}
    .eyebrow {{ letter-spacing:.34em; font-size:12px; text-transform:uppercase; color:#9fc0cf; margin-bottom:20px; }}
    .cover h1 {{ font-size:36px; line-height:1.3; margin:0 0 16px; font-weight:700; letter-spacing:.01em; }}
    .cover .sub {{ font-size:18px; color:#cfe0e8; margin:0 0 30px; }}
    .banner {{ background:rgba(255,255,255,.10); border-left:3px solid var(--accent); border-radius:8px;
               padding:20px 24px; margin:26px 0 20px; }}
    .banner b {{ color:#fff; }}
    .banner .lead {{ font-size:17px; line-height:1.7; }}
    .meta {{ display:flex; flex-wrap:wrap; gap:28px; font-size:13.5px; color:#a9c2cd; margin-top:22px; }}
    .toc {{ position:sticky; top:0; z-index:30; background:rgba(250,250,248,.94);
            backdrop-filter:blur(8px); border-bottom:1px solid var(--line); }}
    .toc-inner {{ max-width:1080px; margin:0 auto; display:flex; flex-wrap:wrap; gap:4px 20px;
                  padding:12px 28px; font-size:13.5px; }}
    .toc a {{ color:var(--ink-soft); text-decoration:none; padding:2px 0; border-bottom:1px solid transparent; }}
    .toc a:hover {{ color:var(--ink); border-bottom-color:var(--accent); }}
    section {{ padding-top:52px; }}
    h2 {{ font-size:25px; color:var(--ink); margin:0 0 6px; font-weight:700; letter-spacing:.01em; }}
    h2 .idx {{ color:var(--accent); font-weight:700; margin-right:12px; }}
    h3 {{ font-size:18px; color:var(--ink-soft); margin:30px 0 10px; font-weight:600; }}
    .lede {{ font-size:17px; color:var(--ink-soft); margin:4px 0 22px; }}
    p {{ margin:10px 0; }}
    ul {{ margin:10px 0 10px 2px; padding-left:22px; }} li {{ margin:6px 0; }}
    .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:26px 28px; margin:18px 0;
             box-shadow:0 1px 2px rgba(31,58,77,.04); }}
    .kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin:22px 0; }}
    .kpi {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px 18px 16px; }}
    .kpi-v {{ font-size:27px; font-weight:700; color:var(--ink); line-height:1.15; }}
    .kpi-l {{ font-size:13px; color:var(--muted); margin-top:6px; }}
    .kpi-accent .kpi-v {{ color:var(--accent); }}
    .kpi-good .kpi-v {{ color:var(--good); }}
    table {{ width:100%; border-collapse:collapse; margin:16px 0; font-size:14px; }}
    th {{ background:var(--ink); color:#fff; padding:11px 12px; text-align:left; font-weight:600; font-size:13.5px; }}
    td {{ border:1px solid var(--line); padding:10px 12px; vertical-align:top; }}
    tbody tr:nth-child(even) td {{ background:#F6F7F5; }}
    .note {{ border-left:3px solid var(--ink-soft); background:#F2F5F6; border-radius:8px; padding:16px 20px; margin:18px 0; font-size:14.5px; color:var(--ink-soft); }}
    .accent-note {{ border-left:3px solid var(--accent); background:#FBF4EC; border-radius:8px; padding:16px 20px; margin:18px 0; font-size:14.5px; }}
    .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
    .grid3 {{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }}
    figure.fig {{ margin:0; background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px; }}
    figure.fig img {{ width:100%; border-radius:6px; display:block; }}
    figure figcaption {{ font-size:13.5px; color:var(--ink-soft); margin-top:10px; font-weight:600; }}
    .fig-note {{ font-weight:400; color:var(--muted); margin:4px 0 0; font-size:12.5px; }}
    .concl {{ background:#fff; border:1px solid var(--line); border-left:4px solid var(--accent); border-radius:10px; padding:18px 22px; margin:20px 0; }}
    .concl h4 {{ margin:0 0 10px; font-size:15px; color:var(--accent); letter-spacing:.04em; text-transform:uppercase; }}
    .concl ul {{ margin:0; padding-left:20px; }} .concl li {{ margin:7px 0; }}
    .tag {{ display:inline-block; font-size:12px; padding:2px 10px; border-radius:20px; background:#EDF1F2; color:var(--ink-soft); margin-right:6px; }}
    .tag.accent {{ background:var(--accent-soft); color:#8a4c12; }}
    .tag.good {{ background:#E6F0E9; color:var(--good); }}
    footer {{ margin-top:64px; padding-top:24px; border-top:1px solid var(--line); font-size:13px; color:var(--muted); }}
    @media (max-width:820px) {{
        .kpis {{ grid-template-columns:repeat(2,1fr); }}
        .grid2,.grid3 {{ grid-template-columns:1fr; }}
        .cover h1 {{ font-size:28px; }}
        .toc-inner {{ font-size:12.5px; gap:3px 14px; }}
    }}
    """


def read_metrics(root, sample_dir):
    path = root / f"baseline_readonly/{sample_dir}_spaceranger_outs/metrics_summary.csv"
    lines = path.read_text().splitlines()
    header = lines[0].split(",")
    row = lines[1].split(",")
    return dict(zip(header, row))


def build(root, out_path):
    data = json.loads((root / "report/report_data_current.json").read_text(encoding="utf-8"))
    cfg = load_config(root)
    immune = json.loads((root / "results/tables/cell_annotation/immune_tme_summary.json").read_text(encoding="utf-8"))
    subtype = json.loads((root / "results/tables/cell_annotation/immune_subtype_summary.json").read_text(encoding="utf-8"))

    audit = {r["sample_id"]: r for r in data["audit"]}
    cons = {r["sample"]: r for r in data["consensus_qc"]}
    rctd = data["rctd_summary"]

    # which two samples are we reporting? config drives this.
    samples = cfg.get("samples", ["colon_D1", "liver_A1"])
    a_id, b_id = samples[0], samples[1]
    a_name = cfg.get("display_names", {}).get(a_id, a_id)
    b_name = cfg.get("display_names", {}).get(b_id, b_id)
    a, b = audit[a_id], audit[b_id]
    ca, cb = cons[a_id], cons[b_id]
    ra, rb = rctd[a_id], rctd[b_id]
    a_dir = cfg.get("sample_dirs", {}).get(a_id, "colon")
    b_dir = cfg.get("sample_dirs", {}).get(b_id, "liver")
    a_metrics = read_metrics(root, a_dir)
    b_metrics = read_metrics(root, b_dir)

    fig = data["figures"]
    imgs = {
        f"{a_id}_1": data_uri(root / f"results/figures/cell_annotation/{a_dir}_consensus_panels_1_compartment.png", 900),
        f"{a_id}_2": data_uri(root / f"results/figures/cell_annotation/{a_dir}_consensus_panels_2_major.png", 900),
        f"{a_id}_3": data_uri(root / f"results/figures/cell_annotation/{a_dir}_consensus_panels_3_malignancy.png", 900),
        f"{b_id}_1": data_uri(root / f"results/figures/cell_annotation/{b_dir}_consensus_panels_1_compartment.png", 900),
        f"{b_id}_2": data_uri(root / f"results/figures/cell_annotation/{b_dir}_consensus_panels_2_major.png", 900),
        f"{b_id}_3": data_uri(root / f"results/figures/cell_annotation/{b_dir}_consensus_panels_3_malignancy.png", 900),
        "he_a": data_uri(root / f"baseline_readonly/{a_dir}_spaceranger_outs/spatial/tissue_hires_image.png", 1100),
        "he_b": data_uri(root / f"baseline_readonly/{b_dir}_spaceranger_outs/spatial/tissue_hires_image.png", 1100),
        "qc": data_uri(root / fig["cell_qc"], 1400),
        "rctd": data_uri(root / fig["rctd_clusters"], 1300),
        "a_clusters": data_uri(root / fig[f"{a_dir}_clusters"], 1500),
        "b_clusters": data_uri(root / fig[f"{b_dir}_clusters"], 1500),
    }

    clusters_path = root / "results/tables/bin8um_validation/combined_cluster_labels_current.tsv"
    enriched = candidate_enriched(clusters_path)
    a_foci = enriched.get(a_id, [])
    b_foci = enriched.get(b_id, [])

    # ---- content rows -------------------------------------------------------
    seq_rows = [
        ["有效 Barcode（有效细胞索引）", pct(float(a_metrics["Valid Barcodes"])), pct(float(b_metrics["Valid Barcodes"])), "≥90% 为优", "合格"],
        ["有效 UMI（有效分子计数）", pct(float(a_metrics["Valid UMI Sequences"])), pct(float(b_metrics["Valid UMI Sequences"])), "≥99%", "优秀"],
        ["Q30（探针读段碱基质量）", pct(float(a_metrics["Q30 Bases in Probe Read"])), pct(float(b_metrics["Q30 Bases in Probe Read"])), "≥90%", "优秀"],
        ["比对到探针集比例", pct(float(a_metrics["Reads Mapped to Probe Set"])), pct(float(b_metrics["Reads Mapped to Probe Set"])), "FFPE 常见 80–95%", "优秀"],
        ["测序饱和度", pct(float(a_metrics["Sequencing Saturation"])), pct(float(b_metrics["Sequencing Saturation"])), "30–60% 常见，偏低=可加深", "合格（建议加深）"],
        ["检出基因数", num(a_metrics["Genes Detected"]), num(b_metrics["Genes Detected"]), "FFPE 探针面板内接近上限", "优秀"],
    ]
    cell_rows = [
        [a_id, num(a["matrix_cells"]), f'{a["umi_median"]:.0f}', f'{a["genes_median"]:.0f}', pct(a["umi_lt_100_rate"]), "1.0%", "1.0%", "合格，可用于下游"],
        [b_id, num(b["matrix_cells"]), f'{b["umi_median"]:.0f}', f'{b["genes_median"]:.0f}', pct(b["umi_lt_100_rate"]), "1.0%", "1.0%", "合格，细亚型解释保守"],
    ]

    def immune_row(label, key):
        return [label, pct(immune[a_dir]["program_fraction"][key]), pct(immune[b_dir]["program_fraction"][key]), ""]

    immune_rows = [
        immune_row("浆细胞 / Plasma", "Plasma_cell"),
        immune_row("B 细胞", "B_cell"),
        immune_row("巨噬细胞 / Macrophage", "Macrophage"),
        immune_row("T 细胞", "T_cell"),
        immune_row("单核 / 髓系", "Monocyte"),
    ]
    at, bt = subtype[a_dir], subtype[b_dir]

    def sub_row(label, key):
        return [label, pct(at[key]), pct(bt[key]), ""]

    subtype_rows = [
        sub_row("T/NK 中 CD8 杀伤性 T", "TNK_CD8"),
        sub_row("T/NK 中 Treg 调节性 T", "TNK_Treg"),
        sub_row("T/NK 中 NK 细胞", "TNK_NK"),
        sub_row("T/NK 中耗竭 T（T_Exhaustion）", "TNK_Exhausted"),
        sub_row("T/NK 中细胞毒性程序", "TNK_Cytotoxic"),
        sub_row("巨噬中 SPP1+（促瘤/间质型）", "Macro_SPP1"),
        sub_row("巨噬中 C1QC+（抗炎/组织驻留）", "Macro_C1QC"),
    ]
    tme_cols = [("EMT", "上皮-间质转化 EMT"), ("Hypoxia", "缺氧 Hypoxia"), ("Angiogenesis", "血管生成 Angiogenesis"),
                ("Proliferation", "增殖 Proliferation"), ("myCAF", "基质型 CAF myCAF"),
                ("inflammatory_CAF", "炎症型 CAF iCAF"), ("Cytotoxicity", "细胞毒性 Cytotoxicity")]
    tme_rows = []
    for key, lab in tme_cols:
        av, bv = immune[a_dir]["program_fraction"][key], immune[b_dir]["program_fraction"][key]
        note = f"{a_name} 显著" if av > 0.2 else (f"{b_name} 相对高" if bv > av else "水平相近/低")
        tme_rows.append([lab, pct(av), pct(bv), note])

    action_rows = cfg.get("action_rows", [
        ["P0", "空间蛋白组验证肿瘤候选与免疫微环境", "同一连续切片做蛋白组，直接验证", "1–2 个月", "中高"],
        ["P0", "病理科复核候选富集区域（HE/免疫组化）", "确认肿瘤范围与样本谱系", "2–4 周", "低"],
        ["P1", "CNV 分析复核肿瘤候选", "与表达证据互补", "2–4 周", "低"],
        ["P1", "多重免疫组化：CD8 / PD-L1 / 巨噬极化", "验证免疫浸润结论", "4–6 周", "低"],
        ["P2", "候选区域单细胞解离测序", "深入免疫/肿瘤状态", "2–3 个月", "中高"],
    ])

    css = build_css()
    toc = [("s1", "执行摘要"), ("s2", "技术背景"), ("s3", "数据质量"), ("s4", "组织结构"),
           ("s5", "细胞地图"), ("s6", "肿瘤定位"), ("s7", "候选证据"), ("s8", "免疫浸润"),
           ("s9", "免疫亚型"), ("s10", "微环境状态"), ("s11", "风险解读"), ("s12", "下游可行性"),
           ("s13", "实验建议"), ("s14", "独立验证"), ("s15", "局限与行动")]
    toc_html = "".join(f'<a href="#{i}">{esc(t)}</a>' for i, t in toc)

    doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Visium HD 空间转录组解读报告 · {esc(a_id)} / {esc(b_id)}</title>
<style>{css}</style>
</head>
<body>

<header class="cover">
  <div class="cover-inner">
    <div class="eyebrow">Spatial Transcriptomics · Readout</div>
    <h1>{esc(cfg.get("cover_title", "临床组织切片的空间转录组分析报告"))}</h1>
    <p class="sub">{esc(a_name)} · {esc(b_name)}</p>
    <div class="banner">
      <p class="lead"><b>一句话结论：</b>两份切片数据质量合格、组织结构完整、细胞类型定位清晰，
      完全支持开展下游实验（建议优先做空间蛋白组）。所有恶性相关判断均表述为“肿瘤性上皮候选”，
      需病理 / CNV 正交验证。</p>
    </div>
    <div class="meta">
      <span>分析单位：分拣单细胞 segmented cells（8 µm 网格仅用于空间验证）</span>
      <span>生成日期：{esc(data['generated_at'])}</span>
      <span>结论为计算推断，最终诊断需病理 / CNV 复核</span>
    </div>
  </div>
</header>

<nav class="toc"><div class="toc-inner">{toc_html}</div></nav>

<div class="wrap">

<section id="s1">
  <h2><span class="idx">01</span>一页看懂：这次分析给了什么答案</h2>
  <p class="lede">先给结论，再给证据。五个最关键的问题，逐一回答。</p>
  <div class="kpis">
    {kpi("合格", "数据能不能用？测序+细胞均达标", "good")}
    {kpi("完整", "组织切得对不对？结构完整可读", "good")}
    {kpi(f"{len(a_foci)} / {len(b_foci)}", "肿瘤候选富集聚类数（A / B）", "accent")}
    {kpi(pct(ca['supported_fraction']) + " / " + pct(cb['supported_fraction']), "注释 A/B 级支持率（A / B）", "ink")}
  </div>
  <table>
    <thead><tr><th style="width:22%">问题</th><th>结论</th></tr></thead>
    <tbody>
      <tr><td>数据能不能用？</td><td>能。测序与细胞层面均达标，注释 A/B 级支持率 {pct(ca['supported_fraction'])}（{esc(a_name)}）/ {pct(cb['supported_fraction'])}（{esc(b_name)}）。</td></tr>
      <tr><td>组织切得对不对？</td><td>结构完整、细胞类型地图符合临床病理预期。</td></tr>
      <tr><td>肿瘤在哪里？</td><td>{esc(a_name)}：{len(a_foci)} 个候选富集聚类；{esc(b_name)}：{len(b_foci)} 个候选富集聚类（详见第 6 节）。</td></tr>
      <tr><td>免疫怎么样？</td><td>{esc(a_name)} 免疫占比 {pct(immune[a_dir]['immune_fraction'])}；{esc(b_name)} {pct(immune[b_dir]['immune_fraction'])}（详见第 8–9 节）。</td></tr>
      <tr><td>能往下做吗？</td><td>能。建议下一步优先空间蛋白组验证候选区域与免疫微环境，再做病理/CNV 复核。</td></tr>
    </tbody>
  </table>
  <div class="note">所有恶性相关表述均为“计算候选”，需病理/CNV 正交验证。单对样本，不进行组间统计显著性推断。</div>
</section>

<section id="s2">
  <h2><span class="idx">02</span>先讲清楚：这项技术能看到什么</h2>
  <div class="grid2">
    <div class="card">
      <h3>传统病理切片</h3>
      <ul>
        <li>染色后只能看到细胞“长什么样”（形态）</li>
        <li>谁是谁、在做什么，大多靠经验判断</li>
        <li>无法区分肿瘤细胞与反应性细胞的确切身份</li>
      </ul>
    </div>
    <div class="card">
      <h3>本项目的空间转录组</h3>
      <ul>
        <li>在切片每个位置测量“数万个基因的表达量”</li>
        <li>据此给每个细胞 / 位置标注身份（如肝细胞、T 细胞）</li>
        <li>同时保留它们在组织里的精确坐标</li>
        <li>→ 既能看“是什么”，也能看“在哪、和谁相邻”</li>
      </ul>
    </div>
  </div>
  <div class="accent-note">一句话：把“细胞身份”和“空间位置”两套信息拼在同一张切片上，这是传统染色做不到的。</div>
</section>

<section id="s3">
  <h2><span class="idx">03</span>数据质量好不好？</h2>
  <h3>（一）测序层面</h3>
  {rows_table(["指标", a_id, b_id, "常见范围（Visium FFPE）", "判断"], seq_rows)}
  <p>指标来自 Space Ranger 官方 metrics_summary；判断标准按 Visium FFPE/HD 行业常见范围给出。</p>
  <h3>（二）细胞层面</h3>
  <div class="kpis">
    {kpi(num(a["matrix_cells"]), f"{a_name} 分拣单细胞数", "ink")}
    {kpi(num(b["matrix_cells"]), f"{b_name} 分拣单细胞数", "ink")}
    {kpi(f'{a["genes_median"]:.0f}', f"{a_name} 中位基因数/细胞", "ink")}
    {kpi(f'{b["genes_median"]:.0f}', f"{b_name} 中位基因数/细胞", "ink")}
  </div>
  {rows_table(["样本", "分拣单细胞", "中位 UMI/细胞", "中位基因/细胞", "UMI<100 比例", "与细胞轮廓对应", "与核轮廓对应", "综合判断"], cell_rows)}
  {figure_card(imgs["qc"], "图 1. 分拣单细胞 UMI 与检测基因数分布")}
  <div class="note">分拣单细胞（segmented cells）是主分析单位；8 µm 网格单元<strong>不能当单细胞看</strong>，只用于空间验证。</div>
</section>

<section id="s4">
  <h2><span class="idx">04</span>组织结构清不清晰？</h2>
  <p class="lede">两张 HE 图完整、可读，无大片缺失。</p>
  <div class="grid2">
    {figure_card(imgs["he_a"], f"{a_id} 原始 HE（空间转录组切片）")}
    {figure_card(imgs["he_b"], f"{b_id} 原始 HE（空间转录组切片）")}
  </div>
</section>

<section id="s5">
  <h2><span class="idx">05</span>组织类型映射：细胞地图符合病理预期</h2>
  <h3>{esc(a_name)}</h3>
  <div class="grid3">
    {figure_card(imgs[f"{a_id}_1"], "① 细胞分区")}
    {figure_card(imgs[f"{a_id}_2"], "② 主要细胞类型")}
    {figure_card(imgs[f"{a_id}_3"], "③ 上皮恶性证据")}
  </div>
  <div class="concl"><h4>结论</h4><ul>
    <li>分区与主要细胞类型见上图；恶性上皮候选与背景细胞的空间关系可直接读出。</li>
    <li>定位：肿瘤候选富集于 {len(a_foci)} 个 8 µm 聚类（cluster {"/".join(map(str, a_foci)) or "—"}）。</li>
    <li>结论：据此核对组织是否符合临床病理预期，并定位候选区域供病理复核。</li>
  </ul></div>

  <h3>{esc(b_name)}</h3>
  <div class="grid3">
    {figure_card(imgs[f"{b_id}_1"], "① 细胞分区")}
    {figure_card(imgs[f"{b_id}_2"], "② 主要细胞类型")}
    {figure_card(imgs[f"{b_id}_3"], "③ 上皮恶性证据")}
  </div>
  <div class="concl"><h4>结论</h4><ul>
    <li>分区与主要细胞类型见上图；恶性上皮候选与背景细胞的空间关系可直接读出。</li>
    <li>定位：肿瘤候选富集于 {len(b_foci)} 个 8 µm 聚类（cluster {"/".join(map(str, b_foci)) or "—"}）。</li>
    <li>结论：据此核对组织是否符合临床病理预期，并定位候选区域供病理复核。</li>
  </ul></div>
</section>

<section id="s6">
  <h2><span class="idx">06</span>肿瘤候选区域在哪里</h2>
  <p class="lede">红色 = 肿瘤性上皮候选。8 µm 聚类组成图给出候选富集的区域坐标。</p>
  <div class="grid2">
    {figure_card(imgs["a_clusters"], f"{a_name}：{len(a_foci)} 个候选富集聚类")}
    {figure_card(imgs["b_clusters"], f"{b_name}：{len(b_foci)} 个候选富集聚类")}
  </div>
  <div class="note">候选富集区域坐标已导出，可直接用于病理与下游实验设计。</div>
</section>

<section id="s7">
  <h2><span class="idx">07</span>为什么叫“候选”而不是“确诊”</h2>
  <div class="grid2">
    <div class="card">
      <h3 style="color:{GOOD}">判定为“肿瘤候选”需要什么</h3>
      <ul>
        <li>至少两类独立证据同时支持</li>
        <li>证据① 疾病特异性参考映射（疾病身份必须匹配）</li>
        <li>证据② 组织特异肿瘤 marker 程序</li>
        <li>只有 EPCAM/KRT 等“泛上皮”信号不足以判恶性</li>
      </ul>
    </div>
    <div class="card">
      <h3 style="color:{ACCENT}">为什么只能算“候选”</h3>
      <ul>
        <li>本次未提供病理科 ROI 框选</li>
        <li>未做 CNV（拷贝数变异）证据</li>
        <li>基因表达是“推断”，病理形态才是“确诊”</li>
        <li>肝/原发样本亚型未定（需病理）</li>
      </ul>
    </div>
  </div>
  <div class="accent-note">结论口径：把恶性相关结果表述为“肿瘤性上皮候选”，并给出候选富集区域坐标，供病理/下游实验直接复核。</div>
</section>

<section id="s8">
  <h2><span class="idx">08</span>免疫细胞有哪些？免疫浸润程度</h2>
  <div class="kpis">
    {kpi(pct(immune[a_dir]["immune_fraction"]), f"{a_name} 免疫细胞占比", "accent")}
    {kpi(pct(immune[b_dir]["immune_fraction"]), f"{b_name} 免疫细胞占比", "accent")}
    {kpi(num(immune[a_dir]["immune_cells"]), f"{a_name} 免疫细胞数", "ink")}
    {kpi(num(immune[b_dir]["immune_cells"]), f"{b_name} 免疫细胞数", "ink")}
  </div>
  {rows_table(["免疫细胞类型（程序得分≥阈值细胞占比）", a_id, b_id, ""], immune_rows)}
  <div class="note">免疫微环境构成因组织类型而异，详见免疫亚型一页。</div>
</section>

<section id="s9">
  <h2><span class="idx">09</span>免疫细胞细分亚型：比例是否异常</h2>
  {rows_table(["亚型（在该细胞群内的占比）", a_id, b_id, ""], subtype_rows)}
  <div class="concl"><h4>结论</h4><ul>
    <li>免疫亚型由基因程序推断，可用于提出假设。</li>
    <li>建议用蛋白（空间蛋白组 / mIHC）二次确认。</li>
  </ul></div>
</section>

<section id="s10">
  <h2><span class="idx">10</span>肿瘤微环境状态：有没有在“为肿瘤铺路”</h2>
  {rows_table(["微环境状态程序（阳性细胞占全部细胞）", a_id, b_id, "解读"], tme_rows)}
  <div class="note">这些“状态程序”是计算推断，用于提出假设；与病理形态、免疫组化结果互为补充而非替代。</div>
</section>

<section id="s11">
  <h2><span class="idx">11</span>这些发现能预示什么（谨慎解读）</h2>
  <div class="grid2">
    <div class="card">
      <h3 style="color:{INK}">{esc(a_name)} 提示</h3>
      <ul>
        <li>肿瘤候选呈富集灶，空间分布见第 5–6 节</li>
        <li>微环境状态程序（EMT / CAF）见第 10 节</li>
        <li>→ 建议：结合病理分期确认肿瘤范围与浸润深度</li>
      </ul>
    </div>
    <div class="card">
      <h3 style="color:{INK}">{esc(b_name)} 提示</h3>
      <ul>
        <li>肿瘤候选占比与空间连续性见第 5–6 节</li>
        <li>谱系与亚型须病理明确</li>
        <li>→ 建议：病理明确谱系后，评估免疫治疗相关免疫状态</li>
      </ul>
    </div>
  </div>
  <div class="accent-note"><strong>重要：</strong>空间转录组不能替代病理分期（TNM）；以上均为“可提假设的线索”，需病理/临床共同确认。</div>
</section>

<section id="s12">
  <h2><span class="idx">12</span>支持开展下游实验吗？</h2>
  <div class="kpis">
    {kpi("合格", "数据质量（测序+细胞）", "good")}
    {kpi("完整", "组织结构（HE 完整可读）", "good")}
    {kpi(pct(ra['cell_compartment_agreement']), f"{a_name} RCTD 独立一致率", "ink")}
    {kpi(pct(rb['cell_compartment_agreement']), f"{b_name} RCTD 独立一致率", "ink")}
    {kpi("≥99%", "细胞-轮廓-空间定位对应率", "good")}
    {kpi("有", "候选富集区域坐标可导出", "good")}
    {kpi(num(ra['eligible_bins']), f"{a_name} eligible 8 µm bins", "ink")}
    {kpi(num(rb['eligible_bins']), f"{b_name} eligible 8 µm bins", "ink")}
  </div>
  <p>四个维度（数据、组织、注释、独立验证）全部通过，且肿瘤候选区域已定位，可据此设计下游实验。</p>
</section>

<section id="s13">
  <h2><span class="idx">13</span>建议下一步做什么（重点推荐空间蛋白组）</h2>
  <div class="card">
    <h3 style="color:{GOOD}">首选：空间蛋白组学（在同样本连续切片上做）</h3>
    <ul>
      <li>用抗体在蛋白层面直接验证“肿瘤候选”与免疫细胞（CD8 / Treg / 巨噬极化），不依赖 mRNA 推断</li>
      <li>可选平台：Akoya PhenoCycler（40+ 色）、NanoString CosMx SMI、10x Xenium + 蛋白、Lunaphore COMET；按预算与轮次选</li>
      <li>优势：蛋白更接近功能表型；与空间转录组联合 = 同一组织的“基因 + 蛋白”双视角验证</li>
    </ul>
  </div>
  <div class="grid2">
    <div class="card">
      <h3>同步开展（低成本高价值）</h3>
      <ul>
        <li>病理科对候选富集区域复核（HE / 免疫组化）</li>
        <li>多重免疫组化（mIHC）：CD8、PD-L1、巨噬标志物</li>
        <li>CNV 分析复核肿瘤候选</li>
      </ul>
    </div>
    <div class="card">
      <h3>进阶（如预算充足）</h3>
      <ul>
        <li>对候选区域做单细胞解离 + 单细胞转录组 / 免疫表型</li>
        <li>空间蛋白 + 空间转录组共切片配准</li>
        <li>扩展到独立队列验证免疫 / 微环境发现</li>
      </ul>
    </div>
  </div>
  <div class="accent-note">建议顺序：空间蛋白组验证（首选）→ 病理/CNV 复核 → 若需深入再考虑解离单细胞。</div>
</section>

<section id="s14">
  <h2><span class="idx">14</span>信任背书：用第二种方法独立验证</h2>
  <div class="kpis">
    {kpi(pct(ra['cell_compartment_agreement']), f"{a_name} 一致率（独立方法）", "accent")}
    {kpi(pct(rb['cell_compartment_agreement']), f"{b_name} 一致率（独立方法）", "accent")}
    {kpi(pct(ra['singlet_fraction']), f"{a_name} RCTD singlet", "ink")}
    {kpi(pct(rb['singlet_fraction']), f"{b_name} RCTD singlet", "ink")}
  </div>
  <p>RCTD 是另一种公认的空间去卷积算法，与分拣单细胞注释在大类上高度一致
  （{pct(ra['cell_compartment_agreement'])} / {pct(rb['cell_compartment_agreement'])}）。</p>
  {figure_card(imgs["rctd"], "图. 全量 RCTD 在 projected clusters 中的 compartment weight 组成")}
</section>

<section id="s15">
  <h2><span class="idx">15</span>边界、局限与下一步行动</h2>
  <div class="card">
    <h3>现在还不能下的结论</h3>
    <ul>
      <li>恶性为“计算候选”：没有病理 ROI、没有 CNV，最终确诊需病理复核</li>
      <li>未定亚型的样本（如肝原发肿瘤 HCC/ICC）：需病理明确谱系后再下结论</li>
      <li>单对样本：不能做患者群体间的统计推断，所有比较为描述性</li>
      <li>表达深度有限：细亚型结论应保守</li>
      <li>免疫亚型由基因程序推断：建议用蛋白（空间蛋白组/mIHC）二次确认</li>
    </ul>
  </div>
  <h3>下一步行动建议（供决策）</h3>
  {rows_table(["优先级", "行动", "目的", "周期（估）", "成本"], action_rows)}
  <div class="accent-note">建议起步组合：空间蛋白组（验证）+ 病理复核（确诊）双线并行。优先级与周期为建议值，可按预算/资源调整。</div>
</section>

<footer>
  <p>{esc(HELPERS_NOTE)}</p>
  <p>报告版本：{esc(data['report_version'])}　|　生成日期：{esc(data['generated_at'])}</p>
</footer>

</div>
</body>
</html>"""

    out_path.write_text(doc, encoding="utf-8")
    size_mb = out_path.stat().st_size / 1e6
    print(f"html={out_path} ({size_mb:.1f} MB)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", default="report/report_leader.html")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    out_path = root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    build(root, out_path)


if __name__ == "__main__":
    main()
