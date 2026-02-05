import unittest
from pathlib import Path


class RequirementsPlatformMarkersTest(unittest.TestCase):
    def test_pywin32_is_gated_to_windows(self) -> None:
        requirements = Path("requirements.txt").read_text(encoding="utf-8").splitlines()
        pywin32_lines = [line.strip() for line in requirements if line.strip().startswith("pywin32")]

        self.assertTrue(pywin32_lines, "requirements.txt should include pywin32 dependency")
        self.assertEqual(
            len(pywin32_lines),
            1,
            "requirements.txt should include a single pywin32 dependency line",
        )
        self.assertIn(
            ";",
            pywin32_lines[0],
            "pywin32 must be guarded with an environment marker for Windows",
        )
        self.assertIn(
            'platform_system == "Windows"',
            pywin32_lines[0],
            "pywin32 should only install on Windows",
        )


if __name__ == "__main__":
    unittest.main()
