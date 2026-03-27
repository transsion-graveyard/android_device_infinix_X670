#!/usr/bin/env python3
import subprocess
import re
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ALL_FILES = os.path.join(SCRIPT_DIR, "all_files.txt")
PROP_FILES = os.path.join(SCRIPT_DIR, "proprietary-files.txt")
DUMP_DIR = os.path.expanduser("~/dump")

LINEAGE_ROOT = "/home/ikan/axion"


def run_build():
    cmd = f"bash -c 'cd {LINEAGE_ROOT} && source build/envsetup.sh && lunch lineage_X670-bp1a-userdebug >/dev/null 2>&1 && m nothing 2>&1'"
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=LINEAGE_ROOT,
    )
    output_lines = []
    for line in iter(proc.stdout.readline, ""):
        if line:
            print(line, end="")
            output_lines.append(line)
    proc.wait()
    return "".join(output_lines), proc.returncode


def parse_missing_modules(output):
    pattern = r'depends on undefined module "([^"]+)"'
    return set(re.findall(pattern, output))


def get_all_files_paths():
    with open(ALL_FILES) as f:
        return set(line.strip() for line in f if line.strip().endswith(".so"))


def check_in_all_files(module_name, all_paths):
    file_name = module_name + ".so"
    candidates = [f"vendor/lib64/{file_name}", f"vendor/lib/{file_name}"]
    for path in candidates:
        if path in all_paths:
            return path
    return None


def add_missing_blobs(missing_modules, all_paths):
    added = []
    for mod in missing_modules:
        path = check_in_all_files(mod, all_paths)
        if path:
            added.append(path)
    return added


def update_proprietary_files(new_blobs):
    if not new_blobs:
        return False

    with open(PROP_FILES) as f:
        lines = f.readlines()

    lib64_blobs = sorted([b for b in new_blobs if "/lib64/" in b])
    lib_blobs = sorted([b for b in new_blobs if "/lib/" in b and "/lib64/" not in b])

    insert_idx = None
    for i, line in enumerate(lines):
        if "# Camera Configurations" in line:
            insert_idx = i
            break

    if insert_idx is None:
        print("Could not find insertion point!")
        return False

    new_section = ["\n# Camera IdxMgr\n"]
    if lib64_blobs:
        new_section.extend(f"{b}\n" for b in lib64_blobs)
    if lib_blobs:
        new_section.extend(f"{b}\n" for b in lib_blobs)

    lines = lines[:insert_idx] + new_section + lines[insert_idx:]

    with open(PROP_FILES, "w") as f:
        f.writelines(lines)

    return True


def run_extraction():
    extract_py = os.path.join(SCRIPT_DIR, "extract-files.py")
    setup_py = os.path.join(SCRIPT_DIR, "setup-makefiles.py")

    if os.path.exists(extract_py):
        print("Running extract-files.py...")
        subprocess.run([extract_py, DUMP_DIR], check=False, cwd=SCRIPT_DIR)

    if os.path.exists(setup_py):
        print("Running setup-makefiles.py...")
        subprocess.run([setup_py], check=False, cwd=SCRIPT_DIR)


def main():
    max_iterations = 20
    all_paths = get_all_files_paths()
    print(f"SCRIPT_DIR: {SCRIPT_DIR}")
    print(f"LINEAGE_ROOT: {LINEAGE_ROOT}")
    print(f"Total .so files in all_files.txt: {len(all_paths)}")

    for i in range(max_iterations):
        print(f"\n{'=' * 50}")
        print(f"Iteration {i + 1}/{max_iterations}")
        print("=" * 50)

        output, returncode = run_build()
        missing = parse_missing_modules(output)

        print(f"Build returncode: {returncode}")
        print(f"Output length: {len(output)}")

        if not missing and returncode == 0:
            print("SUCCESS: Build completed with no missing modules!")
            return 0

        print(f"Found {len(missing)} missing modules:")
        for mod in sorted(missing):
            print(f"  - {mod}")

        new_blobs = add_missing_blobs(missing, all_paths)

        if not new_blobs:
            print("ERROR: None of the missing modules found in all_files.txt!")
            return 1

        print(f"Adding {len(new_blobs)} blobs to proprietary-files.txt:")
        for blob in sorted(new_blobs):
            print(f"  + {blob}")

        if not update_proprietary_files(new_blobs):
            return 1

        all_paths = get_all_files_paths()

        print("Regenerating vendor tree...")
        run_extraction()

    print(f"Max iterations ({max_iterations}) reached")
    return 1


if __name__ == "__main__":
    sys.exit(main())
