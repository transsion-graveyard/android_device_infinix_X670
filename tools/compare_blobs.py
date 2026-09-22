# /// script
# requires-python = ">=3.9"
# ///
"""Compare proprietary-files.txt (extract_utils manifest) against a stock dump listing.

Matching cascade (first hit wins, result tagged with the rule that fired):
  exact       literal path present in the dump
  soc         SoC-named dir dropped (mt6781/x.so -> x.so) or @-tokens
              normalized: mt6781/mt6768 -> mt****
  version     @4.1 / @2.X / @6.0 version tokens normalized to @*
  legacy      system/x -> system/system/x (system-as-root dump layout);
              fixed as src:dst so extract_utils installs the flat path
  basename    token-sorted basename with -vNN suffixes stripped, same dir
  ambiguous   >1 dump candidate at a fuzzy level (listed, never auto-fixed)
  missing     difflib closest-candidate suggestions (report only)

Additionally scans dst / SYMLINK= install names for SoC tokens that don't
match the device (derived from dump lib/hw paths); --fix rewrites those too.

--fix rewrites SRC paths of fixable matches to the exact dump path (backup
written first). Comments, flags, ordering preserved; aliasing rewrites print
a warning with both line numbers.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

VERSION_RE = re.compile(r"@\d[\w.]*")
SOC_RE = re.compile(r"mt\d{4}", re.IGNORECASE)
VTOKEN_SUFFIX_RE = re.compile(r"-v\d+$")
FLAG_RE = re.compile(r";.*$", re.DOTALL)
RULES = ("version", "soc", "legacy", "basename")

FIXABLE_RULES = {"version", "soc", "legacy", "basename"}


@dataclass
class Entry:
    lineno: int
    raw: str
    src: str
    dst: str | None
    flags: str


@dataclass
class Match:
    rule: str  # exact | legacy | version | soc | basename | ambiguous | missing
    dump_path: str | None
    suggestions: list[str] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)


@dataclass
class Manifest:
    lines: list[str]
    entries: list[Entry]
    duplicates: dict[str, list[int]] = field(default_factory=dict)
    disabled: list[int] = field(default_factory=list)
    comments: int = 0
    blanks: int = 0


# --- parsing ---------------------------------------------------------------

def parse_manifest(path: Path) -> Manifest:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    entries: list[Entry] = []
    seen: dict[str, int] = {}
    duplicates: dict[str, list[int]] = {}
    disabled: list[int] = []
    comments = blanks = 0
    for i, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if not stripped:
            blanks += 1
            continue
        if stripped.startswith("#"):
            comments += 1
            if stripped.startswith("#-"):
                disabled.append(i)
            continue
        body = FLAG_RE.sub("", stripped)
        flags = stripped[len(body):]
        if ":" in body:
            src, dst = body.split(":", 1)
        else:
            src, dst = body, None
        src = src.strip()
        if src in seen:
            duplicates.setdefault(src, [seen[src]]).append(i)
            continue
        seen[src] = i
        entries.append(Entry(i, raw.rstrip("\n"), src, dst, flags))
    return Manifest(lines, entries, duplicates, disabled, comments, blanks)


def load_dump(path: Path) -> set[str]:
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


# --- normalizers (pure) ----------------------------------------------------

def norm_versions(path: str) -> str:
    return VERSION_RE.sub("@*", path)


def norm_soc(path: str) -> str:
    return SOC_RE.sub("mt****", path)


def partition_variants(path: str) -> list[str]:
    """Manifest 'system/x' also exists as dump 'system/system/x' (and back)."""
    if path.startswith("system/system/"):
        return [path, path[len("system/system/"):]]
    if path.startswith("system/"):
        return [path, "system/" + path]
    return [path]


def canonical_system(path: str) -> str:
    """Collapse dump's system-as-root nesting: 'system/system/x' -> 'system/x'."""
    if path.startswith("system/system/"):
        return "system/" + path[len("system/system/"):]
    return path


def basename_key(path: str) -> str:
    return VTOKEN_SUFFIX_RE.sub("", os.path.basename(path))


def basename_tokens(path: str) -> tuple[str, ...] | None:
    """Sorted token multiset of the basename; None if too ambiguous to match."""
    stem = basename_key(path)
    tokens = [t for t in re.split(r"[._-]", stem) if t]
    if len(tokens) < 2:
        return None
    return tuple(sorted(tokens))


