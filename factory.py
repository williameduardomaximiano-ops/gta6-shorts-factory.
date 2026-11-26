"""Local, zero-paid-API GTA6 clip prototype. Python 3.10+."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

WORDS = {"caramba", "nossa", "olha", "incrível", "mentira", "impossível",
         "consegui", "explodiu", "missão", "polícia", "fuga", "segredo",
         "easter egg", "wow", "crazy", "insane", "no way"}

def call(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)

def stamp(seconds):
    ms = max(0, round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def candidates(segments, duration, limit):
    scored = []
    for seg in segments:
        start = min(max(0, seg["start"] - 5), max(0, duration - 30))
        end = min(start + 30, duration)
        if end - start < 10:
            continue
        nearby = [s for s in segments if s["end"] > start and s["start"] < end]
        words = " ".join(s["text"] for s in nearby).casefold()
        score = sum(3 for w in WORDS if w in words) + min(len(words.split()), 80) / 20
        scored.append((score, start, end, nearby))
    picked = []
    for item in sorted(scored, key=lambda x: x[0], reverse=True):
        _, a, b, _ = item
        if all(b <= x[1] or a >= x[2] for x in picked):
            picked.append(item)
        if len(picked) >= limit:
            break
    return picked

def make_cuts(args):
    from faster_whisper import WhisperModel
    source = Path(args.source).resolve(strict=True)
    if not source.is_file():
        raise ValueError("Use um arquivo de vídeo autorizado.")
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    probe = call(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                  "-of", "default=noprint_wrappers=1:nokey=1", str(source)],
                 capture_output=True, text=True)
    duration = float(probe.stdout.strip())
    if not 10 <= duration <= args.max_minutes * 60:
        raise ValueError("Duração fora do limite. Divida o vídeo em blocos.")
    model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=4)
    stream, _ = model.transcribe(str(source), vad_filter=True, language=args.language)
    segments = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in stream]
    manifest = []
    for i, (score, a, b, near) in enumerate(candidates(segments, duration, args.limit), 1):
        stem = f"clip_{i:02}"
        srt = out / (stem + ".srt")
        entries = []
        for s in near:
            start, end = max(a, s["start"]) - a, min(b, s["end"]) - a
            if end > start and s["text"]:
                clean = re.sub(r"[\r\n]+", " ", s["text"])
                entries.append(f"{len(entries)+1}\n{stamp(start)} --> {stamp(end)}\n{clean}\n")
        srt.write_text("\n".join(entries), encoding="utf-8")
        vf = ("scale=1080:1920:force_original_aspect_ratio=decrease:force_divisible_by=2,"
              "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,"
              f"subtitles={srt.name}:force_style='FontSize=16,Alignment=2,MarginV=45,Outline=2'")
        target = out / (stem + ".mp4")
        call(["ffmpeg", "-nostdin", "-v", "error", "-n", "-ss", str(a), "-i", str(source),
              "-t", str(b-a), "-map", "0:v:0", "-map", "0:a:0?", "-vf", vf,
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-movflags", "+faststart", str(target)], cwd=out)
        digest = hash_file(target)
        manifest.append({"id": stem, "video": target.name, "sha256": digest,
                         "start": a, "end": b, "score": score, "status": "pending_review",
                         "transcript": " ".join(s["text"] for s in near)})
    (out / "review.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(manifest)} cortes criados. Revise os vídeos antes de aprovar.")

def hash_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def review(args):
    path = Path(args.output).resolve() / "review.json"
    items = json.loads(path.read_text(encoding="utf-8"))
    item = next((x for x in items if x["id"] == args.clip), None)
    if item is None:
        raise ValueError("Corte não encontrado.")
    if hash_file(path.parent / item["video"]) != item["sha256"]:
        raise ValueError("Vídeo alterado; gere um novo corte.")
    item["status"] = args.decision
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)
    print(f"{args.clip}: {args.decision}. Nenhuma publicação foi realizada.")

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    cut = sub.add_parser("cut")
    cut.add_argument("source")
    cut.add_argument("--output", required=True)
    cut.add_argument("--authorized", action="store_true", required=True)
    cut.add_argument("--model", default="base", choices=["tiny", "base", "small"])
    cut.add_argument("--language", default=None)
    cut.add_argument("--limit", type=int, choices=range(1, 6), default=3)
    cut.add_argument("--max-minutes", type=int, choices=range(1, 31), default=15)
    cut.set_defaults(run=make_cuts)
    r = sub.add_parser("review")
    r.add_argument("--output", required=True)
    r.add_argument("--clip", required=True)
    r.add_argument("--decision", choices=["approved", "rejected"], required=True)
    r.set_defaults(run=review)
    args = p.parse_args()
    args.run(args)

if __name__ == "__main__":
    main()
