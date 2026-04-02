#!/usr/bin/env python3
"""Extract Japanese subtitles from MKV and merge with English .ass into combined .srt.

Usage:
    python extract.py --input-folder /path/to/mkv/folder

This script processes MKV files in the input folder, extracts embedded Japanese subtitles,
finds corresponding English .ass/.srt files, and creates combined .srt files in the same directory.

Requirements:
- ffmpeg and ffprobe (for subtitle extraction/conversion)
- pysrt (Python library for SRT manipulation)

Install:
    pip install pysrt
    # ffmpeg: download from https://ffmpeg.org/download.html or use package manager
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import pysrt
except ImportError as exc:
    print("Missing dependency: pysrt. Install it via 'pip install pysrt'", file=sys.stderr)
    raise


def run_cmd(cmd, capture_output=False, check=True):
    """Run a command and handle errors."""
    result = subprocess.run(cmd, shell=False, capture_output=capture_output, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


def get_japanese_subtitle_stream(mkv_path):
    """Find the Japanese subtitle stream index in the MKV file."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "s",
        "-show_entries",
        "stream=index:stream_tags=language,title",
        "-of",
        "json",
        str(mkv_path),
    ]
    res = run_cmd(cmd, capture_output=True)
    import json

    data = json.loads(res.stdout or "{}")
    streams = data.get("streams", [])

    if not streams:
        return None

    candidate = None
    for stream in streams:
        tags = stream.get("tags", {})
        lang = (tags.get("language") or "").lower()
        if lang in ("jpn", "ja", "japanese"):
            return int(stream["index"])
        if lang == "und":
            candidate = int(stream["index"])

    if candidate is not None:
        return candidate

    # fallback first subtitle stream
    return int(streams[0]["index"])


def extract_subtitle_stream(mkv_path, stream_index, out_srt_path):
    """Extract subtitle stream from MKV to SRT."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(mkv_path),
        "-map",
        f"0:{stream_index}",
        str(out_srt_path),
    ]
    run_cmd(cmd, capture_output=False, check=True)


def convert_ass_to_srt(ass_path, srt_path):
    """Convert ASS subtitle to SRT."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(ass_path),
        str(srt_path),
    ]
    run_cmd(cmd, capture_output=False, check=True)


def parse_show_season_episode(filename):
    """Parse show name, season, episode from filename."""
    base = Path(filename).stem
    normalized = base.replace('.', ' ').replace('_', ' ')

    season = None
    episode = None
    week = None

    s_match = re.search(r"S(\d{2})", base, re.IGNORECASE)
    if s_match:
        season = int(s_match.group(1))

    e_match = re.search(r"E(\d{2})", base, re.IGNORECASE)
    if e_match:
        episode = int(e_match.group(1))

    w_match = re.search(r"Week(\d{1,2})", base, re.IGNORECASE)
    if w_match:
        week = int(w_match.group(1))

    show = normalized
    if season is not None:
        show = re.split(r"S\d{2}", normalized, flags=re.IGNORECASE)[0].strip()

    if episode is None and week is not None:
        episode = week

    return show, season, episode, week


def find_english_subtitle(mkv_path, input_folder):
    """Find the corresponding English subtitle file (.ass or .srt)."""
    base = Path(mkv_path).stem
    candidates = list(Path(input_folder).glob("**/*.ass")) + list(Path(input_folder).glob("**/*.srt"))

    # exact name first
    for c in candidates:
        if c.stem.lower() == base.lower():
            return c

    # fallback nearest by prefix
    base_lower = base.lower()
    best = None
    best_score = 0
    for c in candidates:
        name = c.stem.lower()
        common = os.path.commonprefix([name, base_lower])
        if len(common) > best_score:
            best_score = len(common)
            best = c
    return best


