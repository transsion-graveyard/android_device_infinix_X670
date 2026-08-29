#!/usr/bin/env python3
"""Summarize sf_prop_bench.sh results. Drops cold runs (frames < 500)
and reports warm-only medians per config label.

Usage: summarize.py <results.txt> [<results2.txt> ...]
"""
import re, sys, statistics

RX = re.compile(r'\[([\w-]+)-(\d+)\] frames=(\d+) jank=([\d.]+)% p99=([\d.]+)ms vsync_miss=(\d+)')

def main(paths):
    groups = {}
    for path in paths:
        with open(path) as f:
            for ln in f:
                m = RX.search(ln)
                if not m: continue
                lbl, run, fr, jk, p, vm = m.groups()
                fr = int(fr)
                if fr < 500: continue  # cold-start discard
                groups.setdefault(lbl, []).append((float(jk), float(p), int(vm), fr))
    if not groups:
        print("no warm runs found"); return
    print(f"{'label':30s} {'n':>2s}  {'jank%':>7s}  {'p99ms':>6s}  {'miss':>4s}  {'frames':>7s}")
    for lbl, runs in sorted(groups.items()):
        janks = [r[0] for r in runs]
        p99s  = [r[1] for r in runs]
        miss  = [r[2] for r in runs]
        frms  = [r[3] for r in runs]
        print(f"{lbl:30s} {len(runs):2d}  {statistics.median(janks):7.2f}  {statistics.median(p99s):6.0f}  {statistics.median(miss):4.0f}  {statistics.median(frms):7.0f}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1:])
