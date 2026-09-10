#!/usr/bin/env python3
"""Capture automatique des scènes ECO-SURVEILLANCE MALI pour la vidéo de démo.

Pour chaque scène : ouverture d'un contexte Playwright dédié (1280×720), 
navigation, interactions éventuelles, enregistrement vidéo (.webm) + screenshot.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SCENES_DIR = ROOT / "video" / "scenes"
SCENES_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://127.0.0.1:8000"
W, H = 1280, 720


# ── Utilitaires ────────────────────────────────────────────────────────────────
def ensure_server():
    try:
        urllib.request.urlopen(BASE_URL + "/", timeout=3)
        return
    except Exception:
        pass
    print("Démarrage du serveur Django…")
    subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "0.0.0.0:8000"],
        cwd=ROOT,
        stdout=open("/tmp/eco_server.log", "w"),
        stderr=subprocess.STDOUT,
    )
    for _ in range(30):
        try:
            urllib.request.urlopen(BASE_URL + "/", timeout=2)
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("Serveur Django introuvable")


def settle(page, ms=1500):
    page.wait_for_timeout(ms)


def scroll_down(page, steps, step_wait, delta=500):
    for _ in range(steps):
        page.mouse.wheel(0, delta)
        page.wait_for_timeout(step_wait)


def scroll_up(page, steps, step_wait, delta=500):
    for _ in range(steps):
        page.mouse.wheel(0, -delta)
        page.wait_for_timeout(step_wait)


def hover_center(page, selector, label=""):
    locator = page.locator(selector).first
    if locator.count() == 0:
        return
    box = locator.bounding_box()
    if not box:
        return
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.wait_for_timeout(700)


# ── Interactions par scène ─────────────────────────────────────────────────────
def scene_home(page, duration):
    settle(page, 1200)
    scroll_down(page, 4, 550)
    scroll_up(page, 4, 430)


def scene_dashboard(page, duration):
    page.wait_for_load_state("networkidle", timeout=8000)
    settle(page, 2500)
    hover_center(page, "div[class*='kpi']", "KPI")
    page.wait_for_timeout(500)
    try:
        page.click("#btn-tab-feux")
        page.wait_for_timeout(1200)
    except Exception:
        pass
    scroll_down(page, 3, 700)
    scroll_up(page, 2, 500)


def scene_map(page, duration):
    page.wait_for_load_state("networkidle", timeout=8000)
    settle(page, 3000)
    try:
        page.evaluate("() => { if (typeof toggleLayer === 'function') toggleLayer('fires'); }")
        page.wait_for_timeout(1500)
        result = page.evaluate(
            """() => {
                const fs = [];
                if (window.grps && grps.fires) grps.fires.eachLayer(m => fs.push(m));
                if (!fs.length) return null;
                const first = fs[0];
                try {
                    if (grps.fires.zoomToShowLayer) {
                        grps.fires.zoomToShowLayer(first, () => first.openPopup());
                    } else {
                        const ll = first.getLatLng();
                        map.flyTo([ll.lat, ll.lng], 12, { duration: 1.5 });
                        setTimeout(() => first.openPopup(), 1800);
                    }
                } catch (e) {}
                const ll = first.getLatLng();
                return [ll.lat, ll.lng];
            }"""
        )
        if result:
            page.wait_for_timeout(3200)
        else:
            page.evaluate("() => map.setZoom(8, { animate: true })")
            page.wait_for_timeout(2500)
    except Exception:
        page.evaluate("() => map && map.setZoom(8, { animate: true })")
        page.wait_for_timeout(2500)


def scene_scroll(page, duration):
    settle(page, 1000)
    scroll_down(page, 4, 650)


SCENES = [
    {"slug": "home", "url": "/", "duration": 5.0, "run": scene_home},
    {"slug": "dashboard", "url": "/dashboard/", "duration": 8.0, "run": scene_dashboard},
    {"slug": "map", "url": "/map/", "duration": 9.0, "run": scene_map},
    {"slug": "zone", "url": "/zones/1/", "duration": 5.0, "run": scene_scroll},
    {"slug": "fires", "url": "/fires/", "duration": 4.0, "run": scene_scroll},
    {"slug": "anomalies", "url": "/anomalies/", "duration": 4.0, "run": scene_scroll},
    {"slug": "ia", "url": "/ai/", "duration": 4.0, "run": scene_scroll},
    {"slug": "incidents", "url": "/incidents/", "duration": 4.0, "run": scene_scroll},
    {"slug": "alerts", "url": "/alerts/", "duration": 4.0, "run": scene_scroll},
    {"slug": "stations", "url": "/stations/", "duration": 5.0, "run": scene_scroll},
    {"slug": "reports", "url": "/reports/", "duration": 4.0, "run": scene_scroll},
    {"slug": "iez", "url": "/iez/", "duration": 4.0, "run": scene_scroll},
]


def capture_scene(browser, scene, index):
    slug = scene["slug"]
    out_dir = SCENES_DIR / f"{index:02d}_{slug}"
    out_dir.mkdir(exist_ok=True)

    ctx = browser.new_context(
        viewport={"width": W, "height": H},
        device_scale_factor=1,
        record_video_dir=out_dir,
        record_video_size={"width": W, "height": H},
        locale="fr-FR",
    )
    ctx.set_default_timeout(60000)
    page = ctx.new_page()
    t0 = time.time()
    page.goto(BASE_URL + scene["url"], wait_until="domcontentloaded", timeout=60000)
    settle(page, 1200)

    expires = t0 + scene["duration"]
    scene["run"](page, scene["duration"])

    remaining = expires - time.time()
    if remaining > 0:
        page.wait_for_timeout(int(remaining * 1000))

    snapshot = None
    try:
        snapshot = str(out_dir / "shot.png")
        page.screenshot(path=snapshot)
    except Exception:
        pass

    video_path = None
    ctx.close()
    try:
        video_path = page.video.path()
    except Exception:
        pass

    print(f"[{index}] {slug}: {video_path or 'NO VIDEO'}", flush=True)
    return {"slug": slug, "url": scene["url"], "video": video_path, "shot": snapshot}


def warm_up(browser):
    """Charge chaque page dans un contexte jetable pour remplir le cache HTTP/CDN."""
    ctx = browser.new_context(viewport={"width": W, "height": H}, locale="fr-FR")
    pg = ctx.new_page()
    pg.set_default_timeout(60000)
    for scene in SCENES:
        try:
            pg.goto(BASE_URL + scene["url"], wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(1500)
        except Exception as e:
            print("warm-up échoué pour", scene["url"], e)
    ctx.close()
    print("Cache HTTP préchauffé.", flush=True)


def main():
    ensure_server()
    manifest = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        warm_up(browser)
        for idx, scene in enumerate(SCENES):
            manifest.append(capture_scene(browser, scene, idx))
        browser.close()
    with open(SCENES_DIR / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print("Manifest:", SCENES_DIR / "manifest.json")


if __name__ == "__main__":
    main()