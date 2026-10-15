#!/usr/bin/env python3
"""Build a tiny synthetic project so the whole report chain runs end-to-end.

This is NOT analysis -- it fabricates just enough tables/figures/JSON in the
exact shapes the real scripts expect, so a new user can watch collect -> build
HTML -> build PPT -> validate succeed in ~10 seconds, then swap in real data.

Usage:
    python demo/make_demo_data.py --root demo/project
    python scripts/collect_results.py --root demo/project
    python scripts/build_html_report.py --root demo/project --out report/report_leader.html
    python scripts/build_ppt_leader.py --root demo/project --out ppt/output/report.pptx
    python scripts/validate_report.py --root demo/project
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SAMPLES = [("colon_D1", "colon"), ("liver_A1", "liver")]


def make_tables(root):
    (root / "results/tables/cell_annotation").mkdir(parents=True, exist_ok=True)
    (root / "results/tables/bin8um_validation/rctd_full").mkdir(parents=True, exist_ok=True)
    (root / "annotation/references").mkdir(parents=True, exist_ok=True)
    (root / "provenance/dryrun").mkdir(parents=True, exist_ok=True)
    (root / "baseline_readonly/colon_spaceranger_outs").mkdir(parents=True, exist_ok=True)
    (root / "baseline_readonly/liver_spaceranger_outs").mkdir(parents=True, exist_ok=True)

    audit_rows, cons_rows, ref_rows, mapping_rows = [], [], [], []
    for sample, tissue in SAMPLES:
        cells = 80000 if tissue == "colon" else 160000
        audit_rows.append({
            "sample_id": sample, "matrix_cells": cells, "genes": 18000,
            "umi_median": 375 if tissue == "colon" else 244,
            "genes_median": 291 if tissue == "colon" else 186,
            "umi_lt_100_rate": 0.15 if tissue == "colon" else 0.26,
            "azimuth_confident_rate": 0.82,
        })
        cons_rows.append({
            "sample": sample, "supported_fraction": 0.845 if tissue == "colon" else 0.769,
            "malignant_candidates": 2349 if tissue == "colon" else 25108,
        })
        ref_rows.append({"tissue": tissue, "n_reference_cells": 12000, "agreement": 0.78})
        mapping_rows.append({"sample": sample, "cell_to_cluster_rate": 0.995})
    pd.DataFrame(audit_rows).to_csv(root / "results/tables/baseline_audit_summary.tsv", sep="\t", index=False)
    pd.DataFrame(cons_rows).to_csv(root / "results/tables/cell_annotation/current_disease_consensus_qc.tsv", sep="\t", index=False)
    pd.DataFrame(ref_rows).to_csv(root / "results/tables/cell_annotation/colon_reference_evidence_summary.tsv", sep="\t", index=False)
    pd.DataFrame(ref_rows).to_csv(root / "results/tables/cell_annotation/liver_reference_evidence_summary.tsv", sep="\t", index=False)

    # marker QC, cluster labels, per-sample consensus
    pd.DataFrame([
        {"sample": "colon_D1", "tier_A_or_B_fraction": 0.804},
        {"sample": "liver_A1", "tier_A_or_B_fraction": 0.795},
    ]).to_csv(root / "results/tables/cell_annotation/marker_evidence_qc.tsv", sep="\t", index=False)

    labels = []
    for sample, tissue in SAMPLES:
        for cid in range(20):
            enriched = (tissue == "colon" and cid in (2, 4, 14)) or (tissue == "liver" and cid == 12)
            labels.append({
                "sample": sample, "cluster_id": cid,
                "malignant_niche_class": "candidate_enriched" if enriched else "not_enriched",
                "malignant_candidate_fraction": 0.30 if enriched else 0.02,
                "dominant_fraction": 0.5, "annotation_confidence": "High" if cid < 3 else "Medium",
            })
    pd.DataFrame(labels).to_csv(root / "results/tables/bin8um_validation/combined_cluster_labels_current.tsv", sep="\t", index=False)

    rctd = {}
    for sample, tissue in SAMPLES:
        frame = pd.DataFrame({
            "consensus_confidence_tier": ["A"] * 60 + ["B"] * 25 + ["C"] * 15,
            "consensus_compartment": ["Epithelial"] * 30 + ["Immune"] * 30 + ["Stromal"] * 40,
            "consensus_major_cell_type": (["Hepatocyte"] * 30 + ["T cell"] * 30 + ["Fibroblast"] * 40) if tissue == "liver"
            else (["CRC malignant candidate"] * 30 + ["Plasma cell"] * 30 + ["Fibroblast"] * 40),
            "malignant_status": ["CRC malignant candidate - disease reference and CRC marker supported; pathology/CNV pending"] * 30 + ["Not applicable - non-epithelial"] * 70
            if tissue == "colon" else
            ["Liver cancer epithelium candidate - hepatocyte-lineage epithelial identity with liver-cancer reference support; HCC-vs-ICC subtype and pathology/CNV not resolved, spatial tumour boundary not established"] * 30 + ["Not applicable - non-epithelial"] * 70,
        })
        frame.to_csv(root / f"results/tables/cell_annotation/{tissue}_disease_consensus_current.tsv.gz", sep="\t", index=False)
        rctd[sample] = {
            "cell_compartment_agreement": 0.93 if tissue == "colon" else 0.92,
            "singlet_fraction": 0.81, "eligible_bins": 987654 if tissue == "colon" else 1102003,
            "reject_fraction": 0.12,
        }
    (root / "results/tables/bin8um_validation/rctd_full/rctd_full_summary.json").write_text(
        json.dumps(rctd, ensure_ascii=False, indent=2), encoding="utf-8")

    # reference manifest + dryrun
    pd.DataFrame([
        {"reference": "demo CRC atlas", "version": "v1", "accession": "DEMO", "license": "demo", "checksum": "n/a"},
    ]).to_csv(root / "annotation/references/manifest.tsv", sep="\t", index=False)
    (root / "provenance/dryrun/dryrun_summary.json").write_text(
        json.dumps({"colon": {"returncode": 0}, "liver": {"returncode": 0}}, ensure_ascii=False), encoding="utf-8")

    # metrics_summary.csv for both samples
    for sample, tissue in SAMPLES:
        pd.DataFrame([{
            "Valid Barcodes": 0.893, "Valid UMI Sequences": 0.999,
            "Q30 Bases in Probe Read": 0.975, "Reads Mapped to Probe Set": 0.987,
            "Sequencing Saturation": 0.374 if tissue == "colon" else 0.489, "Genes Detected": 18111,
        }]).to_csv(root / f"baseline_readonly/{tissue}_spaceranger_outs/metrics_summary.csv", index=False)

    # immune summaries
    for name, payload in (
        ("immune_tme_summary.json", {
            "colon": {"immune_fraction": 0.304, "immune_cells": 24790,
                      "program_fraction": {"Plasma_cell": 0.34, "B_cell": 0.09, "Macrophage": 0.11,
                                           "T_cell": 0.06, "Monocyte": 0.04, "EMT": 0.356, "Hypoxia": 0.12,
                                           "Angiogenesis": 0.08, "Proliferation": 0.15, "myCAF": 0.452,
                                           "inflammatory_CAF": 0.10, "Cytotoxicity": 0.05}},
            "liver": {"immune_fraction": 0.132, "immune_cells": 21700,
                      "program_fraction": {"Plasma_cell": 0.05, "B_cell": 0.22, "Macrophage": 0.07,
                                           "T_cell": 0.03, "Monocyte": 0.02, "EMT": 0.083, "Hypoxia": 0.06,
                                           "Angiogenesis": 0.11, "Proliferation": 0.10, "myCAF": 0.13,
                                           "inflammatory_CAF": 0.05, "Cytotoxicity": 0.02}},
        }),
        ("immune_subtype_summary.json", {
            "colon": {"TNK_CD8": 0.31, "TNK_Treg": 0.04, "TNK_NK": 0.18, "TNK_Exhausted": 0.05,
                      "TNK_Cytotoxic": 0.22, "Macro_SPP1": 0.41, "Macro_C1QC": 0.38},
            "liver": {"TNK_CD8": 0.12, "TNK_Treg": 0.05, "TNK_NK": 0.02, "TNK_Exhausted": 0.04,
                      "TNK_Cytotoxic": 0.08, "Macro_SPP1": 0.22, "Macro_C1QC": 0.45},
        }),
    ):
        (root / f"results/tables/cell_annotation/{name}").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def make_figures(root):
    rng = np.random.default_rng(0)
    fig_dir = root / "results/figures"
    (fig_dir / "audit").mkdir(parents=True, exist_ok=True)
    (fig_dir / "cell_annotation").mkdir(parents=True, exist_ok=True)
    (fig_dir / "bin8um_validation").mkdir(parents=True, exist_ok=True)

    # QC distributions
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.hist(rng.normal(1500, 500, 2000).clip(0), bins=60, color="#1F3A4D", alpha=0.75, label="colon_D1")
    ax.hist(rng.normal(1000, 400, 2000).clip(0), bins=60, color="#B5651D", alpha=0.6, label="liver_A1")
    ax.set_title("Demo UMI per segmented cell"); ax.legend()
    fig.tight_layout(); fig.savefig(fig_dir / "audit/cell_qc_distributions.png", dpi=110); plt.close(fig)

    # consensus panels for each sample
    for sample, tissue in SAMPLES:
        n = 6000
        coords = rng.uniform(0, 3000, size=(n, 2))
        comp = rng.choice(["Epithelial", "Immune", "Stromal"], size=n, p=[0.4, 0.3, 0.3])
        major = rng.choice(["Hepatocyte", "T cell", "Fibroblast"] if tissue == "liver"
                           else ["CRC malignant candidate", "Plasma cell", "Fibroblast"], size=n)
        malign = rng.choice(
            ["CRC malignant candidate - disease reference and CRC marker supported; pathology/CNV pending",
             "Not applicable - non-epithelial"], size=n, p=[0.15, 0.85]) if tissue == "colon" else rng.choice(
            ["Liver cancer epithelium candidate - hepatocyte-lineage epithelial identity with liver-cancer reference support; HCC-vs-ICC subtype and pathology/CNV not resolved, spatial tumour boundary not established",
             "Not applicable - non-epithelial"], size=n, p=[0.2, 0.8])
        frame = pd.DataFrame({
            "barcode": [f"bc{i}" for i in range(n)],
            "consensus_compartment": comp, "consensus_major_cell_type": major, "malignant_status": malign,
        })
        frame.to_csv(root / f"results/tables/cell_annotation/{tissue}_consensus.tsv.gz", sep="\t", index=False)
        pd.DataFrame({"barcode": frame["barcode"], "cell_x_pixel": coords[:, 0], "cell_y_pixel": coords[:, 1]}).to_csv(
            root / f"results/tables/cell_annotation/{tissue}_coords.tsv", sep="\t", index=False)

        # simple 3 thumbnail panels (demo only; real runs use plot_consensus_panels.py)
        for k, (col, palette) in enumerate([
            ("consensus_compartment", {"Epithelial": "#d73027", "Immune": "#4575b4", "Stromal": "#66a61e"}),
            ("consensus_major_cell_type", None),
            ("malignant_status", None),
        ], start=1):
            fig, ax = plt.subplots(figsize=(3.2, 3.6))
            colors = [palette.get(v, "#969696") if palette else ("#b2182b" if "candidate" in v else "#bdbdbd")
                      for v in frame[col]]
            ax.scatter(coords[:, 0], coords[:, 1], s=0.4, c=colors)
            ax.set_title(f"{sample} panel {k}", fontsize=9); ax.axis("off")
            fig.tight_layout()
            fig.savefig(fig_dir / f"cell_annotation/{tissue}_consensus_panels_{k}_"
                        f"{['compartment', 'major', 'malignancy'][k-1]}.png", dpi=110)
            plt.close(fig)
        # composite
        fig, ax = plt.subplots(figsize=(6, 3)); ax.scatter(coords[:, 0], coords[:, 1], s=0.3, c="#1F3A4D")
        ax.set_title(f"{sample} composite"); ax.axis("off"); fig.tight_layout()
        fig.savefig(fig_dir / f"cell_annotation/{tissue}_consensus_panels.png", dpi=110); plt.close(fig)

    # HE-ish, cluster composition, rctd
    for rel, title in [
        ("colon_cluster_composition_current.png", "colon clusters"),
        ("liver_cluster_composition_current.png", "liver clusters"),
        ("rctd_full_cluster_validation.png", "RCTD validation"),
    ]:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(range(20), rng.uniform(0, 1, 20), color="#41606F"); ax.set_title(title)
        fig.tight_layout(); fig.savefig(fig_dir / f"bin8um_validation/{rel}", dpi=110); plt.close(fig)
    for tissue in ("colon", "liver"):
        fig, ax = plt.subplots(figsize=(6, 5)); ax.imshow(rng.uniform(0.6, 1.0, (400, 500, 3)))
        ax.set_title(f"{tissue} HE (demo)"); ax.axis("off"); fig.tight_layout()
        fig.savefig(root / f"baseline_readonly/{tissue}_spaceranger_outs/tissue_hires_image.png", dpi=110)
        plt.savefig(root / f"baseline_readonly/{tissue}_spaceranger_outs/spatial_tissue_hires_image.png", dpi=110)
        plt.close(fig)
    # the HTML/PPT read tissue_hires_image.png from spatial/ subdir
    for tissue in ("colon", "liver"):
        (root / f"baseline_readonly/{tissue}_spaceranger_outs/spatial").mkdir(parents=True, exist_ok=True)
        src = root / f"baseline_readonly/{tissue}_spaceranger_outs/tissue_hires_image.png"
        (root / f"baseline_readonly/{tissue}_spaceranger_outs/spatial/tissue_hires_image.png").write_bytes(src.read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="demo/project")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "report").mkdir(parents=True, exist_ok=True)
    make_tables(root)
    make_figures(root)
    (root / "report/report_config.json").write_text(
        json.dumps({
            "samples": ["colon_D1", "liver_A1"],
            "display_names": {"colon_D1": "结肠原发灶（colon_D1）", "liver_A1": "肝原发肿瘤（liver_A1）"},
            "sample_dirs": {"colon_D1": "colon", "liver_A1": "liver"},
            "report_version": "demo",
            "tissue_vocab": {"CRC": {"forbidden_markers": ["colon", "结肠", "结直肠", "CRC"]}},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"demo project ready at {root}")


if __name__ == "__main__":
    main()
