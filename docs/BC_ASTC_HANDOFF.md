# S2Arm BC-ASTC 项目交接日志（新对话入口）

> 最后核验时间：2026-11-24（UTC；以 GitHub API 返回时间为准）
> 用途：新对话开启后先读本文件，再核验 GitHub 最新状态。本文是交接快照，不替代当前源码、Actions 日志和 PR 状态。

## 0. 一句话目标

交付两项互相配套的成果：

1. **Windows x64 S2Arm 完整工具包**：用户在 Windows 上自行导入游戏文件、逆向/改写游戏、构建匹配运行资源，并支持 BC-ASTC 4×4 纹理预处理；交付形式应接近用户提供的现有 S2Arm 文件夹（Engine、Runtime、Shell、Fonts、ThirdParty、S2Arm.exe、s2armctl.cmd、s2armctl.py、version.txt 等），而不是源码压缩包或空目录。
2. **完整 iOS 游戏 IPA**：先处理游戏内容及 BC-ASTC 资源，再构建/取得匹配 iOS Runtime Shell，将游戏映像与资源装入壳，生成可由用户自行签名、侧载的 IPA。

最终链路：
游戏原始文件 → S2Arm 解包/逆向与改写 → BC-ASTC 4×4 资源预处理 → iOS Runtime/Shell + 游戏映像/资源组装 → IPA → 用户签名侧载 → iPhone 实机验收。

## 1. 用户授权与边界

用户明确选择 **B：自主开发模式**，允许在目标完成前：
- 读取仓库、分支、PR、源码、Actions、日志和 artifacts；
- 在工作分支内自主修改源码、测试、CI 和打包脚本；
- 自主提交 commit、运行 targeted tests / CI，并在连续失败后多轮修复；
- 推进 Windows x64 工具包、iOS Runtime/Shell 集成、游戏资源装包及 IPA 构建；
- 维护本交接文档，并在每次有实质进展后更新。

仍需单独确认/不能假称已具备：
- 不更改组织/仓库安全设置、Secrets、权限；
- 不做不可逆删除、force push；
- 不擅自合并 PR、公开发布；
- 不使用或伪造用户的 Apple 签名凭据；
- 不伪造商业游戏输入、真实游戏兼容性、签名或真机安装结果。
若缺少游戏文件、密钥、Apple provisioning/signing 或 iPhone，先完成可复现的工具链和 unsigned package，再明确请求真正不可缺少的输入。

## 2. GitHub 当前现场（本次实际核验）