def basename_index_key(version_soc_path: str) -> str | None:
    """(dirname, sorted-basename-tokens) key; None when tokens are ambiguous."""
    tokens = basename_tokens(version_soc_path)
    if tokens is None:
        return None
    dirname = version_soc_path.rpartition("/")[0]
    return dirname + "|" + "+".join(tokens)


# --- match cascade ---------------------------------------------------------

SOC_DIR_RE = re.compile(r"(?i)(?<=/)mt\d{4}/")


def soc_dir_variants(path: str) -> list[str]:
    """Paths formed by deleting one SoC-named directory component
    (vendor/lib64/mt6781/x.so -> vendor/lib64/x.so)."""
    return [path[: m.start()] + path[m.end():] for m in SOC_DIR_RE.finditer(path)]


def match_entry(src: str, dump: set[str], indexes: dict, suggestions_pool: list[str]) -> Match:
    # level 0: literal path, with system-as-root variants
    for v in partition_variants(src):
        if v in dump:
            rule = "exact" if v == src else "legacy"
            return Match(rule, v)

    # level 0.5: SoC-named directory component dropped, literal dump hit
    for alt in soc_dir_variants(src):
        if alt in dump:
            return Match("soc", alt)

    csrc = canonical_system(src)

    # level 1: version-normalized (system wrapper collapsed)
    nv = norm_versions(csrc)
    hits = indexes["version"].get(nv) or []
    if len(hits) == 1:
        return Match("version", hits[0])
    if hits:
        return Match("ambiguous", None, candidates=sorted(hits))

    # level 2: version + soc-normalized
    nvs = norm_soc(nv)
    hits = indexes["soc"].get(nvs) or []
    if len(hits) == 1:
        return Match("soc", hits[0])
    if hits:
        return Match("ambiguous", None, candidates=sorted(hits))

    # level 3: same directory + token-sorted basename (suffix-stripped)
    bkey = basename_index_key(nvs)
    if bkey is not None:
        hits = indexes["basename"].get(bkey) or []
        if len(hits) == 1:
            return Match("basename", hits[0])
        if hits:
            return Match("ambiguous", None, candidates=sorted(hits))

    # missing: difflib suggestions (report-only, never auto-fixed)
    pool_key = norm_soc(norm_versions(csrc))
    close = difflib.get_close_matches(pool_key, suggestions_pool, n=3, cutoff=0.75)
    return Match("missing", None, suggestions=[indexes["reverse"][c] for c in close])


def build_indexes(dump: set[str]) -> dict:
    version: dict[str, list[str]] = {}
    soc: dict[str, list[str]] = {}
    basename: dict[str, list[str]] = {}
    reverse: dict[str, str] = {}
    for p in dump:
        cp = canonical_system(p)
        nv = norm_versions(cp)
        version.setdefault(nv, []).append(p)
        nvs = norm_soc(nv)
        soc.setdefault(nvs, []).append(p)
        bkey = basename_index_key(nvs)
        if bkey is not None:
            basename.setdefault(bkey, []).append(p)
        reverse.setdefault(norm_soc(nv), p)
    return {
        "version": version,
        "soc": soc,
        "basename": basename,
        "reverse": reverse,
        "suggestions_pool": list(reverse),
    }


# --- reporting -------------------------------------------------------------

def run_compare(manifest: Manifest, dump: set[str]) -> list[tuple[Entry, Match]]:
    indexes = build_indexes(dump)
    # share the suggestion pool across entries via closure-free call
    results = []
    for entry in manifest.entries:
        results.append((entry, match_entry_shim(entry.src, dump, indexes)))
    return results


def match_entry_shim(src: str, dump: set[str], indexes: dict) -> Match:
    return match_entry(src, dump, indexes, indexes["suggestions_pool"])


def build_report(manifest: Manifest, results: list[tuple[Entry, Match]]) -> dict:
    exact = [(e, m) for e, m in results if m.rule == "exact"]
    equivalent = [(e, m) for e, m in results if m.rule in FIXABLE_RULES]
    ambiguous = [(e, m) for e, m in results if m.rule == "ambiguous"]
    missing = [(e, m) for e, m in results if m.rule == "missing"]
    return {
        "exact": [{"src": e.src} for e, _ in exact],
        "equivalent": [
            {"src": e.src, "rule": m.rule, "dump_path": m.dump_path} for e, m in equivalent
        ],
        "ambiguous": [
            {"src": e.src, "lineno": e.lineno, "candidates": m.candidates}
            for e, m in ambiguous
        ],
        "missing": [
            {"src": e.src, "lineno": e.lineno, "suggestions": m.suggestions}
            for e, m in missing
        ],
        "duplicates": dict(manifest.duplicates),
        "disabled_lines": manifest.disabled,
        "counts": {
            "entries": len(manifest.entries),
            "exact": len(exact),
            "equivalent": len(equivalent),
            "ambiguous": len(ambiguous),
            "missing": len(missing),
        },
    }


