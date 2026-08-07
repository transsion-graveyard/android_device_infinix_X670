#!/usr/bin/env python3
"""Analyze gfxinfo summary + framestats dumps from capture.sh for UX frame-time work.

Outputs, for the given framestats file:
  - frame-time distribution (p50/p90/p95/p99/max, ms)
  - drop-rate buckets (>1 vsync, >2 vsync, >3 vsync, >100ms)
  - where time goes: input / animation / traversals / hwui phases (if columns present)

Usage:
  analyze_gfxinfo.py out/TAG/framestats_<pkg>.txt [more_framestats...]
  analyze_gfxinfo.py out/TAG/gfxinfo_summary.txt --summary
"""
import argparse
import os
import sys

NS_TO_MS = 1_000_000.0

COLUMNS = [
    "intendedVsync", "frameDeadline", "frameStart", "frameDuration",
    "frameCompleted", "frameInterval", "vsyncNumber", "processStartTime",
    "handleInputStart", "animationStart", "performTraversalsStart",
    "drawStart", "syncStart", "issueDrawCommandsStart", "swapBuffers",
    "frameCompleted2",
]


def pct(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    idx = int(round(p / 100.0 * (len(sorted_vals) - 1)))
    return sorted_vals[idx] / NS_TO_MS


def fmt_ms(ns):
    return f"{ns / NS_TO_MS:.2f}"


def read_framestats(path):
    """Parse a `dumpsys gfxinfo <pkg> framestats` dump. Returns dict of stats."""
    header = None
    frames = []
    with open(path, errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.startswith("AppPackage:"):
                continue
            if line.startswith("RefreshPeriod:"):
                continue
            if line.startswith("HISTOGRAM:"):
                continue
            if "," not in line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if header is None:
                header = parts
                continue
            try:
                vals = [int(p) for p in parts if p.lstrip("-").isdigit()]
            except ValueError:
                continue
            if not vals:
                continue
            frames.append(vals)

    if header is None or not frames:
        return None

    def col(name):
        return header.index(name) if name in header else None

    idx = {name: col(name) for name in COLUMNS}

    rows = []
    for f in frames:
        def g(name, default=None):
            i = idx.get(name)
            if i is None or i >= len(f):
                return default
            return f[i]

        row = {
            "start": g("frameStart"),
            "completed": g("frameCompleted"),
            "intended": g("intendedVsync"),
            "input_start": g("handleInputStart"),
            "anim_start": g("animationStart"),
            "traversals_start": g("performTraversalsStart"),
            "draw_start": g("drawStart"),
            "swap": g("swapBuffers"),
        }
        if row["start"] is None or row["completed"] is None:
            continue
        total = row["completed"] - row["start"]
        if total <= 0:
            continue
        rows.append((row, total))

    if not rows:
        return None

    totals = sorted(t for _, t in rows)
    n = len(totals)
    refresh = 16.666
    over = {
        ">1 vsync (16.6ms)": sum(1 for t in totals if t > refresh * NS_TO_MS),
        ">2 vsync (33.3ms)": sum(1 for t in totals if t > refresh * 2 * NS_TO_MS),
        ">3 vsync (50.0ms)": sum(1 for t in totals if t > refresh * 3 * NS_TO_MS),
        ">100ms": sum(1 for t in totals if t > 100 * NS_TO_MS),
    }

    phases = {}
    for phase, a, b in (
        ("input", "input_start", "anim_start"),
        ("animation", "anim_start", "traversals_start"),
        ("traversals/draw", "traversals_start", "draw_start"),
        ("hwui(render)", "draw_start", "swap"),
    ):
        vals = sorted(
            (r[b] - r[a])
            for r, _ in rows
            if r[a] is not None and r[b] is not None and r[b] - r[a] >= 0
        )
        if vals:
            phases[phase] = {
                "p50": pct(vals, 50),
                "p95": pct(vals, 95),
                "max": max(vals) / NS_TO_MS,
            }

    return {
        "n": n,
        "refresh_ms": refresh,
        "totals": totals,
        "over": over,
        "phases": phases,
    }


def parse_summary(path):
    """Parse `dumpsys gfxinfo` (no package) summary block."""
    import re

    result = {}
    pats = {
        "total_frames": r"Total frames rendered:\s*(\d+)",
        "janky": r"Janky frames:\s*(\d+)\s*\(([\d.]+)%\)",
        "p50": r"50th percentile:\s*(\d+)ms",
        "p90": r"90th percentile:\s*(\d+)ms",
        "p95": r"95th percentile:\s*(\d+)ms",
        "p99": r"99th percentile:\s*(\d+)ms",
        "missed_vsync": r"Number Missed Vsync:\s*(\d+)",
        "slow_ui": r"Number Slow UI thread:\s*(\d+)",
        "slow_bitmap": r"Number Slow bitmap uploads:\s*(\d+)",
        "slow_draw": r"Number Slow draw:\s*(\d+)",
    }
    current = None
    with open(path, errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            m = re.match(r"^\*\* Graphics info for pid \d+ \[([^\]]+)\] \*\*$", line)
            if m:
                current = m.group(1)
            for key, pat in pats.items():
                m = re.search(pat, line)
                if m:
                    result.setdefault(key, {})
                    val = m.group(2) if len(m.groups()) > 1 else int(m.group(1))
                    if key == "janky":
                        result[key][current or "?"] = (int(m.group(1)), m.group(2))
                    else:
                        result[key][current or "?"] = val
    return result


def main():
    ap = argparse.ArgumentParser(description="Analyze gfxinfo framestats/summary dumps")
    ap.add_argument("files", nargs="+", help="framestats or summary files")
    ap.add_argument("--summary", action="store_true", help="treat input as gfxinfo summary files")
    args = ap.parse_args()

    for path in args.files:
        name = os.path.basename(path)
        if not os.path.exists(path):
            print(f"SKIP {name}: not found")
            continue

        if args.summary:
            s = parse_summary(path)
            if not s:
                print(f"SKIP {name}: no stats found")
                continue
            print(f"==== {name} (gfxinfo summary) ====")
            for key in ("total_frames", "janky", "p50", "p90", "p95", "p99",
                        "missed_vsync", "slow_ui", "slow_bitmap", "slow_draw"):
                if key not in s:
                    continue
                for proc, val in s[key].items():
                    if key == "janky":
                        print(f"  {proc:32s} {key}: {val[0]} frames ({val[1]}%)")
                    else:
                        print(f"  {proc:32s} {key}: {val}")
            continue

        stats = read_framestats(path)
        if stats is None:
            print(f"SKIP {name}: no parsable frame rows (is this a framestats dump?)")
            continue

        t = stats["totals"]
        n = stats["n"]
        print(f"==== {name} ====")
        print(f"  frames: {n}   refresh: {stats['refresh_ms']:.1f}ms")
        print(f"  frame time (completed-start): "
              f"p50={pct(t,50):.1f}ms  p90={pct(t,90):.1f}ms  "
              f"p95={pct(t,95):.1f}ms  p99={pct(t,99):.1f}ms  max={t[-1]/NS_TO_MS:.1f}ms")
        for label, cnt in stats["over"].items():
            print(f"    frames {label}: {cnt} ({cnt / n * 100:.1f}%)")
        if stats["phases"]:
            print("  phase cost (p50 / p95 / max ms):")
            for phase, v in stats["phases"].items():
                print(f"    {phase:18s} {v['p50']:7.2f} / {v['p95']:7.2f} / {v['max']:7.2f}")


if __name__ == "__main__":
    main()
