#!/usr/bin/env python3
"""Static guard for the intended first-party dependency direction.

This is deliberately simple and should complement (not replace) Gradle dependency checks/tests.
"""
from pathlib import Path
import re, sys

ROOT = Path(__file__).resolve().parents[1]
checks = [
    (ROOT / "samcnpc-core", ("samcnpc.behavior", "samcnpc.llm", "samcnpc_behavior", "samcnpc_llm")),
    (ROOT / "samcnpc-behavior", ("samcnpc.llm", "samcnpc_llm",)),
]
violations = []
for base, forbidden in checks:
    if not base.exists():
        continue
    for p in base.rglob("*.kt"):
        text = p.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not (stripped.startswith("import ") or stripped.startswith("package ")):
                continue
            for token in forbidden:
                if token in stripped:
                    violations.append(f"{p.relative_to(ROOT)}:{line_no}: forbidden dependency token {token!r}: {stripped}")

# Behavior may consume only Core's deliberately bounded API package. Reaching into the entity,
# inventory/menu, client renderer, or command implementation would bypass the Core boundary.
behavior_root = ROOT / "samcnpc-behavior"
for p in behavior_root.rglob("*.kt"):
    for line_no, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        stripped = line.strip()
        if not stripped.startswith("import io.samcnpc.core."):
            continue
        if not stripped.startswith("import io.samcnpc.core.api."):
            violations.append(
                f"{p.relative_to(ROOT)}:{line_no}: behavior must import Core through io.samcnpc.core.api only: {stripped}"
            )

if violations:
    print("Boundary violations:")
    print("\n".join(" - " + v for v in violations))
    sys.exit(1)
print("OK: no forbidden source-level module dependency direction detected.")
