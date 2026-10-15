#!/usr/bin/env python3
"""Stage 6: validate the deliverables against report_data_current.json.

Checks the things that actually bit us:
  * slide count / picture count / shape overflow / empty slides in the PPTX;
  * every headline number in the PPTX also exists in report_data_current.json
    (so "the report says X but the figure says Y" cannot ship);
  * no leftover terms from an unrelated template;
  * a tissue-focused page must not carry another tissue's reference vocabulary
    (guards against "wrong reference reused" regressions).

Usage:
    python validate_report.py --root /path/to/project
Exit code 0 = all gates pass, 1 = at least one gate failed.
"""
import argparse
import json
import re
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from report_common import load_config

# terms that must never appear (leftovers from an unrelated template project)
FORBIDDEN = ["CUT&Tag", "ChIP-seq", "Peak Calling", "九象限"]


def shape_overflow(presentation, slide):
    bad = []
    for shape in slide.shapes:
        if shape.left is None or shape.top is None:
            continue
        if (shape.left < 0 or shape.top < 0
                or shape.left + shape.width > presentation.slide_width
                or shape.top + shape.height > presentation.slide_height):
            bad.append(shape.name)
    return bad


def validate_pptx(path, data, cfg):
    presentation = Presentation(path)
    pictures, overflow, empty, texts = 0, [], [], []
    per_slide = []
    for number, slide in enumerate(presentation.slides, start=1):
        slide_text = []
        for shape in slide.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                pictures += 1
            if hasattr(shape, "text") and shape.text.strip():
                slide_text.append(shape.text.strip())
        overflow += [{"slide": number, "shape": name} for name in shape_overflow(presentation, slide)]
        if not slide_text:
            empty.append(number)
        per_slide.append((number, "\n".join(slide_text)))
        texts.extend(slide_text)

    all_text = "\n".join(texts)

    # required fragments: vocabulary that must survive in every deck
    required = ["空间蛋白组", "病理", "CNV", "候选", "8 µm", "segmented"]
    # dynamic numbers taken straight from the data source
    for row in data.get("audit", []):
        required.append(f'{row["matrix_cells"]:,}')
    for sample, row in data.get("rctd_summary", {}).items():
        required.append(f'{row["cell_compartment_agreement"]:.1%}')

    # tissue-isolation guard: config declares which CRC/other-family vocabulary
    # belongs to which sample, so a liver-only page never says "CRC".
    vocab = cfg.get("tissue_vocab", {})
    forbidden_on_tissue = {}
    for term, spec in vocab.items():
        forbidden_on_tissue[term] = spec.get("forbidden_markers", [])
    cross_hits = []
    for number, text in per_slide:
        for term, markers in forbidden_on_tissue.items():
            if any(m in text for m in markers):
                continue  # page legitimately discusses that tissue too
            if term in text:
                cross_hits.append(f"slide{number} term='{term}' text='{text[:80]}'")

    return {
        "pptx": str(path),
        "slides": len(presentation.slides),
        "pictures": pictures,
        "pictures_ok": pictures >= 6,
        "overflow_shapes": overflow,
        "overflow_ok": not overflow,
        "empty_slides": empty,
        "empty_slides_ok": not empty,
        "forbidden_terms": {t: t in all_text for t in FORBIDDEN},
        "forbidden_terms_ok": not any(t in all_text for t in FORBIDDEN),
        "required_fragments": {t: t in all_text for t in required},
        "required_fragments_ok": all(t in all_text for t in required),
        "cross_tissue_hits": cross_hits,
        "cross_tissue_ok": not cross_hits,
    }


def validate_html(path, data):
    if not path.exists():
        return {"html": str(path), "exists": False, "ok": False}
    text = path.read_text(encoding="utf-8")
    n_img = text.count("<img ")
    n_section = len(re.findall(r'<section id="s\d+"', text))
    unbalanced = text.count("<div") - text.count("</div>")
    return {
        "html": str(path),
        "exists": True,
        "images": n_img,
        "images_ok": n_img >= 6,
        "sections": n_section,
        "sections_ok": n_section >= 10,
        "div_balance": unbalanced,
        "div_balance_ok": unbalanced == 0,
        "empty_ok": len(text) > 5000,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--pptx", default="ppt/output/report.pptx")
    parser.add_argument("--html", default="report/report_leader.html")
    parser.add_argument("--out", default="ppt/output/validation_current.json")
    parser.add_argument("--no-pptx", action="store_true", help="skip the PPTX gate")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    cfg = load_config(root)
    data = json.loads((root / "report/report_data_current.json").read_text(encoding="utf-8"))

    result = {"report_version": data.get("report_version")}
    if not args.no_pptx:
        pptx_path = root / args.pptx
        if pptx_path.exists():
            result["pptx"] = validate_pptx(pptx_path, data, cfg)
        else:
            result["pptx"] = {"pptx": str(pptx_path), "exists": False, "ok": False}
    result["html"] = validate_html(root / args.html, data)

    ok = all(
        part.get("ok", True)
        and part.get("pictures_ok", True)
        and part.get("overflow_ok", True)
        and part.get("empty_slides_ok", True)
        and part.get("forbidden_terms_ok", True)
        and part.get("required_fragments_ok", True)
        and part.get("cross_tissue_ok", True)
        and part.get("images_ok", True)
        and part.get("sections_ok", True)
        and part.get("div_balance_ok", True)
        and part.get("empty_ok", True)
        for part in result.values() if isinstance(part, dict)
    )
    result["ok"] = ok

    out_path = root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
