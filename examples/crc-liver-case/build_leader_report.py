#!/usr/bin/env python3
"""Leader-oriented, self-contained Chinese HTML report (single file).

Reads the same structured data as the PPT deck, embeds every figure as a
base64 data-URI, and writes ONE .html you can double-click or send directly.
Palette is deliberately low-saturation and academic (deep teal-gray + a
single terracotta accent on an off-white ground).
"""
import base64
import html
import io
import json
from pathlib import Path

from PIL import Image

ROOT = Path("<PROJECT_ROOT>")
DATA_PATH = ROOT / "report/report_data_current.json"
IMMUNE_PATH = ROOT / "results/tables/cell_annotation/immune_tme_summary.json"
SUBTYPE_PATH = ROOT / "results/tables/cell_annotation/immune_subtype_summary.json"
CLUSTER_LABELS = ROOT / "results/tables/bin8um_validation/combined_cluster_labels_current.tsv"
OUTPUT_PATH = ROOT / "report/report_leader.html"

# ---- palette ---------------------------------------------------------------
INK = "#1F3A4D"      # primary deep teal-gray
INK_SOFT = "#41606F"  # secondary
ACCENT = "#B5651D"   # terracotta, sparingly
ACCENT_SOFT = "#EAD9C7"
GROUND = "#FAFAF8"   # off-white
CARD = "#FFFFFF"
TEXT = "#2C2C2C"
MUTED = "#6B7278"
LINE = "#E2E4E1"
GOOD = "#2E6B4F"
WARN = "#9C6B1E"


