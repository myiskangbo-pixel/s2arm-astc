#!/usr/bin/env python3
"""Regression tests for Windows CMake compiler identity detection."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pack"))
import rewriter  # noqa: E402


class CMakeCompilerMetadataTests(unittest.TestCase):
    def write_config(self, root, c_id="Clang", c_front="MSVC",
                     cxx_id="Clang", cxx_front="MSVC"):
        root.mkdir(parents=True, exist_ok=True)
        (root / "CMakeCache.txt").write_text(
            "CMAKE_GENERATOR:INTERNAL=Ninja\n", encoding="utf-8"
        )
        metadata = root / "CMakeFiles" / "3.31.6"
        metadata.mkdir(parents=True, exist_ok=True)
        (metadata / "CMakeCCompiler.cmake").write_text(
            f'set(CMAKE_C_COMPILER_ID "{c_id}")\n'
            f'set(CMAKE_C_COMPILER_FRONTEND_VARIANT "{c_front}")\n',
            encoding="utf-8",
        )
        (metadata / "CMakeCXXCompiler.cmake").write_text(
            f'set(CMAKE_CXX_COMPILER_ID "{cxx_id}")\n'
            f'set(CMAKE_CXX_COMPILER_FRONTEND_VARIANT "{cxx_front}")\n',
            encoding="utf-8",
        )

    def test_reads_clang_cl_identity_from_generated_files(self):
        with tempfile.TemporaryDirectory() as temp:
            build = Path(temp)
            self.write_config(build)
            cache = (build / "CMakeCache.txt").read_text(encoding="utf-8")
            self.assertNotIn("CMAKE_C_COMPILER_ID", cache)
            self.assertNotIn("CMAKE_CXX_COMPILER_ID", cache)
            self.assertEqual(
                rewriter.validate_windows_cmake(build),
                ("Clang", "MSVC", "Clang", "MSVC"),
            )

    def test_accepts_gnu_frontend(self):
        with tempfile.TemporaryDirectory() as temp:
            build = Path(temp)
            self.write_config(build, "GNU", "GNU", "GNU", "GNU")
            self.assertEqual(
                rewriter.validate_windows_cmake(build),
                ("GNU", "GNU", "GNU", "GNU"),
            )

    def test_rejects_mixed_frontends(self):
        with tempfile.TemporaryDirectory() as temp:
            build = Path(temp)
            self.write_config(build, cxx_front="GNU")
            with self.assertRaisesRegex(ValueError, "前端不一致"):
                rewriter.validate_windows_cmake(build)

    def test_rejects_msvc_compiler_id(self):
        with tempfile.TemporaryDirectory() as temp:
            build = Path(temp)
            self.write_config(build, "MSVC", "MSVC", "MSVC", "MSVC")
            with self.assertRaisesRegex(ValueError, "Clang/GNU"):
                rewriter.validate_windows_cmake(build)

    def test_rejects_missing_cxx_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            build = Path(temp)
            self.write_config(build)
            (build / "CMakeFiles" / "3.31.6" / "CMakeCXXCompiler.cmake").unlink()
            with self.assertRaisesRegex(ValueError, "CXX 编译器元数据"):
                rewriter.validate_windows_cmake(build)


if __name__ == "__main__":
    unittest.main(verbosity=2)
