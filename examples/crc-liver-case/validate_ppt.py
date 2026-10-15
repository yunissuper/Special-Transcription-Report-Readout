#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path("<PROJECT_ROOT>")
PPT_ROOT = ROOT / "ppt"
sys.path.insert(0, str(PPT_ROOT / "python_lib"))

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

PPTX = PPT_ROOT / "output/demo_current_zh.pptx"
DATA = ROOT / "report/report_data_current.json"
OUTPUT = PPT_ROOT / "output/validation_current.json"


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    presentation = Presentation(PPTX)
    texts = []
    pictures = 0
    overflow = []
    empty_slides = []
    for slide_number, slide in enumerate(presentation.slides, start=1):
        slide_text = []
        for shape in slide.shapes:
            if shape.left < 0 or shape.top < 0 or shape.left + shape.width > presentation.slide_width or shape.top + shape.height > presentation.slide_height:
                overflow.append({"slide": slide_number, "shape": shape.name})
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                pictures += 1
            if hasattr(shape, "text") and shape.text.strip():
                slide_text.append(shape.text.strip())
        if not slide_text:
            empty_slides.append(slide_number)
        texts.extend(slide_text)
    all_text = "\n".join(texts)
    audit = {row["sample_id"]: row for row in data["audit"]}
    consensus = {row["sample"]: row for row in data["consensus_qc"]}
    rctd = data["rctd_summary"]
    forbidden = ["CUT&Tag", "ChIP-seq", "Peak Calling", "九象限"]
    required_fragments = [
        "一句话结论",
        "segmented cells",  # analysis unit
        "8 µm",  # grid used for spatial validation, not single cells
        "空间蛋白组",
        "RCTD",
        "病理",
        "CNV",
        "HCC/ICC 亚型未定",
        "肝原发肿瘤" if "肝癌" not in all_text else "肝癌",
        "肿瘤性上皮候选",
        "候选富集区域",
        f'{audit["sample_A"]["matrix_cells"]:,}',
        f'{audit["sample_B"]["matrix_cells"]:,}',
        f'{consensus["sample_A"]["malignant_candidates"]:,}',
        f'{consensus["sample_B"]["malignant_candidates"]:,}',
        f'{rctd["sample_A"]["cell_compartment_agreement"]:.1%}',
        f'{rctd["sample_B"]["cell_compartment_agreement"]:.1%}',
    ]
    # Core complaint guard: a slide that is liver-focused (mentions 肝/liver but
    # no colon context) must never carry CRC-family wording. Slides that compare
    # both samples may legitimately say "结肠：CRC Atlas；肝：肝癌参考".
    crc_terms = ["CRC", "CRLM", "结直肠癌", "结肠癌", "colorectal", "结直肠"]
    colon_markers = ["colon", "结肠", "CRC", "结直肠"]
    liver_crc_hits = []
    for slide in presentation.slides:
        texts = [sh.text.strip() for sh in slide.shapes if hasattr(sh, "text") and sh.text.strip()]
        slide_text = "\n".join(texts)
        has_liver = ("肝" in slide_text) or ("liver" in slide_text)
        has_colon = any(m in slide_text for m in colon_markers)
        if has_liver and not has_colon:
            for term in crc_terms:
                if term in slide_text:
                    liver_crc_hits.append(f"slide_liver-only term='{term}' text='{slide_text[:90]}'")
    result = {
        "pptx": str(PPTX),
        "slides": len(presentation.slides),
        "slide_count_ok": 18 <= len(presentation.slides) <= 22,
        "pictures": pictures,
        "pictures_ok": pictures >= 8,
        "overflow_shapes": overflow,
        "overflow_ok": not overflow,
        "empty_slides": empty_slides,
        "empty_slides_ok": not empty_slides,
        "forbidden_terms": {term: term in all_text for term in forbidden},
        "forbidden_terms_ok": not any(term in all_text for term in forbidden),
        "liver_crc_hits": liver_crc_hits,
        "liver_crc_ok": not liver_crc_hits,
        "required_fragments": {term: term in all_text for term in required_fragments},
        "required_fragments_ok": all(term in all_text for term in required_fragments),
    }
    result["ok"] = all([
        result["slide_count_ok"],
        result["pictures_ok"],
        result["overflow_ok"],
        result["empty_slides_ok"],
        result["forbidden_terms_ok"],
        result["liver_crc_ok"],
        result["required_fragments_ok"],
    ])
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
