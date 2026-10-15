#!/usr/bin/env python3
"""Shared helpers for the spatial-transcriptomics report generators.

Everything here is UI/data plumbing only -- no analysis, no project-specific
numbers. Imported by build_html_report.py / build_ppt_leader.py / collect_results.py
so the palette and the small formatting helpers stay in one place.
"""
import base64
import csv
import html
import io
import json
from pathlib import Path

# ---- palette (low-saturation, academic) ------------------------------------
INK = "#1F3A4D"        # primary deep teal-gray
INK_SOFT = "#41606F"   # secondary
ACCENT = "#B5651D"     # terracotta, used sparingly
ACCENT_SOFT = "#EAD9C7"
GROUND = "#FAFAF8"     # off-white page ground
CARD = "#FFFFFF"
TEXT = "#2C2C2C"
MUTED = "#6B7278"
LINE = "#E2E4E1"
GOOD = "#2E6B4F"
WARN = "#9C6B1E"

PALETTE = {
    "ink": INK, "ink_soft": INK_SOFT, "accent": ACCENT, "accent_soft": ACCENT_SOFT,
    "ground": GROUND, "card": CARD, "text": TEXT, "muted": MUTED,
    "line": LINE, "good": GOOD, "warn": WARN,
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_config(root, name="report_config.json"):
    """Load <root>/report/<name>; return {} when absent so callers can default."""
    path = Path(root) / "report" / name
    if not path.exists():
        return {}
    return load_json(path)


def records(frame):
    """DataFrame -> list[dict] with UTF-8 preserved (not \\uXXXX escaped)."""
    return json.loads(frame.to_json(orient="records", force_ascii=False))


def pct(value, digits=1):
    return f"{100 * float(value):.{digits}f}%"


def num(value):
    return f"{int(value):,}"


def esc(text):
    return html.escape(str(text))


def data_uri(path, max_w=1500, quality=85):
    """Load an image, downscale for web, return a JPEG base64 data URI.

    Raises FileNotFoundError so a missing figure fails loudly instead of
    silently shipping a broken report.
    """
    from PIL import Image  # imported lazily: only report builders need Pillow

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    with Image.open(path) as im:
        im = im.convert("RGB")
        if im.width > max_w:
            ratio = max_w / im.width
            im = im.resize((max_w, int(im.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=quality, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def candidate_enriched(cluster_labels_path):
    """CLUSTER_LABELS tsv -> {sample_id: [cluster_id, ...]} for candidate-enriched clusters."""
    out = {}
    path = Path(cluster_labels_path)
    if not path.exists():
        return out
    with path.open() as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if row.get("malignant_niche_class") == "candidate_enriched":
                out.setdefault(row["sample"], []).append(int(row["cluster_id"]))
    return out


def sample_meta(data, sample_id):
    """Pull the audit row for a sample (falls back to first row)."""
    for row in data.get("audit", []):
        if row.get("sample_id") == sample_id:
            return row
    raise KeyError(f"sample {sample_id!r} not found in audit table")
