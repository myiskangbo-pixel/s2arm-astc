#!/bin/bash
# 门禁覆盖：pack/rewriter.py
# CMake 编译器元数据回归测试（Windows clang-cl / MSVC frontend）：bash tests/rewriter_cmake_metadata_test.sh
set -euo pipefail
H=$(cd "$(dirname "$0")/.." && pwd)
PY=${S2A_PY:-python3}
"$PY" "$H/tests/rewriter_cmake_metadata_test.py"
