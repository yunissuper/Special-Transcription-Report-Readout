#!/usr/bin/env python3
"""Stage 4 of the pipeline: aggregate every downstream table into ONE JSON.

This is the single source of truth that every report/PPT reads from. If a
number is not in here, it must not appear in a deliverable. Keeping the
aggregation in one place is what stops "the report says X but the figure says Y".

Usage:
    python collect_results.py --root /path/to/project
    python collect_results.py --root . --out report/report_data_current.json

The set of tables/figures is described in <root>/report/report_config.json
(see templates/report_config.example.json). Anything missing from the config
falls back to the conventional paths below, so a project that follows the
recommended layout works with no config at all.
"""
import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd


def records(frame):
    """DataFrame -> list[dict] preserving UTF-8 (not \\uXXXX escaped)."""
    return json.loads(frame.to_json(orient="records", force_ascii=False))


DEFAULTS = {
    "samples": ["sample_A", "sample_B"],
    "sample_dirs": {"sample_A": "colon", "sample_B": "liver"},
    "display_names": {},
    "report_version": "auto",
    "tables": {
        "audit": "results/tables/baseline_audit_summary.tsv",
        "marker_qc": "results/tables/cell_annotation/marker_evidence_qc.tsv",
        "consensus_qc": "results/tables/cell_annotation/current_disease_consensus_qc.tsv",
        "cluster_labels": "results/tables/bin8um_validation/combined_cluster_labels_current.tsv",
        "cluster_labels_rctd": "results/tables/bin8um_validation/combined_cluster_labels_rctd_current.tsv",
        "cell_to_cluster_qc": [
            "results/tables/bin8um_validation/colon_cell_to_cluster_qc.tsv",
            "results/tables/bin8um_validation/liver_cell_to_cluster_qc.tsv",
        ],
        "reference_manifest": "annotation/references/manifest.tsv",
        "dryrun_summary": "provenance/dryrun/dryrun_summary.json",
        "rctd_summary": "results/tables/bin8um_validation/rctd_full/rctd_full_summary.json",
    },
    # per-tissue consensus tables: {tissue: path}
    "consensus_tables": {
        "colon": "results/tables/cell_annotation/colon_disease_consensus_current.tsv.gz",
        "liver": "results/tables/cell_annotation/liver_disease_consensus_current.tsv.gz",
    },
    # per-tissue reference evidence summaries
    "reference_evidence": {
        "colon": "results/tables/cell_annotation/colon_reference_evidence_summary.tsv",
        "liver": "results/tables/cell_annotation/liver_reference_evidence_summary.tsv",
    },
    "figures": {
        "cell_qc": "results/figures/audit/cell_qc_distributions.png",
        "azimuth_qc": "results/figures/audit/azimuth_confidence_distributions.png",
        "colon_marker": "results/figures/cell_annotation/colon_marker_evidence_spatial.png",
        "liver_marker": "results/figures/cell_annotation/liver_marker_evidence_spatial.png",
        "colon_ucell": "results/figures/cell_annotation/colon_ucell_programs.png",
        "liver_ucell": "results/figures/cell_annotation/liver_ucell_programs.png",
        "colon_consensus": "results/figures/cell_annotation/colon_disease_consensus_current_spatial.png",
        "liver_consensus": "results/figures/cell_annotation/liver_disease_consensus_current_spatial.png",
        "colon_clusters": "results/figures/bin8um_validation/colon_cluster_composition_current.png",
        "liver_clusters": "results/figures/bin8um_validation/liver_cluster_composition_current.png",
        "rctd_clusters": "results/figures/bin8um_validation/rctd_full_cluster_validation.png",
    },
    # required consensus columns
    "consensus_columns": [
        "consensus_confidence_tier",
        "consensus_compartment",
        "consensus_major_cell_type",
        "malignant_status",
    ],
}