- Repository：`myiskangbo-pixel/s2arm-astc`
- 工作分支：`fix/bc-astc-shell-inputs`
- 当前 HEAD：`13076da98865a5abddd512b2a79269251c4a2574`
- PR：[#2 fix(pack): register BC ASTC shell inputs](https://github.com/myiskangbo-pixel/s2arm-astc/pull/2)
- PR 状态：open、Draft、未合并；目标分支 `bc-astc-import`
- PR base SHA：`b9c1840178d77a3537c67aaa9f8c98c22eacc64c`
- 本次核验未发现比 `13076da` 更新的该分支提交；不要假定旧对话声称的“正在运行”仍然成立，必须重新查 Actions。

### 最近已知 Actions

**完整贡献者自检**
- Run [45371346488](https://github.com/myiskangbo-pixel/s2arm-astc/actions/runs/45371346488)
- HEAD：`13076da...`
- 结果：failure
- Job：`Contributor self-check (macOS)`，失败步骤为 `Run contributor self-check against PR base`。
- 准备步骤全部通过：Checkout full history、Python 3.12、.NET 10.0.403、Bash 5、Python/rewriter dependencies、Xcode/iOS SDK/Metal prerequisites、synthetic system archive。
- Diagnostics artifact：`contributor-self-check-45371346488`，artifact ID `14909554617`，大小 9,085 bytes，SHA-256 `7d005d7e94788c16043ed02bd34c251c12e94562b0abedc223dc5d23bbbb20b5`，到期时间 2026-12-08T10:29:51Z。
- [Artifacts/API 下载地址](https://api.github.com/repos/myiskangbo-pixel/s2arm-astc/actions/artifacts/14909554617/zip)

自检日志的准确摘要（来自 job 138366113426）：
- Full 档；应跑 125 步，实际执行 125 步；耗时 1,419 秒。
- 116 项绿、4 项红，但只产生 120 条结论；另有 5 项没有有效结论，因此完整性门禁失败。
- 红项：`cores_lanes_test`、`dev_run_test`、`py_undefined_names_test`、Ryujinx 补丁核对。
- 基线复跑摘要：新红 1 项（`dev_run_test`，基线未产生该项结论）；同样红/未证 3 项（`cores_lanes_test`、`py_undefined_names_test`、Ryujinx 补丁核对）。不要把“基线同红”直接写成已证明无影响。
- `cores_lanes_test` 现象：入口进程 nice 预期 10，实际 -10。
- `dev_run_test` 现象：帧号/心跳用例失败，副本停 40 帧而心跳仍增长，窗口读数 95 帧；需追查是否测试时序、心跳语义或真实运行缺陷。
- `py_undefined_names_test`：缺少 Ruff，日志要求 `ruff==0.17.1` 或设置 `S2A_RUFF`。当前 workflow Python setup 之后的依赖安装清单没有明确列入 Ruff。
- Ryujinx 检查：报 `compat/tree` 有改动时必须通过 `compat/patch_new.sh` 生成补丁并在改动清单写明理由。
- `make_tzdata_test`、`public_repo_scan_test`、`shared_matrix_test` 等此前红项在这次 Run 中已绿（make_tzdata 具体日志显示通过）；不要沿用旧失败列表。

**关键源码问题（优先复核）**
- 当前分支 `tools/cores.sh` 的 `s2a_cores()` 行实际内容为：
  `[ "$nv" -gt 0 ] ... && renice "$nv" -p $ > /dev/null 2>&1`
- 这里 `-p $` 看起来是前一轮修改误删了 PID 展开符，预期很可能应为 `-p $$`。这是明确需要先修复/加回归测试的疑点，且与 nice 测试“期望 10、实际 -10”高度相关。先查看 blame/diff 与测试，再作最小修复，不能把它当作基线问题。

**BC ASTC 专项 CI**
- Run [45371346498](https://github.com/myiskangbo-pixel/s2arm-astc/actions/runs/45371346498)
- HEAD：`13076da...`
- 结果：success；两个 job 全通过：
  - Portable BC texture tests：壳输入登记检查、纹理测试构建、BC transcode tests、texture tests 全通过。
  - iOS ARM64 Metal static library：Apple toolchain 检查、iOS NVN library 构建、静态库检查、artifact 上传全通过。
- Artifact 约 5.06 MB；之前记录的 SHA-256（Run 45367755900 产物）为 `065d476d…e1e3118`，不要把旧 Run 的 digest 当成 Run 45371346498 的 digest；需下载当前 run artifact 并核验。
- 这只证明专项测试及静态库构建通过，不证明实际游戏资源闭环、Windows 包、IPA 或真机兼容性。

## 3. 已确认的代码/构建组件（按仓库现有文件说明）

### Windows 工具包构建
- `launchers/windows/bundle_win.py`：完整 Windows 启动器发版目录组装器；文档描述 Engine 快照、Runtime、Shell、可选 Shell-tvOS、Fonts、ThirdParty/Impactor。
- `launchers/windows/bundle_prepare_win.py`：Windows 发版预编件，文档列出 RomFS 索引、dsh_batch、devpush、rcodesign、dsx、nx_unpack、gamedec、codecs、ASTC 等工具。
- `launchers/windows/bundle_runtime_win.py`：Python 3.12 嵌入版、运行时依赖、Git for Windows usr/bin/bash、zstd、licenses、s2arm_env.cmd。
- 这三份脚本真实存在，但**尚无证据证明已成功生成用户要求的 Windows x64 完整目录/ZIP**。bundle_win 文档说明预编 Shell、tzdata、Fonts 目前由 Mac 产出，需先确认可用的构建来源及 shellId/source identity/hash 检查。
- 用户要求的外观参考：现有 S2Arm 目录含 CommunityPatches、Engine、Fonts、Runtime、Shell、Shell-tvOS、skill、ThirdParty、S2Arm.exe、s2armctl.cmd、s2armctl.py、version.txt。最终包需保留对应功能与可执行 launcher，不只是同名空目录。

### BC → ASTC 资源链
- `pack/astc_pack.py`：文档说明从 RomFS / BNTX（可嵌套 BFRES、zstd、Yaz0、SARC）提取 BC 纹理平面，解码并编码 ASTC 4×4，生成带索引只读包。
- 运行时接口说明为 `NXGAL_ASTC_PACK=<包路径>`；包键定义需与 `graphics/metal/gal_astc.h` 保持一致。
- `graphics/tools/astc/bc2astc.c`：BC/块线性处理与 ASTC 编码的 C 工具库。
- `graphics/metal/gal_astc.m`、`graphics/metal/gal_tex.m`：Metal 路径有 ASTC pack 读取/BC→ASTC 存储逻辑。
- `launchers/windows/bundle_prepare_win.py` 当前文档把 `libbc2astc-<hash>.dll` 标注为“Apple TV 包用”。必须审查并扩展/明确 iOS 游戏包处理路径，不能仅因库编译成功就声称 Windows 端完整支持 iOS BC-ASTC。
- 必须核实 iOS Shell/Runtime 实际读取 ASTC pack 的环境变量、资源包路径、索引格式、纹理键一致性，以及资源包是否被 IPA 包含；做端到端合成 fixture 和真实游戏验证分层。

### iOS 壳与 IPA
- `pack/shell_build.sh`：iOS 预编壳构建入口。
- `ios/embed.py`：将改写映像写入 `Frameworks/S2AImages.dylib`。
- `pack/ipa.sh`：文档描述预编壳、`pack/ship_ext.py build`、开发直签、IPA 生成及资源包 v2 验证；需要审查完整参数与签名依赖，目标先实现可复现的 unsigned/package artifact，不得假称用户已签名。
- 目前没有已验证的完整 IPA artifact。

## 4. 重要历史修复（仍需按当前 HEAD 验证）
- `.github/workflows/contrib-check.yml` 建立 macOS 15 贡献者自检。
- workflow 创建 `$HOME/.s2arm/venv`，安装 `tools/rewriter-requirements.txt`、`pack/fonts/requirements.txt`、`launchers/macos/requirements-runtime.txt`，执行 `compat/fetch_base.sh`。
- workflow 开启 `CONTRIB_BASE_RERUN=1` 并上传 diagnostics artifact。
- `docs/安卓接入矩阵_例外.tsv` 登记 Apple Metal 专用 `nvn_bc_soft.c`，解释 Android Vulkan 使用独立 `nvn_vk_bcdec.c`。
- `tests/public_repo_scan_test.py` 改为验证当前 `contrib-check.yml`。
- `tests/t_result_lint_test.sh` 使用 `GATE_SCAN_BASE` / PR base。
- 注意：上述历史修复不代表当前完整自检已绿。

## 5. 下一对话的立即执行清单（按顺序）

1. 重新查询 Actions 最新 runs、分支 HEAD、PR #2 状态，不要假定本文快照仍最新。
2. 先修 `tools/cores.sh` 的 `renice -p $` PID 参数疑点；补/跑 `cores_lanes_test`，验证实际 nice 行为。检查当前工作树其他误改，特别是之前的替换操作是否把 `$$` 错误替换为 `$`。
3. 补齐 workflow 中 Ruff 固定版本（按仓库 pin 要求 `ruff==0.17.1`，先查 requirements/锁定策略），重跑 `py_undefined_names_test`。
4. 查 `compat/tree` 相对 PR base 的差异；按仓库约定运行 `compat/patch_new.sh`，更新 patch series/patch files 和改动说明，或证明该目录不应有差异并正确回退。不要直接豁免。
5. 单独定位 `dev_run_test` 心跳/帧号失败，复核基线为何没有结论，检查日志/测试 fixture/运行时代码；不得通过放宽断言解决。
6. 查清 5 条无结论的步骤为何缺少结果行（日志显示 gate 有 125 步但 120 结论），使门禁能完整给出结论；不允许以删减应跑项目解决。
7. targeted tests 通过后重新跑完整贡献者自检与 BC ASTC 专项 CI，保留 logs/artifacts。
8. 建立 Windows x64 workflow：在 Windows runner 满足 .NET SDK、VS Build Tools/MSVC、clang/cmake/ninja/cargo、Git for Windows、S2A_REWRITER_DEPS 等真实要求；按现有 bundle_prepare_win.py → bundle_runtime_win.py → bundle_win.py 顺序构建，Mac 预编 Shell/tzdata/fonts 作为受控输入，校验 shellId、源码指纹、SHA256，输出 ZIP + manifest。
9. 验证 Windows 包能在干净 Windows runner/VM 启动并运行 CLI；至少跑 BC→ASTC 真实合成 RomFS fixture、info/verify 与输出 hash。
10. 打通 iOS Runtime 读取 ASTC pack 的资源路径；构建 Shell；将实际改写映像与资源包装入 IPA；执行 IPA 结构/资源完整性检查。
11. 真实商业游戏的画面金样、A/B、九款回归和 iPhone 14 Pro 侧载验收仍是单独验收层。没有用户游戏文件/设备/签名凭据时，不得虚报。

## 6. 当前不可宣称已完成的事项

- 完整贡献者自检通过：否。
- PR #2 Ready / merged：否（Draft / open）。
- Windows x64 完整工具包 ZIP：未验证/未交付。
- 用户可独立处理游戏的 BC-ASTC Windows 工具链：未验收。
- iOS Runtime 完整 BC-ASTC 运行链：未端到端验收。
- 完整 IPA：未生成/未验证。
- 用户签名、侧载、iPhone 真机画面和稳定性：未完成。

## 7. 新对话开场提示

请先读取本文件，再通过 GitHub 重新检查 `myiskangbo-pixel/s2arm-astc` 的最新状态。用户已授权 B 自主开发模式：允许在工作分支自主改代码、测试、commit、反复修复 CI；不得逐步询问。第一件事优先检查并修复 `tools/cores.sh` 中疑似误写的 `renice "$nv" -p $`，再解决当前贡献者自检红项和无结论项。最终目标不是仅 CI 变绿，而是交付可用 Windows x64 S2Arm BC-ASTC 工具包与完整 iOS IPA。
