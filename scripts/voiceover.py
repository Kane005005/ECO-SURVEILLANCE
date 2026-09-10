#!/usr/bin/env python3
"""Voix off générée (Piper TTS, français) synchronisée sur la vidéo de démo.

Répète le calcul de timeline du montage (intro + scènes + outro, fondus de 0,4 s),
génère une réplique par scène, l'ajuste au timing (atempo) puis muxe la piste
résultante sur la vidéo muette → video/ECO_SURVEILLANCE_DEMO_VO.mp4.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import wave

ROOT = Path(__file__).resolve().parent.parent
SCENES_DIR = ROOT / "video" / "scenes"
TTS_DIR = ROOT / "video" / "tts"
SEG_DIR = TTS_DIR / "segments"
FINAL_SILENT = ROOT / "video" / "ECO_SURVEILLANCE_DEMO.mp4"
FINAL_VO = ROOT / "video" / "ECO_SURVEILLANCE_DEMO_VO.mp4"
TRANS = 0.4
INTRO_DUR = 4.0
OUTRO_DUR = 3.0

MODEL = TTS_DIR / "fr_FR-siwis-medium.onnx"
CONFIG = TTS_DIR / "fr_FR-siwis-medium.onnx.json"

# Texte de narration, aligné sur le scénario docs/SCRIPT_DEMO.md
NARRATION = [
    ("intro", "ECO-SURVEILLANCE Mali. Surveillance environnementale intelligente."),
    ("home", "Données satellite, climat, air et eau, réunies dans une seule plateforme."),
    ("dashboard", "Le tableau de bord national agrège en temps réel climat, hydrologie, qualité de l'air et feux."),
    ("map", "La carte interactive localise les zones surveillées, les feux actifs et les stations."),
    ("zone", "Chaque zone dispose d'un indice environnemental et d'un niveau de risque."),
    ("fires", "Les feux de brousse sont détectés en continu par satellite."),
    ("anomalies", "Les anomalies sont repérées automatiquement."),
    ("ia", "L'IA interprète chaque situation et recommande des actions."),
    ("incidents", "Incidents et interventions sont centralisés et suivis."),
    ("alerts", "Les alertes déclenchent des actions ciblées sur le terrain."),
    ("stations", "Des stations et capteurs simulent la surveillance en continu."),
    ("reports", "Des rapports synthétiques sur l'état de l'environnement."),
    ("iez", "L'indice environnemental de zone oriente les priorités."),
    ("outro", "Surveiller. Alerter. Agir."),
]

VOICE = None


def synth(text, path):
    global VOICE
    if VOICE is None:
        from piper.voice import PiperVoice
        VOICE = PiperVoice.load(str(MODEL), config_path=str(CONFIG))
    chunks = list(VOICE.synthesize(text))
    audio = np.concatenate([c.audio_int16_array for c in chunks])
    sr = chunks[0].sample_rate
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(audio.tobytes())
    return len(audio) / sr


def ffprobe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def atempo(src, dst, factor):
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), "-filter:a", f"atempo={factor}",
         "-ar", "44100", "-ac", "1", str(dst)],
        check=True, capture_output=True)


def build_timeline():
    manifest = json.loads((SCENES_DIR / "manifest.json").read_text())
    durs = [INTRO_DUR]
    for e in manifest:
        v = Path(e["video"])
        raw = ffprobe_duration(v)
        want = min(e.get("duration", 5.0), max(0.8, raw - 1.0))
        durs.append(want)
    durs.append(OUTRO_DUR)

    starts = [0.0]
    cum = durs[0]
    for i in range(1, len(durs)):
        off = cum - TRANS
        starts.append(off + 0.15)
        cum += durs[i] - TRANS
    total = cum
    return durs, starts, total


def main():
    SEG_DIR.mkdir(exist_ok=True)
    durs, starts, total = build_timeline()
    print(f"Timeline: {len(durs)} segments, total {total:.2f}s")

    plan = []
    for (slug, text), dur, start in zip(NARRATION, durs, starts):
        raw_wav = SEG_DIR / f"{slug.upper()}.wav"
        if not raw_wav.exists():
            t = synth(text, raw_wav)
            print(f"  [synth] {slug:10s} {t:.2f}s")
        raw_dur = ffprobe_duration(raw_wav)

        fit_wav = raw_wav
        target = dur - 0.7
        factor = 1.0
        if raw_dur > target and target > 1.5:
            factor = min(raw_dur / target, 1.3)
            if factor >= 1.05:
                fit_wav = SEG_DIR / f"{slug.upper()}_ato.wav"
                atempo(raw_wav, fit_wav, factor)
                raw_dur = ffprobe_duration(fit_wav)
        plan.append({"slug": slug, "wav": fit_wav, "dur": raw_dur,
                     "window": dur, "start": start, "factor": factor})
        print(f"  [fit] {slug:10s} tts={raw_dur:4.2f}s fen={dur:4.2f}s "
              f"atempo={factor:.2f} @ {start:5.2f}s")

    # Graph de mixage : chaque voix retardée à son instant + padding final.
    inputs = []
    graph = []
    labels = []
    for i, seg in enumerate(plan):
        inputs += ["-i", str(seg["wav"])]
        label = f"[v{i}]"
        ms = int(round(seg["start"] * 1000))
        graph.append(f"[{i}:a]aresample=44100,pan=stereo|c0=c0|c1=c0,"
                     f"volume=1.6,adelay={ms}|{ms}{label}")
        labels.append(label)
    graph.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,"
                 "alimiter=limit=0.95[aout]")
    flt = ";".join(graph)

    total_ms = int(round(total * 1000)) + 300
    cmd = ["ffmpeg", "-y", *inputs, "-i", str(FINAL_SILENT),
           "-filter_complex", flt, "-map", f"[aout]", "-map", f"{len(plan)}:v",
           "-t", f"{total_ms/1000:.3f}",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", str(FINAL_VO)]
    subprocess.run(cmd, check=True)
    print("FINAL:", FINAL_VO)
    d = ffprobe_duration(FINAL_VO)
    print("Durée vidéo voix off:", round(d, 2), "s")


if __name__ == "__main__":
    main()