def merge_config(cfg):
    """Overlay the user config on the defaults (one level of dict merge)."""
    merged = json.loads(json.dumps(DEFAULTS))  # deep copy
    for key, value in (cfg or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    return merged


def resolve(root, rel):
    return Path(root) / rel


def read_optional(path):
    return pd.read_csv(path, sep="\t") if Path(path).exists() else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="project root directory")
    parser.add_argument("--out", default="report/report_data_current.json")
    parser.add_argument("--config", default="report/report_config.json")
    parser.add_argument("--version", default=None, help="override report_version string")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    cfg = {}
    cfg_path = root / args.config
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg = merge_config(cfg)
    tables = cfg["tables"]

    # ---- mandatory inputs ---------------------------------------------------
    audit = pd.read_csv(resolve(root, tables["audit"]), sep="\t")
    marker = pd.read_csv(resolve(root, tables["marker_qc"]), sep="\t")
    consensus_qc = pd.read_csv(resolve(root, tables["consensus_qc"]), sep="\t")

    rctd_rel = tables["cluster_labels_rctd"]
    cluster_labels = pd.read_csv(
        resolve(root, rctd_rel if resolve(root, rctd_rel).exists() else tables["cluster_labels"]),
        sep="\t",
    )

    mapping_parts = [
        pd.read_csv(resolve(root, p), sep="\t")
        for p in tables["cell_to_cluster_qc"]
        if resolve(root, p).exists()
    ]
    mapping_qc = pd.concat(mapping_parts, ignore_index=True) if mapping_parts else pd.DataFrame()

    # reference evidence: one summary per tissue, tagged with a sample column
    ref_parts = []
    for tissue, rel in cfg["reference_evidence"].items():
        path = resolve(root, rel)
        if path.exists():
            ref_parts.append(pd.read_csv(path, sep="\t").assign(sample=tissue))
    reference_summary = pd.concat(ref_parts, ignore_index=True) if ref_parts else pd.DataFrame()

    manifest = pd.read_csv(resolve(root, tables["reference_manifest"]), sep="\t")

    dryrun_rel = resolve(root, tables["dryrun_summary"])
    dryrun = json.loads(dryrun_rel.read_text(encoding="utf-8")) if dryrun_rel.exists() else {}

    rctd_summary_path = resolve(root, tables["rctd_summary"])
    if not rctd_summary_path.exists():
        raise FileNotFoundError(
            f"RCTD summary is required for the final report: {rctd_summary_path}\n"
            "Run the bin-level RCTD validation first, or relax this gate intentionally."
        )
    rctd_summary = json.loads(rctd_summary_path.read_text(encoding="utf-8"))

    # ---- per-sample derived tables -----------------------------------------
    # map consensus-table tissue key -> audit sample_id (via sample_dirs inverse)
    dir_to_sample = {v: k for k, v in cfg.get("sample_dirs", {}).items()}
    audit_ids = set(audit["sample_id"])

    major_tables, status_tables, tier_tables = {}, {}, {}
    for tissue, rel in cfg["consensus_tables"].items():
        path = resolve(root, rel)
        if not path.exists():
            continue
        frame = pd.read_csv(path, sep="\t", usecols=cfg["consensus_columns"])
        if tissue in dir_to_sample:
            sample = dir_to_sample[tissue]
        else:
            sample = next((sid for sid in audit_ids if sid.startswith(tissue)), tissue)
        supported = frame[frame["consensus_confidence_tier"].isin(["A", "B"])]

        major = supported["consensus_major_cell_type"].value_counts().rename_axis("major_cell_type").reset_index(name="n_cells")
        major["fraction_of_all_cells"] = major["n_cells"] / len(frame)
        major["fraction_of_supported_cells"] = major["n_cells"] / max(len(supported), 1)
        major_tables[sample] = records(major.head(15))

        status = frame["malignant_status"].value_counts().rename_axis("malignant_status").reset_index(name="n_cells")
        status["fraction"] = status["n_cells"] / len(frame)
        status_tables[sample] = records(status)

        tier = frame["consensus_confidence_tier"].value_counts().rename_axis("tier").reset_index(name="n_cells")
        tier["fraction"] = tier["n_cells"] / len(frame)
        tier_tables[sample] = records(tier)

    highlighted = cluster_labels[
        cluster_labels["malignant_niche_class"].ne("not_enriched")
        | cluster_labels["annotation_confidence"].eq("High")
    ].copy()
    highlighted = highlighted.sort_values(
        ["sample", "malignant_candidate_fraction", "dominant_fraction"], ascending=[True, False, False]
    )

    version = args.version or cfg.get("report_version", "auto")

    data = {
        "report_version": version,
        "generated_at": date.today().isoformat(),
        "project_root": str(root),
        "audit": records(audit),
        "marker_qc": records(marker),
        "consensus_qc": records(consensus_qc),
        "mapping_qc": records(mapping_qc) if not mapping_qc.empty else [],
        "reference_summary": records(reference_summary) if not reference_summary.empty else [],
        "reference_manifest": records(manifest),
        "dryrun": dryrun,
        "rctd_summary": rctd_summary,
        "major_tables": major_tables,
        "status_tables": status_tables,
        "tier_tables": tier_tables,
        "highlighted_clusters": records(highlighted),
        "all_cluster_labels": records(cluster_labels),
        "figures": cfg["figures"],
    }

    output = root / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"output={output} samples={sorted(major_tables)}")


if __name__ == "__main__":
    main()
