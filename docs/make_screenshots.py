#!/usr/bin/env python3
"""Capture README screenshots of the demo HTML report and demo PPT.

Outputs (docs/images/):
    html-cover.png        report cover with the one-line conclusion
    html-exec.png         executive-summary section
    html-cellmap.png      cell-map section (3 panels per sample)
    ppt-slide01.png       deck cover
    ppt-slide07.png       a two-sample cell-map slide

Run:  python docs/make_screenshots.py
Requires: playwright chromium (HTML) + soffice/pdftoppm (PPT).
"""
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
IMG = HERE / "images"
DEMO = ROOT / "demo" / "project"


def shoot_html():
    from playwright.sync_api import sync_playwright

    url = (DEMO / "report" / "report_leader.html").as_uri()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        page = browser.new_page(viewport={"width": 1200, "height": 860}, device_scale_factor=1.6)
        page.goto(url, wait_until="load", timeout=60000)
        page.wait_for_timeout(1200)
        page.screenshot(path=str(IMG / "html-cover.png"))
        for name, sel in [("html-exec.png", "#s1"), ("html-cellmap.png", "#s5")]:
            page.eval_on_selector(sel, "el => el.scrollIntoView({block:'start'})")
            page.wait_for_timeout(500)
            page.screenshot(path=str(IMG / name))
        browser.close()


def shoot_ppt():
    pptx = DEMO / "ppt" / "output" / "report.pptx"
    if not pptx.exists():
        print(f"skip ppt (missing {pptx})")
        return
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, str(pptx)],
                       check=True, capture_output=True, timeout=300)
        pdf = next(Path(tmp).glob("*.pdf"))
        for page, out in [("1", "ppt-slide01.png"), ("7", "ppt-slide07.png")]:
            subprocess.run(["pdftoppm", "-png", "-r", "110", "-f", page, "-l", page, str(pdf), str(IMG / out.split(".")[0])],
                           check=True, capture_output=True, timeout=120)
    # pdftoppm writes e.g. ppt-slide01-01.png -> keep as-is


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    shoot_html()
    shoot_ppt()
    print(f"screenshots -> {IMG}")


if __name__ == "__main__":
    main()
