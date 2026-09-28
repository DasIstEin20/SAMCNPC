"""Regression cases for the first-party artifact acceptance gate."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from verify_distribution import MODULES, inspect_distribution


class DistributionTest(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory(prefix="samcnpc-distribution-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for module in MODULES:
            self.write_mod(module)

    def write_mod(self, module, suffix="", major=61, metadata=True):
        path = self.root / module / "build" / "libs" / f"{module}-0.1.0{suffix}.jar"
        path.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(path, "w") as archive:
            if metadata:
                archive.writestr("META-INF/mods.toml", "modLoader=\"kotlinforforge\"")
            name = "io/samcnpc/" + module.removeprefix("samcnpc-") + "/Example.class"
            archive.writestr(name, b"\xca\xfe\xba\xbe\x00\x00" + major.to_bytes(2, "big"))
        return path

    def test_three_final_mods_pass(self):
        artifacts, problems = inspect_distribution(self.root, "0.1.0")
        self.assertEqual(3, len(artifacts))
        self.assertEqual([], problems)

    def test_additional_first_party_jar_fails(self):
        self.write_mod("samcnpc-core", "-extra")
        _, problems = inspect_distribution(self.root, "0.1.0")
        self.assertTrue(any("exactly one" in problem and "samcnpc-core" in problem for problem in problems))

    def test_missing_module_fails(self):
        path = self.root / "samcnpc-llm/build/libs/samcnpc-llm-0.1.0.jar"
        path.unlink()
        _, problems = inspect_distribution(self.root, "0.1.0")
        self.assertTrue(any("samcnpc-llm" in problem for problem in problems))

    def test_old_version_is_not_accepted_as_current(self):
        _, problems = inspect_distribution(self.root, "0.2.0")
        self.assertEqual(3, len(problems))
        self.assertTrue(all("expected" in problem for problem in problems))

    def test_documentation_archives_are_not_runtime_mods(self):
        directory = self.root / "samcnpc-core/build/libs"
        for classifier in ("sources", "javadoc"):
            with ZipFile(directory / f"samcnpc-core-0.1.0-{classifier}.jar", "w"):
                pass
        artifacts, problems = inspect_distribution(self.root, "0.1.0")
        self.assertEqual(3, len(artifacts))
        self.assertEqual([], problems)

    def test_java_21_bytecode_is_rejected(self):
        self.write_mod("samcnpc-behavior", major=65)
        _, problems = inspect_distribution(self.root, "0.1.0")
        self.assertTrue(any("Java 17" in problem for problem in problems))

    def test_missing_forge_metadata_is_rejected(self):
        self.write_mod("samcnpc-llm", metadata=False)
        _, problems = inspect_distribution(self.root, "0.1.0")
        self.assertTrue(any("Forge mod metadata" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main()