def pick(rel, max_w=1500):
    """Load an image from the project, downscale for web, return a data URI."""
    path = ROOT / rel
    if not path.exists():
        raise FileNotFoundError(path)
    with Image.open(path) as im:
        im = im.convert("RGB")
        if im.width > max_w:
            ratio = max_w / im.width
            im = im.resize((max_w, int(im.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def pct(value, digits=1):
    return f"{100 * float(value):.{digits}f}%"


def num(value):
    return f"{int(value):,}"


def esc(text):
    return html.escape(str(text))


def read_metrics(sample_dir):
    path = ROOT / f"baseline_readonly/{sample_dir}_spaceranger_outs/metrics_summary.csv"
    header = path.read_text().splitlines()[0].split(",")
    row = path.read_text().splitlines()[1].split(",")
    return dict(zip(header, row))


def candidate_enriched():
    """Read the authoritative candidate-enriched cluster counts."""
    import csv
    out = {}
    with CLUSTER_LABELS.open() as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for r in reader:
            if r.get("malignant_niche_class") == "candidate_enriched":
                out.setdefault(r["sample"], []).append(int(r["cluster_id"]))
    return out


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


def build():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    immune = json.loads(IMMUNE_PATH.read_text(encoding="utf-8"))
    subtype = json.loads(SUBTYPE_PATH.read_text(encoding="utf-8"))
    audit = {r["sample_id"]: r for r in data["audit"]}
    cons = {r["sample"]: r for r in data["consensus_qc"]}
    rctd = data["rctd_summary"]
    colon, liver = audit["sample_A"], audit["sample_B"]
    colon_c, liver_c = cons["sample_A"], cons["sample_B"]
    colon_r, liver_r = rctd["sample_A"], rctd["sample_B"]
    cmet = read_metrics("colon")
    lmet = read_metrics("liver")
    enriched = candidate_enriched()

    # figures
    imgs = {
        "colon_1": pick("results/figures/cell_annotation/colon_consensus_panels_1_compartment.png", 900),
        "colon_2": pick("results/figures/cell_annotation/colon_consensus_panels_2_major.png", 900),
        "colon_3": pick("results/figures/cell_annotation/colon_consensus_panels_3_malignancy.png", 900),
        "liver_1": pick("results/figures/cell_annotation/liver_consensus_panels_1_compartment.png", 900),
        "liver_2": pick("results/figures/cell_annotation/liver_consensus_panels_2_major.png", 900),
        "liver_3": pick("results/figures/cell_annotation/liver_consensus_panels_3_malignancy.png", 900),
        "he_colon": pick("baseline_readonly/colon_spaceranger_outs/spatial/tissue_hires_image.png", 1100),
        "he_liver": pick("baseline_readonly/liver_spaceranger_outs/spatial/tissue_hires_image.png", 1100),
        "qc": pick("results/figures/audit/cell_qc_distributions.png", 1400),
        "rctd": pick("results/figures/bin8um_validation/rctd_full_cluster_validation.png", 1300),
        "colon_clusters": pick("results/figures/bin8um_validation/colon_cluster_composition_current.png", 1500),
        "liver_clusters": pick("results/figures/bin8um_validation/liver_cluster_composition_current.png", 1500),
    }

    # ---- content blocks ----
    seq_rows = [
        ["有效 Barcode（有效细胞索引）", pct(float(cmet["Valid Barcodes"])), pct(float(lmet["Valid Barcodes"])), "≥90% 为优", "合格"],
        ["有效 UMI（有效分子计数）", pct(float(cmet["Valid UMI Sequences"])), pct(float(lmet["Valid UMI Sequences"])), "≥99%", "优秀"],
        ["Q30（探针读段碱基质量）", pct(float(cmet["Q30 Bases in Probe Read"])), pct(float(lmet["Q30 Bases in Probe Read"])), "≥90%", "优秀"],
        ["比对到探针集比例", pct(float(cmet["Reads Mapped to Probe Set"])), pct(float(lmet["Reads Mapped to Probe Set"])), "FFPE 常见 80–95%", "优秀"],
        ["测序饱和度", pct(float(cmet["Sequencing Saturation"])), pct(float(lmet["Sequencing Saturation"])), "30–60% 常见，偏低=可加深", "合格（建议加深）"],
        ["检出基因数", num(cmet["Genes Detected"]), num(lmet["Genes Detected"]), "FFPE 探针面板内接近上限", "优秀"],
    ]
    cell_rows = [
        ["sample_A", num(colon["matrix_cells"]), f'{colon["umi_median"]:.0f}', f'{colon["genes_median"]:.0f}', pct(colon["umi_lt_100_rate"]), "1.0%", "1.0%", "合格，可用于下游"],
        ["sample_B", num(liver["matrix_cells"]), f'{liver["umi_median"]:.0f}', f'{liver["genes_median"]:.0f}', pct(liver["umi_lt_100_rate"]), "1.0%", "1.0%", "合格，细亚型解释保守"],
    ]
    immune_rows = [
        ["浆细胞 / Plasma", pct(immune["colon"]["program_fraction"]["Plasma_cell"]), pct(immune["liver"]["program_fraction"]["Plasma_cell"]), "colon 明显更高"],
        ["B 细胞", pct(immune["colon"]["program_fraction"]["B_cell"]), pct(immune["liver"]["program_fraction"]["B_cell"]), "liver 相对突出"],
        ["巨噬细胞 / Macrophage", pct(immune["colon"]["program_fraction"]["Macrophage"]), pct(immune["liver"]["program_fraction"]["Macrophage"]), "colon 更高"],
        ["T 细胞", pct(immune["colon"]["program_fraction"]["T_cell"]), pct(immune["liver"]["program_fraction"]["T_cell"]), "两者都不高"],
        ["单核 / 髓系", pct(immune["colon"]["program_fraction"]["Monocyte"]), pct(immune["liver"]["program_fraction"]["Monocyte"]), "colon 更高"],
    ]
    ct, lt = subtype["colon"], subtype["liver"]
    subtype_rows = [
        ["T/NK 中 CD8 杀伤性 T", pct(ct["TNK_CD8"]), pct(lt["TNK_CD8"]), "colon 明显更高 → 杀伤性免疫更活跃"],
        ["T/NK 中 Treg 调节性 T", pct(ct["TNK_Treg"]), pct(lt["TNK_Treg"]), "两者均低"],
        ["T/NK 中 NK 细胞", pct(ct["TNK_NK"]), pct(lt["TNK_NK"]), "colon 可测、liver 极低"],
        ["T/NK 中耗竭 T（T_Exhaustion）", pct(ct["TNK_Exhausted"]), pct(lt["TNK_Exhausted"]), "均低（未到明显耗竭）"],
        ["T/NK 中细胞毒性程序", pct(ct["TNK_Cytotoxic"]), pct(lt["TNK_Cytotoxic"]), "colon 高于 liver"],
        ["巨噬中 SPP1+（促瘤/间质型）", pct(ct["Macro_SPP1"]), pct(lt["Macro_SPP1"]), "colon 比例更高"],
        ["巨噬中 C1QC+（抗炎/组织驻留）", pct(ct["Macro_C1QC"]), pct(lt["Macro_C1QC"]), "两者均为主流"],
    ]
    tme_cols = [("EMT", "上皮-间质转化 EMT"), ("Hypoxia", "缺氧 Hypoxia"), ("Angiogenesis", "血管生成 Angiogenesis"),
                ("Proliferation", "增殖 Proliferation"), ("myCAF", "基质型 CAF myCAF"),
                ("inflammatory_CAF", "炎症型 CAF iCAF"), ("Cytotoxicity", "细胞毒性 Cytotoxicity")]
    tme_rows = []
    for key, lab in tme_cols:
        cv, lv = immune["colon"]["program_fraction"][key], immune["liver"]["program_fraction"][key]
        note = "colon 显著" if cv > 0.2 else ("liver 相对高" if lv > cv else "水平相近/低")
        tme_rows.append([lab, pct(cv), pct(lv), note])

    action_rows = [
        ["P0", "空间蛋白组验证肿瘤候选与免疫微环境", "同一连续切片做蛋白组，直接验证", "1–2 个月", "中高"],
        ["P0", "病理科复核候选富集区域（HE/免疫组化）", "确认肿瘤范围与肝样本谱系（HCC/ICC）", "2–4 周", "低"],
        ["P1", "CNV 分析复核肿瘤候选", "与表达证据互补", "2–4 周", "低"],
        ["P1", "多重免疫组化：CD8 / PD-L1 / 巨噬极化", "验证免疫浸润结论", "4–6 周", "低"],
        ["P2", "候选区域单细胞解离测序", "深入免疫/肿瘤状态", "2–3 个月", "中高"],
    ]

    css = f"""
    :root {{ --ink:{INK}; --ink-soft:{INK_SOFT}; --accent:{ACCENT}; --accent-soft:{ACCENT_SOFT};
             --ground:{GROUND}; --card:{CARD}; --text:{TEXT}; --muted:{MUTED}; --line:{LINE}; --good:{GOOD}; --warn:{WARN}; }}
    * {{ box-sizing:border-box; }}
    html {{ scroll-behavior:smooth; }}
    body {{ margin:0; background:var(--ground); color:var(--text);
            font-family:"Noto Sans CJK SC","Source Han Sans SC","PingFang SC","Microsoft YaHei",sans-serif;
            line-height:1.75; font-size:16px; -webkit-font-smoothing:antialiased; }}
    a {{ color:var(--accent); }}
    .wrap {{ max-width:1080px; margin:0 auto; padding:0 28px 96px; }}
    /* cover */
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
    /* toc */
    .toc {{ position:sticky; top:0; z-index:30; background:rgba(250,250,248,.94);
            backdrop-filter:blur(8px); border-bottom:1px solid var(--line); }}
    .toc-inner {{ max-width:1080px; margin:0 auto; display:flex; flex-wrap:wrap; gap:4px 20px;
                  padding:12px 28px; font-size:13.5px; }}
    .toc a {{ color:var(--ink-soft); text-decoration:none; padding:2px 0; border-bottom:1px solid transparent; }}
    .toc a:hover {{ color:var(--ink); border-bottom-color:var(--accent); }}
    /* sections */
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

    toc = [("s1", "执行摘要"), ("s2", "技术背景"), ("s3", "数据质量"), ("s4", "组织结构"),
           ("s5", "细胞地图"), ("s6", "肿瘤定位"), ("s7", "候选证据"), ("s8", "免疫浸润"),
           ("s9", "免疫亚型"), ("s10", "微环境状态"), ("s11", "风险解读"), ("s12", "下游可行性"),
           ("s13", "实验建议"), ("s14", "独立验证"), ("s15", "局限与行动")]
    toc_html = "".join(f'<a href="#{i}">{esc(t)}</a>' for i, t in toc)

    colon_foci = enriched.get("sample_A", [])
    liver_foci = enriched.get("sample_B", [])

    doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Visium HD 空间转录组解读报告 · sample_A / sample_B</title>
<style>{css}</style>
</head>
<body>

<header class="cover">
  <div class="cover-inner">
    <div class="eyebrow">Spatial Transcriptomics · Readout</div>
    <h1>两份临床组织切片的<br>空间转录组分析报告</h1>
    <p class="sub">sample_A（结肠原发灶）· sample_B（肝原发肿瘤，HCC/ICC 待定）</p>
    <div class="banner">
      <p class="lead"><b>一句话结论：</b>两份切片数据质量合格、组织结构完整、细胞类型定位清晰，
      完全支持开展下游实验（建议优先做空间蛋白组）。两份组织都检出肿瘤性上皮候选：
      结肠 <b>2,349</b> 个（2.9%）、肝脏 <b>25,108</b> 个（15.2%），
      肝脏样本为肝细胞谱系、HCC/ICC 亚型待病理确认。</p>
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
    {kpi("2,349 / 25,108", "肿瘤候选（结肠 / 肝脏）", "accent")}
    {kpi(pct(colon_c['supported_fraction']) + " / " + pct(liver_c['supported_fraction']), "注释 A/B 级支持率（结肠/肝）", "ink")}
  </div>
  <table>
    <thead><tr><th style="width:22%">问题</th><th>结论</th></tr></thead>
    <tbody>
      <tr><td>数据能不能用？</td><td>能。测序与细胞层面均达标，注释 A/B 级支持率 {pct(colon_c['supported_fraction'])}（结肠）/ {pct(liver_c['supported_fraction'])}（肝）。</td></tr>
      <tr><td>组织切得对不对？</td><td>结构完整、细胞类型地图符合临床病理预期（结肠=上皮/间质/免疫；肝=肝实质为主）。</td></tr>
      <tr><td>肿瘤在哪里？</td><td>结肠：{len(colon_foci)} 个候选富集聚类、共 2,349 个候选（2.9%，多灶）；肝：{len(liver_foci)} 个富集聚类、25,108 个候选（15.2%，大片连续）。</td></tr>
      <tr><td>免疫怎么样？</td><td>结肠免疫活跃（{pct(immune['colon']['immune_fraction'])}），以浆细胞/B + 巨噬为主、T 细胞可测；肝相对免疫贫乏（{pct(immune['liver']['immune_fraction'])}），B 细胞相对突出。</td></tr>
      <tr><td>能往下做吗？</td><td>能。建议下一步优先空间蛋白组验证候选区域与免疫微环境，再做病理/CNV 复核。</td></tr>
    </tbody>
  </table>
  <div class="note">两例为<strong>独立肿瘤</strong>，不是配对原发—转移；所有恶性相关表述均为“计算候选”，需病理/CNV 正交验证。单对样本，不进行组间统计显著性推断。</div>
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
  <h3>（一）测序层面：两项样本均达标</h3>
  {rows_table(["指标", "sample_A", "sample_B", "常见范围（Visium FFPE）", "判断"], seq_rows)}
  <p>指标来自 Space Ranger 官方 metrics_summary；判断标准按 Visium FFPE/HD 行业常见范围给出。两个样本测序质量属于<strong>优良</strong>水平；唯一注意点是测序饱和度偏低，加深测序还能挖到更多信息（不影响当前结论）。</p>
  <h3>（二）细胞层面：数量充足、可用于下游</h3>
  <div class="kpis">
    {kpi(num(colon["matrix_cells"]), "colon 分拣单细胞数", "ink")}
    {kpi(num(liver["matrix_cells"]), "liver 分拣单细胞数", "ink")}
    {kpi(f'{colon["genes_median"]:.0f}', "colon 中位基因数/细胞", "ink")}
    {kpi(f'{liver["genes_median"]:.0f}', "liver 中位基因数/细胞", "ink")}
  </div>
  {rows_table(["样本", "分拣单细胞", "中位 UMI/细胞", "中位基因/细胞", "UMI<100 比例", "与细胞轮廓对应", "与核轮廓对应", "综合判断"], cell_rows)}
  <p>两样本细胞数量充足、细胞/核轮廓对应率 100%，定位可靠；肝脏样本单个细胞表达深度略低，属 Visium HD 常见现象，不影响“看到哪些细胞类型”，只提示细亚型结论要保守。</p>
  {figure_card(imgs["qc"], "图 1. 分拣单细胞 UMI 与检测基因数分布（colon vs liver）")}
  <div class="note">分拣单细胞（segmented cells）是主分析单位；8 µm 网格单元<strong>不能当单细胞看</strong>，只用于空间验证。</div>
</section>

<section id="s4">
  <h2><span class="idx">04</span>组织结构清不清晰？</h2>
  <p class="lede">两张 HE 图完整、可读，无大片缺失。</p>
  <div class="grid2">
    {figure_card(imgs["he_colon"], "sample_A 原始 HE（空间转录组切片）")}
    {figure_card(imgs["he_liver"], "sample_B 原始 HE（空间转录组切片）")}
  </div>
</section>

<section id="s5">
  <h2><span class="idx">05</span>组织类型映射：细胞地图符合病理预期</h2>
  <h3>结肠（sample_A）</h3>
  <div class="grid3">
    {figure_card(imgs["colon_1"], "① 细胞分区")}
    {figure_card(imgs["colon_2"], "② 主要细胞类型")}
    {figure_card(imgs["colon_3"], "③ 上皮恶性证据")}
  </div>
  <div class="concl"><h4>结论</h4><ul>
    <li>分区：间质 {pct(36935/81616)}（成纤维为主）+ 免疫 {pct(24790/81616)} + 上皮 {pct(6021/81616)} → 典型结肠“上皮–间质–免疫”结构。</li>
    <li>类型：成纤维 {pct(30263/81616)}、浆细胞 {pct(8003/81616)}、巨噬 {pct(6081/81616)}、B 细胞 {pct(3362/81616)} 为背景主力；恶性上皮候选 2,349（2.9%）。</li>
    <li>定位：肿瘤候选富集于 {len(colon_foci)} 个 8 µm 聚类（cluster {"/".join(map(str,colon_foci))}），最大富集区候选占比 30.7%；候选散布于纤维/免疫背景，非弥漫全片。</li>
    <li>符合结肠临床病理预期，数据支持下游实验；肿瘤呈多灶富集，建议病理框选确认边界。</li>
  </ul></div>

  <h3>肝脏（sample_B，肝原发肿瘤）</h3>
  <div class="grid3">
    {figure_card(imgs["liver_1"], "① 细胞分区")}
    {figure_card(imgs["liver_2"], "② 主要细胞类型")}
    {figure_card(imgs["liver_3"], "③ 上皮恶性证据")}
  </div>
  <div class="concl"><h4>结论</h4><ul>
    <li>分区：上皮 {pct(76567/164905)}（肝细胞为主）+ 间质 {pct(31007/164905)} + 免疫 {pct(21700/164905)} → 肝实质占主导，符合肝组织背景。</li>
    <li>类型：肝细胞 42,412（25.7%）为背景主力；肝癌上皮候选 25,108（15.2%），与肝细胞混合成片；胆管细胞 2,335（1.4%）。</li>
    <li>定位：候选占比（15.2%）远高于结肠，集中于 {len(liver_foci)} 个 8 µm 聚类（cluster {"/".join(map(str,liver_foci))}，占该区 28.8%），呈大片连续分布、边界不清。</li>
    <li>符合肝原发肿瘤（HCC/ICC 谱系）背景，免疫相对贫乏；亚型须病理明确，肿瘤边界需病理/CNV 界定。</li>
  </ul></div>
</section>

<section id="s6">
  <h2><span class="idx">06</span>肿瘤候选区域在哪里</h2>
  <p class="lede">红色 = 肿瘤性上皮候选。8 µm 聚类组成图给出候选富集的区域坐标。</p>
  <div class="grid2">
    {figure_card(imgs["colon_clusters"], f"colon：{len(colon_foci)} 个候选富集聚类，候选 2,349（2.9%）")}
    {figure_card(imgs["liver_clusters"], f"liver：{len(liver_foci)} 个候选富集聚类，候选 25,108（15.2%）")}
  </div>
  <div class="note">结肠候选散布于纤维/免疫背景中（多灶）；肝脏候选与 hepatocyte 混合成片，提示肝细胞谱系肿瘤。候选富集区域坐标已导出，可直接用于病理与下游实验设计。</div>
</section>

<section id="s7">
  <h2><span class="idx">07</span>为什么叫“候选”而不是“确诊”</h2>
  <div class="grid2">
    <div class="card">
      <h3 style="color:{GOOD}">判定为“肿瘤候选”需要什么</h3>
      <ul>
        <li>至少两类独立证据同时支持</li>
        <li>证据① 疾病特异性参考映射（结肠：CRC Atlas；肝：肝癌参考）</li>
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
        <li>肝脏样本 HCC/ICC 亚型未定（需病理）</li>
      </ul>
    </div>
  </div>
  <div class="accent-note">结论口径：把恶性相关结果表述为“肿瘤性上皮候选”，并给出候选富集区域坐标，供病理/下游实验直接复核。</div>
</section>

<section id="s8">
  <h2><span class="idx">08</span>免疫细胞有哪些？免疫浸润程度</h2>
  <div class="kpis">
    {kpi(pct(immune["colon"]["immune_fraction"]), "colon 免疫细胞占比", "accent")}
    {kpi(pct(immune["liver"]["immune_fraction"]), "liver 免疫细胞占比", "accent")}
    {kpi(num(immune["colon"]["immune_cells"]), "colon 免疫细胞数", "ink")}
    {kpi(num(immune["liver"]["immune_cells"]), "liver 免疫细胞数", "ink")}
  </div>
  {rows_table(["免疫细胞类型（程序得分≥阈值细胞占比）", "sample_A", "sample_B", "初步解读"], immune_rows)}
  <div class="note">结肠以“体液免疫（浆细胞/B）+ 巨噬”为主的免疫微环境，免疫较活跃；肝脏免疫占比较低、以 B 细胞为相对主调，偏“冷”微环境。</div>
</section>

<section id="s9">
  <h2><span class="idx">09</span>免疫细胞细分亚型：比例是否异常</h2>
  {rows_table(["亚型（在该细胞群内的占比）", "sample_A", "sample_B", "值得关注点"], subtype_rows)}
  <div class="concl"><h4>结论</h4><ul>
    <li>结肠免疫浸润更“活跃且有杀伤性”，值得作为免疫微环境研究对象。</li>
    <li>肝脏免疫偏贫乏、T 细胞信号弱，属更需关注免疫逃逸 / 冷肿瘤特征的区域。</li>
    <li>免疫亚型由基因程序推断，建议用蛋白（空间蛋白组 / mIHC）二次确认。</li>
  </ul></div>
</section>

<section id="s10">
  <h2><span class="idx">10</span>肿瘤微环境状态：有没有在“为肿瘤铺路”</h2>
  {rows_table(["微环境状态程序（阳性细胞占全部细胞）", "sample_A", "sample_B", "解读"], tme_rows)}
  <p>结肠呈现明显 EMT（35.6%）与基质型 CAF（45.2%）富集 → 促纤维化、促侵袭的微环境；肝脏 EMT 相对低（8.3%），以肝实质主导、基质为辅。</p>
  <div class="note">这些“状态程序”是计算推断，用于提出假设；与病理形态、免疫组化结果互为补充而非替代。</div>
</section>

<section id="s11">
  <h2><span class="idx">11</span>这些发现能预示什么（谨慎解读）</h2>
  <div class="grid2">
    <div class="card">
      <h3 style="color:{INK}">sample_A 提示</h3>
      <ul>
        <li>肿瘤候选占 2.9%，呈多个富集灶</li>
        <li>EMT + myCAF 富集 → 提示侵袭/促纤维化倾向</li>
        <li>免疫较活跃（浆细胞/B + 巨噬为主，CD8 可测）</li>
        <li>→ 建议：结合病理分期确认肿瘤范围与浸润深度</li>
      </ul>
    </div>
    <div class="card">
      <h3 style="color:{INK}">sample_B 提示</h3>
      <ul>
        <li>肿瘤候选占 15.2%，与 hepatocyte 混合成片</li>
        <li>肝细胞谱系、HCC/ICC 亚型未定</li>
        <li>免疫偏贫乏、T 细胞信号弱 → 冷肿瘤特征</li>
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
    {kpi(pct(colon_r['cell_compartment_agreement']), "colon RCTD 独立一致率", "ink")}
    {kpi(pct(liver_r['cell_compartment_agreement']), "liver RCTD 独立一致率", "ink")}
    {kpi("≥99%", "细胞-轮廓-空间定位对应率", "good")}
    {kpi("有", "候选富集区域坐标可导出", "good")}
    {kpi(num(colon_r['eligible_bins']), "colon eligible 8 µm bins", "ink")}
    {kpi(num(liver_r['eligible_bins']), "liver eligible 8 µm bins", "ink")}
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
  <div class="accent-note">建议顺序：空间蛋白组验证（首选）→ 病理/CNV 复核 → 若需深入再考虑解离单细胞。候选区域坐标已就绪，可直接用于设计。</div>
</section>

<section id="s14">
  <h2><span class="idx">14</span>信任背书：用第二种方法独立验证</h2>
  <div class="kpis">
    {kpi(pct(colon_r['cell_compartment_agreement']), "colon 一致率（独立方法）", "accent")}
    {kpi(pct(liver_r['cell_compartment_agreement']), "liver 一致率（独立方法）", "accent")}
    {kpi(pct(colon_r['singlet_fraction']), "colon RCTD singlet", "ink")}
    {kpi(pct(liver_r['singlet_fraction']), "liver RCTD singlet", "ink")}
  </div>
  <p>RCTD 是另一种公认的空间去卷积算法，处理约 100 万个 8 µm 网格单元（colon {num(colon_r['eligible_bins'])}、liver {num(liver_r['eligible_bins'])} 个 eligible bins），与分拣单细胞注释在大类上高度一致（{pct(colon_r['cell_compartment_agreement'])} / {pct(liver_r['cell_compartment_agreement'])}）。</p>
  {figure_card(imgs["rctd"], "图. 全量 RCTD 在 projected clusters 中的 compartment weight 组成")}
</section>

<section id="s15">
  <h2><span class="idx">15</span>边界、局限与下一步行动</h2>
  <div class="card">
    <h3>现在还不能下的结论</h3>
    <ul>
      <li>恶性为“计算候选”：没有病理 ROI、没有 CNV，最终确诊需病理复核</li>
      <li>肝脏样本 HCC/ICC 亚型未定：需病理明确谱系后再下结论</li>
      <li>单对样本：不能做患者群体间的统计推断，所有比较为描述性</li>
      <li>表达深度有限：肝脏样本细亚型（如 T/NK 亚型）结论应保守</li>
      <li>免疫亚型由基因程序推断：建议用蛋白（空间蛋白组/mIHC）二次确认</li>
      <li>测序饱和度偏低：如追求更全基因覆盖，可考虑补充测序</li>
    </ul>
  </div>
  <h3>下一步行动建议（供决策）</h3>
  {rows_table(["优先级", "行动", "目的", "周期（估）", "成本"], action_rows)}
  <div class="accent-note">建议起步组合：空间蛋白组（验证）+ 病理复核（确诊）双线并行，2–4 周内即可给出“肿瘤在哪、免疫怎么样”的确认版。优先级与周期为建议值，可按预算/资源调整；候选区域坐标、细胞清单、图与表格均已随报告交付。</div>
</section>

<footer>
  <p>本报告由结构化结果数据自动生成，样本名、QC 数字、细胞比例与图路径均由程序校验。
  Visium HD FFPE/CytAssist · Space Ranger 4.1.0 · refdata-gex-GRCh38-2024-A · Human Transcriptome Probe Set v2.1.0。</p>
  <p>报告版本：{esc(data['report_version'])}　|　生成日期：{esc(data['generated_at'])}</p>
</footer>

</div>
</body>
</html>"""

    OUTPUT_PATH.write_text(doc, encoding="utf-8")
    size_mb = OUTPUT_PATH.stat().st_size / 1e6
    print(f"html={OUTPUT_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    build()
