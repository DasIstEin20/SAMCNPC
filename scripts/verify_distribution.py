#!/usr/bin/env python3
"""Verify the three named SAMCNPC mod artifacts and their Java 17 class headers."""
from pathlib import Path
import re
import sys
from zipfile import BadZipFile, ZipFile

MODULES = ("samcnpc-core", "samcnpc-behavior", "samcnpc-llm")
DOCUMENTATION_JAR = re.compile(r"-(sources|javadoc)\.jar$")


def inspect_distribution(root: Path, version: str) -> tuple[list[Path], list[str]]:
    artifacts: list[Path] = []
    problems: list[str] = []
    for module in MODULES:
        directory = root / module / "build" / "libs"
        jars = sorted(path for path in directory.glob("*.jar") if not DOCUMENTATION_JAR.search(path.name))
        if len(jars) != 1:
            names = ", ".join(path.name for path in jars) or "(none)"
            problems.append(f"{module}: expected exactly one final mod JAR, found {len(jars)}: {names}")
            continue
        jar = jars[0]
        expected = f"{module}-{version}.jar"
        if jar.name != expected:
            problems.append(f"{module}: expected {expected}, found {jar.name}")
            continue
        artifacts.append(jar)
        prefix = "io/samcnpc/" + module.removeprefix("samcnpc-") + "/"
        try:
            with ZipFile(jar) as archive:
                names = archive.namelist()
                if "META-INF/mods.toml" not in names:
                    problems.append(f"{module}: missing Forge mod metadata")
                classes = [name for name in names if name.startswith(prefix) and name.endswith(".class")]
                if not classes:
                    problems.append(f"{module}: no first-party compiled classes")
                for name in classes:
                    with archive.open(name) as source:
                        header = source.read(8)
                    if len(header) != 8 or header[:4] != b"\xca\xfe\xba\xbe":
                        problems.append(f"{module}: invalid class header in {name}")
                    elif int.from_bytes(header[6:8], "big") != 61:
                        problems.append(f"{module}: {name} must target Java 17 (class version 61)")
        except (BadZipFile, OSError) as error:
            problems.append(f"{module}: cannot inspect {jar.name}: {error}")
    return artifacts, problems


def read_version(root: Path) -> str:
    for line in (root / "gradle.properties").read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == "mod_version" and value.strip():
            return value.strip()
    raise ValueError("gradle.properties must specify mod_version")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        version = read_version(root)
    except (OSError, ValueError) as error:
        print(f"Distribution check failed: {error}")
        return 1
    artifacts, problems = inspect_distribution(root, version)
    if problems:
        print("Distribution check failed:")
        for problem in problems:
            print(" -", problem)
        return 1
    print("Verified exactly three named SAMCNPC mod JARs with Java 17 classes:")
    for artifact in artifacts:
        print(" -", artifact.relative_to(root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