def print_report(manifest: Manifest, report: dict, out=sys.stdout) -> None:
    equivalent = report["equivalent"]
    ambiguous = report["ambiguous"]
    missing = report["missing"]
    w = max((len(e["src"]) for e in equivalent), default=0)
    print(f"EXACT     : {report['counts']['exact']}", file=out)
    print(f"EQUIVALENT: {report['counts']['equivalent']}", file=out)
    for e in equivalent:
        print(f"  [{e['rule']:<8}] {e['src']:<{w}}  ->  {e['dump_path']}", file=out)
    print(
        f"INSTALL-NAME: {report['counts']['install_name']}  "
        f"(dst/symlink soc token != {report.get('device_soc')}; install names, not dump paths)",
        file=out,
    )
    for e in report["install_names"]:
        for ch in e["changes"]:
            print(f"  line {e['lineno']}  {ch['field']}: {ch['old']}  ->  {ch['new']}", file=out)
    print(f"AMBIGUOUS : {report['counts']['ambiguous']}  (multiple dump candidates; never auto-fixed)", file=out)
    for e in ambiguous:
        print(f"  {e['src']}", file=out)
        for c in e["candidates"]:
            print(f"      candidate: {c}", file=out)
    print(f"MISSING   : {report['counts']['missing']}", file=out)
    for e in missing:
        print(f"  {e['src']}", file=out)
        for s in e["suggestions"]:
            print(f"      closest: {s}", file=out)
    if manifest.duplicates:
        print(f"DUPLICATES: {len(manifest.duplicates)}", file=out)
        for src, linenos in manifest.duplicates.items():
            print(f"  {src} (lines {', '.join(map(str, linenos))})", file=out)
    if manifest.disabled:
        print(f"disabled  : {len(manifest.disabled)} (lines {', '.join(map(str, manifest.disabled))})", file=out)
    c = report["counts"]
    print(
        f"\nsummary: {c['entries']} unique entries | {c['exact']} exact | "
        f"{c['equivalent']} equivalent | {c['install_name']} install-name | "
        f"{c['ambiguous']} ambiguous | {c['missing']} missing",
        file=out,
    )


# --- fix mode --------------------------------------------------------------

def detect_device_soc(dump: set[str]) -> str | None:
    """Device SoC codename = unique mt#### token under a lib hw/ directory."""
    tokens = {m.group(0).lower() for p in dump if "/hw/" in p for m in SOC_RE.finditer(p)}
    return tokens.pop() if len(tokens) == 1 else None


def scan_install_names(
    manifest: Manifest, device_soc: str | None
) -> dict[int, list[tuple[str, str, str]]]:
    """lineno -> [(field, old_token, new_token)] for dst / SYMLINK= soc tokens
    that don't match the device (install names, not dump paths)."""
    soc_tok = re.compile(r"(?i)mt\d{4}")
    found: dict[int, list[tuple[str, str, str]]] = {}
    if not device_soc:
        return found
    for e in manifest.entries:
        changes: list[tuple[str, str, str]] = []
        fields: list[tuple[str, str]] = []
        if e.dst:
            fields.append(("dst", e.dst))
        symlink = re.search(r";SYMLINK=([^\s;]+)", e.flags)
        if symlink:
            fields.append(("symlink", symlink.group(1)))
        for field, value in fields:
            for m in soc_tok.finditer(value):
                if m.group(0).lower() != device_soc:
                    changes.append((field, m.group(0), device_soc))
        if changes:
            found[e.lineno] = changes
    return found


def collect_src_fixes(manifest: Manifest, results: list[tuple[Entry, Match]]) -> dict[int, str]:
    src_lines: dict[str, list[int]] = {}
    for e in manifest.entries:
        src_lines.setdefault(e.src, []).append(e.lineno)

    replacements: dict[int, str] = {}
    for entry, match in results:
        if match.rule not in FIXABLE_RULES or not match.dump_path:
            continue
        if match.dump_path == entry.src:
            continue

        flags = entry.flags
        # a SYMLINK= whose target equals the new src is a self-link: drop it
        symlink = re.search(r";SYMLINK=([^\s;]+)", flags)
        if symlink and symlink.group(1) == match.dump_path:
            flags = flags.replace(symlink.group(0), "")

        if match.rule == "legacy":
            # install path differs from dump path (system-as-root nesting):
            # must emit src:dst or extract_utils installs the nested path
            dst = entry.dst if entry.dst else entry.src
            new_body = f"{match.dump_path}:{dst}{flags}"
        else:
            new_body = match.dump_path + (f":{entry.dst}" if entry.dst else "") + flags

        if match.dump_path in src_lines and match.dump_path != entry.src:
            other = [n for n in src_lines[match.dump_path] if n != entry.lineno]
            if other:
                print(
                    f"warning: line {entry.lineno} now aliases existing "
                    f"line(s) {', '.join(map(str, other))}: {match.dump_path}"
                )
        replacements[entry.lineno] = new_body
    return replacements


