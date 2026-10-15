#!/usr/bin/env python3
import json
from datetime import date
from pathlib import Path

import pandas as pd


ROOT = Path("<PROJECT_ROOT>")


def records(frame):
    return json.loads(frame.to_json(orient="records", force_ascii=False))


def main():
    audit = pd.read_csv(ROOT / "results/tables/baseline_audit_summary.tsv", sep="\t")
    marker = pd.read_csv(ROOT / "results/tables/cell_annotation/marker_evidence_qc.tsv", sep="\t")
    consensus_qc = pd.read_csv(ROOT / "results/tables/cell_annotation/current_disease_consensus_qc.tsv", sep="\t")
    rctd_cluster_path = ROOT / "results/tables/bin8um_validation/combined_cluster_labels_rctd_current.tsv"
    cluster_labels = pd.read_csv(
        rctd_cluster_path if rctd_cluster_path.exists() else ROOT / "results/tables/bin8um_validation/combined_cluster_labels_current.tsv",
        sep="\t",
    )
    mapping_qc = pd.concat(
        [
            pd.read_csv(ROOT / "results/tables/bin8um_validation/colon_cell_to_cluster_qc.tsv", sep="\t"),
            pd.read_csv(ROOT / "results/tables/bin8um_validation/liver_cell_to_cluster_qc.tsv", sep="\t"),
        ],
        ignore_index=True,
    )
    reference_summary = pd.concat(
        [
            pd.read_csv(ROOT / "results/tables/cell_annotation/colon_reference_evidence_summary.tsv", sep="\t").assign(sample="sample_A"),
            pd.read_csv(ROOT / "results/tables/cell_annotation/liver_reference_evidence_v2_summary.tsv", sep="\t").assign(sample="sample_B"),
        ],
        ignore_index=True,
    )
    manifest = pd.read_csv(ROOT / "annotation/references/manifest.tsv", sep="\t")
    dryrun = json.loads((ROOT / "provenance/dryrun/dryrun_summary.json").read_text(encoding="utf-8"))
    rctd_summary_path = ROOT / "results/tables/bin8um_validation/rctd_full/rctd_full_summary.json"
    if not rctd_summary_path.exists():
        raise FileNotFoundError(f"full RCTD summary is required for the final report: {rctd_summary_path}")
    rctd_summary = json.loads(rctd_summary_path.read_text(encoding="utf-8"))

    major_tables = {}
    status_tables = {}
    tier_tables = {}
    for tissue, sample in (("colon", "sample_A"), ("liver", "sample_B")):
        frame = pd.read_csv(
            ROOT / f"results/tables/cell_annotation/{tissue}_disease_consensus_current.tsv.gz",
            sep="\t",
            usecols=[
                "consensus_confidence_tier",
                "consensus_compartment",
                "consensus_major_cell_type",
                "malignant_status",
            ],
        )
        supported = frame[frame["consensus_confidence_tier"].isin(["A", "B"])]
        major = supported["consensus_major_cell_type"].value_counts().rename_axis("major_cell_type").reset_index(name="n_cells")
        major["fraction_of_all_cells"] = major["n_cells"] / len(frame)
        major["fraction_of_supported_cells"] = major["n_cells"] / len(supported)
        major_tables[sample] = records(major.head(15))
        status = frame["malignant_status"].value_counts().rename_axis("malignant_status").reset_index(name="n_cells")
        status["fraction"] = status["n_cells"] / len(frame)
        status_tables[sample] = records(status)
        tier = frame["consensus_confidence_tier"].value_counts().rename_axis("tier").reset_index(name="n_cells")
        tier["fraction"] = tier["n_cells"] / len(frame)
        tier_tables[sample] = records(tier)

    highlighted_clusters = cluster_labels[
        cluster_labels["malignant_niche_class"].ne("not_enriched")
        | cluster_labels["annotation_confidence"].eq("High")
    ].copy()
    highlighted_clusters = highlighted_clusters.sort_values(
        ["sample", "malignant_candidate_fraction", "dominant_fraction"], ascending=[True, False, False]
    )

    data = {
        "report_version": "最终版（colon: CRC Atlas/CRLM；liver: 肝癌参考重注释 + 全量 RCTD）",
        "generated_at": date.today().isoformat(),
        "project_root": str(ROOT),
        "audit": records(audit),
        "marker_qc": records(marker),
        "consensus_qc": records(consensus_qc),
        "mapping_qc": records(mapping_qc),
        "reference_summary": records(reference_summary),
        "reference_manifest": records(manifest),
        "dryrun": dryrun,
        "rctd_summary": rctd_summary,
        "major_tables": major_tables,
        "status_tables": status_tables,
        "tier_tables": tier_tables,
        "highlighted_clusters": records(highlighted_clusters),
        "all_cluster_labels": records(cluster_labels),
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
    }
    output = ROOT / "report/report_data_current.json"
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"output={output}")


if __name__ == "__main__":
    main()
