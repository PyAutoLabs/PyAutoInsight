"""Real Chromium interaction/viewport check, run separately from hermetic pytest."""

import json
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from insight import board, ingest, registry  # noqa: E402


def main():
    from playwright.sync_api import sync_playwright

    doc = json.loads((ROOT / "tests/fixtures/lens_summary_v2.json").read_text())
    other = deepcopy(doc["setups"][0])
    other.update(id="imaging/delaunay/euclid", instrument="euclid", label="Euclid Delaunay")
    doc["setups"].append(other)
    numba = deepcopy(doc["records"][0])
    numba.update(
        id="numba-only-record", backend="numba_cpu", sampler="numba-only-sampler", archived=False
    )
    doc["records"].append(numba)
    instance = registry.Instance(
        "lens",
        "autolens_inference",
        "dashboard/catalogue.json",
        "inference-summary@2",
        "https://example.invalid/",
        github="PyAutoLabs/autolens_inference",
    )
    snapshot = ingest.Snapshot(
        instance, "ok", "remote", doc=doc, commit="a" * 40, fetched_at="2026-10-08T00:00:00Z"
    )
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp, sync_playwright() as p:
        path = Path(tmp) / "index.html"
        path.write_text(board.render_html([snapshot]))
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        context.add_init_script(
            "Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async(t)=>{window.copiedPrompt=t}}})"
        )
        page = context.new_page()
        errors = []
        context.on("page", lambda tab: tab.on("pageerror", lambda error: errors.append(str(error))))
        page.goto(path.as_uri())
        assert page.locator("#inference-home").is_visible()
        assert not page.locator("#inference-pages").is_visible()
        page.locator("h2#evidence").locator("xpath=ancestor::details[1]").evaluate("e=>e.open=true")
        page.locator("summary", has_text="PyAutoLens").last.click()
        page.locator("summary", has_text="Imaging").first.click()
        with page.expect_popup() as popup:
            page.locator(".setup-choice").first.click()
        detail = popup.value
        detail.wait_for_load_state()
        assert "view=setup" in detail.url
        assert not detail.locator("#inference-home").is_visible()
        assert detail.locator(".setup-page:not([hidden]) h1").inner_text() == "Delaunay"
        assert (
            detail.locator(".setup-page:not([hidden])")
            .get_by_text("No accepted baseline selected", exact=True)
            .is_visible()
        )
        detail.locator(".setup-page:not([hidden]) summary", has_text="smc ·").click()
        assert (
            detail.locator(
                ".setup-page:not([hidden]) summary", has_text="mass_total[1] · warm"
            ).count()
            == 1
        )
        active = detail.locator(".setup-page:not([hidden])")
        assert "numba-only-sampler" not in active.inner_text()
        active.locator("[data-instrument]").select_option(label="EUCLID")
        assert "euclid" in detail.url and "implementation=jax" in detail.url
        assert (
            "No recorded Delaunay results"
            in detail.locator(".setup-page:not([hidden])").inner_text()
        )
        detail.go_back()
        assert "hst" in detail.url
        assert (
            detail.locator(
                ".setup-page:not([hidden]) [data-instrument] option:checked"
            ).inner_text()
            == "HST"
        )
        detail.goto(
            path.as_uri()
            + "?view=setup&instance=lens&setup=imaging%2Fdelaunay%2Fhst&implementation=numba"
        )
        active = detail.locator(".setup-page:not([hidden])")
        assert active.locator("h1").inner_text() == "Delaunay (Numba)"
        assert active.locator("summary", has_text="numba-only-sampler").count() == 1
        assert active.locator("summary", has_text="smc ·").count() == 0
        # Routine provenance is accessible but not expanded on the page.
        assert not active.get_by_text("Captured source branch:", exact=False).is_visible()
        detail.set_viewport_size({"width": 390, "height": 844})
        assert detail.evaluate("document.documentElement.scrollWidth <= innerWidth")
        detail.goto(path.as_uri() + "?view=setup&instance=lens&setup=imaging%2Fdelaunay%2Fhst")
        assert detail.locator(".setup-page:not([hidden]) h1").inner_text() == "Delaunay"
        detail.goto(path.as_uri() + "?view=setup&instance=lens&setup=missing")
        assert detail.locator("#inference-home").is_visible()
        assert "unavailable" in detail.locator("#setup-route-status").inner_text()
        detail.go_back()
        assert detail.locator(".setup-page:not([hidden]) h1").is_visible()
        page.locator("#sampler-candidates").locator("xpath=ancestor::details[1]").evaluate(
            "e=>e.open=true"
        )
        page.locator("summary", has_text="dynesty").click()
        panel = page.locator("[data-candidate]").first
        panel.locator("details").evaluate("e=>e.open=true")
        panel.locator("textarea").fill("Edited investigation prompt")
        panel.locator("button").click()
        assert page.evaluate("window.copiedPrompt") == "Edited investigation prompt"
        page.evaluate(
            "Object.defineProperty(navigator,'clipboard',{value:undefined,configurable:true})"
        )
        panel.locator("button").click()
        assert "Select and copy" in panel.locator('[role="status"]').inner_text()
        nojs = browser.new_context(java_script_enabled=False)
        fallback = nojs.new_page()
        fallback.goto(path.as_uri())
        assert fallback.locator("#inference-pages").is_visible()
        fallback.locator(".setup-page>summary").first.click()
        assert fallback.locator(".setup-page h1").first.is_visible()
        assert not errors, errors
        browser.close()
    print(
        "Chromium: new tab, history, empty route, editable copy/fallback, no-JS and mobile viewport passed"
    )


if __name__ == "__main__":
    main()