def apply_fixes(
    manifest_path: Path,
    manifest: Manifest,
    results: list[tuple[Entry, Match]],
    device_soc: str | None,
) -> int:
    replacements = collect_src_fixes(manifest, results)
    by_lineno = {e.lineno: e for e in manifest.entries}
    soc_tok = re.compile(r"(?i)mt\d{4}")

    for lineno, changes in scan_install_names(manifest, device_soc).items():
        if lineno in replacements:
            print(f"warning: line {lineno} has both src and install-name fixes; review manually")
            continue
        entry = by_lineno[lineno]
        new_dst, new_flags = entry.dst, entry.flags
        if any(f == "dst" for f, _, _ in changes) and new_dst is not None:
            new_dst = soc_tok.sub(
                lambda m: m.group(0) if m.group(0).lower() == device_soc else device_soc,
                new_dst,
            )
        if any(f == "symlink" for f, _, _ in changes):
            new_flags = soc_tok.sub(
                lambda m: m.group(0) if m.group(0).lower() == device_soc else device_soc,
                new_flags,
            )
        replacements[lineno] = entry.src + (f":{new_dst}" if new_dst else "") + new_flags

    if not replacements:
        print("nothing to fix")
        return 0

    backup = manifest_path.with_suffix(manifest_path.suffix + ".bak")
    if backup.exists():
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = manifest_path.with_suffix(f"{manifest_path.suffix}.bak.{stamp}")
    shutil.copy2(manifest_path, backup)

    lines = manifest.lines
    for lineno, new_body in replacements.items():
        idx = lineno - 1
        original = lines[idx]
        ending = ""
        for eol in ("\r\n", "\n", "\r"):
            if original.endswith(eol):
                ending = eol
                break
        lines[idx] = new_body + ending
    manifest_path.write_text("".join(lines), encoding="utf-8")
    print(f"fixed {len(replacements)} entries; backup: {backup}")
    return len(replacements)


# --- cli -------------------------------------------------------------------

def default_paths() -> tuple[Path, Path]:
    repo = Path(__file__).resolve().parent.parent
    manifest = repo / "proprietary-files.txt"
    dump = repo.parent / "Infinix-Hot-11S-NFC-X6812B-30" / "all_files.txt"
    return manifest, dump


def main(argv: list[str] | None = None) -> int:
    def_manifest, def_dump = default_paths()
    ap = argparse.ArgumentParser(
        description="Compare proprietary-files.txt against a stock dump file listing."
    )
    ap.add_argument("--list", type=Path, default=def_manifest, help="manifest path")
    ap.add_argument("--dump", type=Path, default=def_dump, help="dump listing path (all_files.txt)")
    ap.add_argument("--fix", action="store_true", help="rewrite fuzzy-matched SRC paths to dump paths (backup first)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON report")
    args = ap.parse_args(argv)

    for p in (args.list, args.dump):
        if not p.is_file():
            ap.error(f"file not found: {p}")

    manifest = parse_manifest(args.list)
    dump = load_dump(args.dump)
    device_soc = detect_device_soc(dump)
    results = run_compare(manifest, dump)
    report = build_report(manifest, results)
    install_names = [
        {
            "lineno": n,
            "src": by_src.src,
            "changes": [
                {"field": f, "old": o, "new": w} for f, o, w in changes
            ],
        }
        for n, changes in scan_install_names(manifest, device_soc).items()
        for by_src in [next(e for e in manifest.entries if e.lineno == n)]
    ]
    report["device_soc"] = device_soc
    report["install_names"] = install_names
    report["counts"]["install_name"] = len(install_names)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(manifest, report)

    if args.fix:
        apply_fixes(args.list, manifest, results, device_soc)

    c = report["counts"]
    unresolved = c["missing"] + c["ambiguous"] + c["equivalent"] + c["install_name"]
    return 1 if unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
