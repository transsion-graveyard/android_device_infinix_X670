#!/usr/bin/env python3

import argparse
from collections import defaultdict
from pathlib import Path


ALIAS_PREFIXES = [
    ("system/", "system/system/"),
    ("system/system/", "system/"),
    ("system_ext/", "system/system_ext/"),
    ("system/system_ext/", "system_ext/"),
    ("product/", "system/product/"),
    ("system/product/", "product/"),
]


def read_all_paths(path):
    paths = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line and not line.startswith("#"):
                paths.append(line)
    return paths


def parse_line(raw):
    line = raw.rstrip("\n")
    newline = raw[len(line) :]
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return {"active": False, "raw": raw}

    leading = line[: len(line) - len(line.lstrip())]
    core = stripped
    disabled = core.startswith("-")
    if disabled:
        core = core[1:].strip()

    flags = ""
    if ";" in core:
        core, rest = core.split(";", 1)
        core = core.strip()
        flags = ";" + rest

    src, dest = None, core
    if ":" in core:
        left, right = core.split(":", 1)
        src = left.strip() or None
        dest = right.strip() or left.strip()

    return {
        "active": True,
        "raw": raw,
        "newline": newline,
        "leading": leading,
        "disabled": disabled,
        "src": src,
        "dest": dest,
        "flags": flags,
    }


def rebuild(entry, new_dest=None, normalize_disabled_remap=True):
    dest = new_dest if new_dest is not None else entry["dest"]
    left = ""
    if entry["src"] and not (normalize_disabled_remap and entry["disabled"]):
        left = entry["src"] + ":"
    prefix = "-" if entry["disabled"] else ""
    return f"{entry['leading']}{prefix}{left}{dest}{entry['flags']}{entry['newline']}"


def aliases(path):
    out = [path]
    for left, right in ALIAS_PREFIXES:
        if path.startswith(left):
            alt = right + path[len(left) :]
            if alt not in out:
                out.append(alt)
    return out


def exists_with_alias(path, all_set):
    for c in aliases(path):
        if c in all_set:
            return True
    return False


def choose_candidate(candidates):
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    lib64 = [c for c in candidates if "/lib64/" in f"/{c}"]
    if len(lib64) == 1:
        return lib64[0]
    return None


def process(all_files, proprietary, out_path):
    all_paths = read_all_paths(all_files)
    all_set = set(all_paths)
    by_name = defaultdict(list)
    for p in all_paths:
        by_name[p.rsplit("/", 1)[-1]].append(p)

    with open(proprietary, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out = []
    stats = {
        "total": len(lines),
        "kept": 0,
        "moved": 0,
        "dropped": 0,
        "ambiguous_kept": 0,
        "disabled_normalized": 0,
    }

    for raw in lines:
        entry = parse_line(raw)
        if not entry["active"]:
            out.append(raw)
            continue

        if entry["disabled"] and entry["src"]:
            stats["disabled_normalized"] += 1

        if exists_with_alias(entry["dest"], all_set):
            out.append(rebuild(entry))
            stats["kept"] += 1
            continue

        if entry["src"] and exists_with_alias(entry["src"], all_set):
            out.append(rebuild(entry))
            stats["kept"] += 1
            continue

        if entry["disabled"]:
            out.append(rebuild(entry))
            stats["kept"] += 1
            continue

        candidates = sorted(by_name.get(entry["dest"].rsplit("/", 1)[-1], []))
        chosen = choose_candidate(candidates)

        if chosen:
            out.append(rebuild(entry, new_dest=chosen))
            stats["moved"] += 1
        elif candidates:
            out.append(rebuild(entry))
            stats["ambiguous_kept"] += 1
        else:
            stats["dropped"] += 1

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(out)

    print("done")
    print(f"input:  {proprietary}")
    print(f"output: {out_path}")
    print(
        f"moved: {stats['moved']}, dropped: {stats['dropped']}, ambiguous-kept: {stats['ambiguous_kept']}"
    )
    print(f"kept: {stats['kept']}, disabled-normalized: {stats['disabled_normalized']}")


def detect_input_file(explicit, preferred_names, glob_patterns, label):
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise SystemExit(f"{label} not found: {explicit}")
        return str(path)

    for name in preferred_names:
        path = Path(name)
        if path.is_file():
            return str(path)

    matches = []
    seen = set()
    for pattern in glob_patterns:
        for match in sorted(Path(".").glob(pattern)):
            key = str(match)
            if match.is_file() and key not in seen:
                seen.add(key)
                matches.append(key)

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise SystemExit(
            f"Multiple {label} candidates found: {', '.join(matches)}. Use --{label}."
        )

    raise SystemExit(f"Could not auto-detect {label}. Use --{label}.")


def main():
    p = argparse.ArgumentParser(
        description="Trim proprietary-files using all_files (auto-move, drop missing, prefer lib64)."
    )
    p.add_argument("--all-files", default="")
    p.add_argument("--proprietary", default="")
    p.add_argument("--out", default="proprietary-files.trimmed.txt")
    p.add_argument("--in-place", action="store_true")
    a = p.parse_args()

    all_files = detect_input_file(
        explicit=a.all_files,
        preferred_names=["all_files.txt", "all-files.txt"],
        glob_patterns=["*all_files*.txt", "*all-files*.txt"],
        label="all-files",
    )
    proprietary = detect_input_file(
        explicit=a.proprietary,
        preferred_names=["proprietary-files.txt"],
        glob_patterns=["proprietary-files*.txt"],
        label="proprietary",
    )

    out_path = proprietary if a.in_place else a.out
    process(all_files, proprietary, out_path)


if __name__ == "__main__":
    main()