def merge_subtitles(jpn_srt_path, eng_srt_path, out_srt_path):
    """Merge Japanese and English SRT files into one."""
    jpn_subs = pysrt.open(str(jpn_srt_path), encoding='utf-8')
    eng_subs = pysrt.open(str(eng_srt_path), encoding='utf-8')

    out_subs = pysrt.SubRipFile()
    if len(jpn_subs) == len(eng_subs):
        for jpn_item, eng_item in zip(jpn_subs, eng_subs):
            text = jpn_item.text.strip()
            if eng_item.text.strip():
                if text:
                    text = text + "\n" + eng_item.text.strip()
                else:
                    text = eng_item.text.strip()
            out_item = pysrt.SubRipItem(
                index=jpn_item.index,
                start=jpn_item.start,
                end=jpn_item.end,
                text=text,
            )
            out_subs.append(out_item)
    else:
        # fallback merging by chronological order
        merged = []
        for item in jpn_subs:
            merged.append((item.start.to_time(), 'jpn', item))
        for item in eng_subs:
            merged.append((item.start.to_time(), 'eng', item))
        merged.sort(key=lambda x: x[0])

        for idx, (_t, _kind, item) in enumerate(merged, start=1):
            if _kind == 'jpn':
                text = item.text.strip()
            else:
                text = item.text.strip()
            out_subs.append(
                pysrt.SubRipItem(index=idx, start=item.start, end=item.end, text=text)
            )

    out_subs.save(str(out_srt_path), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description="Extract and combine Japanese+English subtitles from MKV")
    parser.add_argument("--input-folder", required=True, help="Folder containing MKV and ASS/SRT files")
    parser.add_argument("--output-folder", default=None, help="Optional root folder for output; if omitted, uses same folder as each MKV")
    args = parser.parse_args()

    input_folder = Path(args.input_folder).expanduser().resolve()
    if not input_folder.exists():
        raise SystemExit(f"Error: input-folder '{input_folder}' does not exist")

    output_root = Path(args.output_folder).expanduser().resolve() if args.output_folder else None

    mkv_files = sorted(input_folder.glob("**/*.mkv"))
    if not mkv_files:
        print("No MKV files found in", input_folder)
        return

    for mkv_file in mkv_files:
        print("Processing", mkv_file)
        show_name, season, episode, week = parse_show_season_episode(mkv_file.name)
        season_label = f"Season {season:02d}" if season is not None else None
        ep_label = f"E{episode:02d}" if episode is not None else None

        if output_root:
            try:
                rel_path = mkv_file.parent.relative_to(input_folder)
            except ValueError:
                rel_path = mkv_file.parent
            out_dir = output_root / rel_path
        else:
            out_dir = mkv_file.parent

        out_dir.mkdir(parents=True, exist_ok=True)

        out_srt = out_dir / f"{mkv_file.stem}.srt"
        if out_srt.exists():
            print(f"Skipped {mkv_file.name}: SRT already exists")
            continue

        eng_sub = find_english_subtitle(mkv_file, input_folder)
        if eng_sub is None:
            print(f"Skipped {mkv_file.name}: no English .ass/.srt file found")
            continue

        stream_index = get_japanese_subtitle_stream(mkv_file)
        if stream_index is None:
            print(f"Skipped {mkv_file.name}: no subtitle stream found")
            continue

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            tmp_jpn = tmp_dir / "jpn.srt"
            tmp_eng = tmp_dir / "eng.srt"
            try:
                extract_subtitle_stream(mkv_file, stream_index, tmp_jpn)
            except Exception as exc:
                print(f"Failed to extract JAP sub for {mkv_file.name}: {exc}")
                continue

            try:
                if eng_sub.suffix.lower() == '.ass':
                    convert_ass_to_srt(eng_sub, tmp_eng)
                else:
                    shutil.copyfile(eng_sub, tmp_eng)
                
            except Exception as exc:
                print(f"Failed to convert ENG subtitle for {mkv_file.name}: {exc}")
                continue

            try:
                merge_subtitles(tmp_jpn, tmp_eng, out_srt)
                print("Created", out_srt)
            except Exception as exc:
                print(f"Failed to merge subs for {mkv_file.name}: {exc}")


if __name__ == '__main__':
    main()

