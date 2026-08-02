# Bug Journal

> 开发过程中的硬核经验：触发情况、解决方案、原因解释。

<!-- 新 bug 追加到本行下方 -->

## 2026-08-02：Isaac Sim GPU foundation 失败会以 exit 0 制造 smoke 假阳性

- **触发：** 在 Alibaba Cloud DSW 的 2×H20 上执行安装器 `--gpu-smoke`；CUDA 和
  `nvidia-smi` 均正常，但 Isaac Sim 依赖 Vulkan/RTX graphics device。
- **现象：** Kit 输出 `Driver Version: 0`、空 GPU 表、`No device could be created` 和
  `Unable to get IGpuFoundation`，但 `AppLauncher(...)` 提前以 exit 0 结束 Python；旧
  安装器没有看到后续 TacEx 导入，也仍打印 `Installation completed successfully`。
- **环境证据：** 默认 `vulkaninfo` 只枚举 CPU llvmpipe，系统 ICD 目录没有 NVIDIA
  JSON；显式使用 RLinf/SAPIEN 的 NVIDIA ICD 后，匹配 580.95.05 的
  `libGLX_nvidia.so.0` 仍返回 `VK_ERROR_INCOMPATIBLE_DRIVER`。这证明当前容器的 NVIDIA
  Vulkan graphics 路径没有建立；独立于该软件栈故障，NVIDIA 对 H20 的
  [直接答复](https://forums.developer.nvidia.com/t/does-the-h20-graphics-card-support-isaac-lab-isaac-sim/339701)
  与 Isaac Sim 官方仓库 [Discussion #446](https://github.com/isaac-sim/IsaacSim/discussions/446)
  均确认 H20 没有 RT Cores、不受 Isaac Sim 支持。补齐 ICD 不能消除最终硬件边界。
- **处理：** GPU smoke 记录完整 Kit 输出，要求 GPU foundation device count 大于 0，
  并要求 Python 输出 TacEx/`tacex_uipc` 最终成功哨兵；出现设备创建错误或哨兵缺失即
  exit 1。用户命令固定使用 `$CONDA_PREFIX/bin/python`，避免根 `.venv` 抢占解释器。
- **验证：** 修订前同一日志误报成功；修订后真实 H20 复验以 exit 1 结束，并明确输出
  `Isaac Sim could not create a Vulkan/RTX graphics device`。证据见
  `/mnt/data/atticux/vla-post-train/univtac/h20-gpu-smoke.log`、
  `gpu-foundation-probe.log` 和 `gpu-smoke-negative-verification.log`。
- **状态：** smoke 假阳性已修复；当前 H20 不再投入 Isaac Sim runtime 修复，本地
  RTX 4060 单环境 GUI/触觉仿真已通过，后续采用本地仿真、云端模型训练与推理。

## 2026-08-02：UniVTAC vendored TacEx 漏掉 GelSight low-res gelpad

- **触发：** 完整安装后运行 TacEx `check_taxim_sim.py --num_envs 1 --debug_vis
  --rendering_mode performance`。
- **现象：** Isaac Sim 能启动且显存仍有约 6.9 GB 空闲，但 USD stage 报
  `Gelpad_low_res.usd` 无法打开，随后 gelpad prim 不是有效 rigid body，Robot
  articulation 创建失败。
- **原因：** UniVTAC 提交 `a9abc0d` 为规避 Git LFS 配额删除 low-res 资产；后续
  `97a3fe3` 把其他 LFS pointer 恢复成普通 Git 文件时漏掉该文件，而 vendored robot USD
  仍保留 payload 引用。官方 TacEx 当前文件树和 UniVTAC 早期提交 `b371b18` 均包含它。
- **处理：** 从 `b371b18` 原样恢复 267,452 字节 USD crate，blob
  `54ec424ca942aa55cfdc1a168b5e71cdc6e16ab8`，不以 mid/high-res 文件猜测替代。
- **验证：** 相同单环境 `performance` 命令进入 `Setup complete`，触觉 debug view 可见，
  连续 reset 且无 CUDA OOM；见 [`docs/univtac-smoke-20260802.md`](univtac-smoke-20260802.md)。
- **状态：** 已在 method 提交 `4423bb7` 修复并通过用户 GUI 验收。

## 2026-08-02：UniVTAC 安装链同时受 channel、镜像与上游版本脚本影响

- **触发：** 修复首次 `grep` 退出后，在全新 `UniVTAC` Conda 环境继续执行官方完整
  安装链。
- **现象：** 默认 Anaconda channel 先要求非交互 TOS；DSW Aliyun PyPI 镜像缺少
  `uv`/构建依赖；Isaac Lab 2.1.1 wrapper 强制安装 torch 2.7/cu128，覆盖 UniVTAC
  需要的 torch 2.5.1/cu124；cuRobo 构建缺 `vcs-versioning`；未 bootstrap 的 vcpkg
  已存在 toolchain 文件，导致只检查该文件时误判安装完成。
- **原因：** 原脚本把多个外部项目各自的“当前默认值”当成同一套固定环境，且把目录
  存在、元数据存在和可执行组件可用混为一谈。网络镜像和非交互云端又放大了这一问题。
- **处理：** Conda 环境限定 conda-forge；bootstrap 包显式使用官方 PyPI；固定 Isaac
  Lab v2.1.1 和 cuRobo commit，直接 editable 安装 Isaac Lab 源码扩展以保留指定
  PyTorch；用 vcpkg 可执行文件而非 toolchain 文件作为 bootstrap 完成标志；把真实
  GPU 启动改为显式 `--gpu-smoke`，不再让安装器自动跑 512-env 训练或数据采集。
- **进一步实装：** 云端 `retry-9` 已成功 bootstrap vcpkg 并识别 GNU 11.4/CUDA
  12.4，但复用了上次失败后残留的 `build/vcpkg.json`；libuipc 因 manifest 内容未变化
  把 `VCPKG_MANIFEST_INSTALL` 强制设为 `OFF`，空的 `vcpkg_installed` 随后报
  `Eigen3Config.cmake` 缺失。隔离 6.2 MB 的失败 build 后，`retry-10` 正常进入 39 个
  port 的 manifest install，证明后续 `CMAKE_MAKE_PROGRAM`/compiler 提示只是 vcpkg
  首错的级联输出。
- **后续已解决阻塞：** `retry-10` 安装至 34/39，随后 tinygltf 2.9.3 的 GitHub tarball
  SHA512 从 vcpkg 记录的 `4f4d479a…` 变为 `6dbcff3e…`。归档可正常解压且 tag 仍指向
  `14ba27113e…`；同一时段 vcpkg [#53143](https://github.com/microsoft/vcpkg/issues/53143)
  在 macOS 与 WSL2/Ubuntu 报告相同类型的 tinygltf archive hash 变化。云端对归档完成
  gzip、源码内容和 tar commit 校验后使用临时 overlay，安装余下 5 个 ports；随后补齐
  `mypy`、嵌套 pip 官方源与 pyuipc 搜索顺序，最终 wheel 和 `import uipc` 通过。
- **证据边界：** 云端 Python/CUDA 构建链完整通过，libuipc 针对 H20 `sm_90` 编译，
  `pip check` 无冲突；本地 RTX 4060 GUI/触觉仿真通过。云端 H20 的 Isaac Sim
  Vulkan/RTX runtime 失败属于独立环境边界，见上一条；本地 GUI 证据见
  [`docs/univtac-smoke-20260802.md`](univtac-smoke-20260802.md)。
- **状态：** 安装器和依赖安装已修复；tinygltf 临时 overlay 未固化，若上游归档再次
  变化仍需重新校验，不能关闭完整性检查。

## 2026-08-01：UniVTAC 首次安装被 `set -e` 与无匹配 `grep` 静默中止

- **触发：** 在尚无 `UniVTAC` Conda 环境的机器上从已激活的 base 环境执行
  `bash -x scripts/install.sh`。
- **现象：** 脚本在输出任何 `Creating conda environment` 之前以 exit code 1
  结束，trace 最后是 `conda env list`、`grep UniVTAC`、
  `is_conda_env_exists=`；运行前后都没有创建 `UniVTAC` 环境。
- **原因：** 脚本启用了 `set -e`，而
  `is_conda_env_exists=$(conda env list | grep ${CONDA_ENV_NAME})` 在首次安装时
  必然因无匹配返回 1。赋值命令继承命令替换的非零状态，Bash 因而在进入后续
  `[ -z ... ]` 判断和 `conda create` 前直接退出。Python 3.10、Isaac Sim 4.5、
  Isaac Lab 2.1.1 与 PyTorch 2.5.1 的主版本组合符合当前 Isaac Lab 文档，
  不是本次首错原因。
- **后续静态阻塞：** vcpkg 首次安装条件写反且检查相对 `Toolchain`，随后却把
  `CMAKE_TOOLCHAIN_FILE` 指向不存在的 `$HOME/Toolchain/vcpkg/...`；fresh
  `tacex_uipc` 安装后也没有恢复 UniVTAC 根目录，最终 `bash collect_data.sh`
  会在 `third_party/TacEx` 下找不到文件。安装器还把 cuRobo 全量 pytest、
  512-env TacEx 训练和数据采集耦合在依赖安装流程中。
- **证据：** 原始 trace 与完整分析位于
  `/mnt/data/atticux/vla-post-train/univtac/install-20260801T124939Z/`。按用户要求撤销
  Agent 新增文件后，fork `dev@1e9272a` 与官方 `main@05bcd3e` 的完整 tree 均为
  `283d1675...`、安装脚本 blob 均为 `8efc2591...`；第二次实装仍以相同 trace 和
  exit code 1 结束，证据位于
  `/mnt/data/atticux/vla-post-train/univtac/install-20260801T132145Z-reverted/`。
- **状态：** 已诊断、未修复；本轮只向用户提供可搜索证据，不改上游安装脚本。

## 2026-07-31：`takeover_max=25` 收窄导致 Box Close / Bin Picking 评估时机械臂卡死

- **触发：** `metaworld12_suite.yaml`（协议 v1）把 `InterventionHandler` 的
  `takeover_min/max` 从上游微软 FlowDAgger 官方默认（也是本仓库自己历史 Assembly
  基线实际使用的值）`5/60` 显式改成了 `0/25`，且从未启用已有的
  `takeover_max_start`/`takeover_max_curriculum_episodes` 课程扩展。
- **现象：** 用户直接在评估视频里看到机械臂"抓住不动"。抽帧核对（对照同一
  eval 批次里的真实成功案例，证实录像管线本身没问题）确认：失败 episode 里
  机械臂从第 5 步左右起，在整段 300 步（10 秒）视频里逐像素完全静止；
  console.log 的逐步诊断显示底层动作并非零输出——Box Close 案例里 z 分量持续在
  `-3.6` 附近（远超 `metaworld_pi05_adapter.py:118` 的 `np.clip(-1,1)` 执行时钳制
  上限），Bin Picking 案例里动作收敛到一个近似恒定的小幅度值——两者都指向
  观测-动作闭环卡进了一个自洽定点：夹爪被卡住不动，画面不再变化，策略于是
  持续输出几乎相同的（在 Box Close 案例里是持续钳制到边界的）动作，没有任何
  机制能检测"卡住"并跳出。
- **根因：** `shared/intervention_handler.py` 的 `beta_decay` 模式下，
  `check_progress()` 完全不看 `off_nominal_distance`，只按每回合开始时采样的
  固定步数（`takeover_min`~`takeover_max`）切换到脚本专家、随后专家开到回合
  结束。`perform_control_eval` 则完全不调用 `intervention_handler`，全程
  300 步都由策略自主决策。协议 v1 把窗口固定为 0~25 步（300 步任务的 8%），
  且训练全程 4,000 BC step 都不会扩大，导致策略几乎从未在训练中获得"任务
  后半段、尤其是精细接触阶段"的自主决策经验；一旦评估要求它独立走完全程，
  在 Box Close（合盖卡扣）、Bin Picking（抓取+精确放置）这类难点集中在后半段
  的任务上就会进入未训练过的状态并卡死。Door Lock/Hammer/Stick Push 等容错更
  高的任务受影响小。`filter_failures=1` 会整条丢弃失败的探索 episode，所以
  这不是训练 buffer 被污染，纯粹是自主决策窗口配置过窄导致的覆盖缺口——不是
  代码逻辑错误，`InterventionHandler`/`dagger_loop.py`/eval 循环都严格按配置
  执行。
- **处理：** 把 `metaworld12_suite.yaml` 的 `takeover_min/max` 改回官方默认
  `5/60`，未启用课程扩展（避免和窗口复原两个变量混在一起判断效果）；同时把
  `protocol`/`id` 从 `metaworld12-v1` 升级到 `metaworld12-v2`，并将旧协议下已
  完成的 15 个正式 run 的 `run.json` 标记 `historical: true`（`scripts/
  flowdagger_suite.py::_suite_results` 已经会跳过 `historical` run），使
  `metaworld12-report.md` 干净地回到 0/36，不需要删除旧证据。旧 15 个 run
  （含 50%→59.7% 的 seed0 汇总）作为协议 v1 的历史证据保留在
  `experiments/flowdagger/runs/`，不进入新协议的正式结论。
- **复盘（协议 v2 seed0 12/12 跑完后）：** Box Close 按预期修复
  （−20pp → +32pp）。但 Bin Picking 完全没好转（v1 −44pp → v2 −48pp），
  两次协议下失败 episode 的收敛动作向量几乎数值重合
  （`[0.03,-0.05,-0.35,0.60]` vs `[0.04,-0.08,-0.35,0.59]`），说明它不是
  接管窗口覆盖不够的问题，更像是冻结的 π0.5 底座策略在这个具体视觉场景下
  存在一个稳定吸引点，噪声空间 steering 拉不出来。对照原论文 Table 1
  （arXiv:2607.08877）：Bin Picking 官方结果是 0.56→0.69（+13pp），且原文
  声称 MetaWorld 上没有任何任务出现下降。但 `methods/flowdagger/README.md`
  明确写着发布的代码"only running the MetaWorld assembly task"——官方只在
  Assembly 上验证过这份参考实现；本仓库 12-task 里的 Coffee Pull/Dial
  Turn/Lever Pull/Pick Place/Soccer 5 个任务完全是自建扩展，论文没有报告过。
  原文对干预机制的描述是人类操作员"判断策略行为不满意时"实时介入，更接近
  `InterventionHandler` 里已实现但当前协议未启用的 `intervention_mode=
  disagreement`（按策略/专家动作差距触发），而不是当前用的 `beta_decay`
  固定步数调度。`disagreement` 模式没有实测验证，作为已知选项记录，不在
  本轮范围内。
- **结论：** 用户决定到此收尾，不再追加 Bin Picking 专项实验；Bin Picking
  标记为协议 v2 下的已知未解决限制，其余 11 个任务的 seed0 结果作为当前
  最新证据。

## 2026-07-30：根 `uv run` 的 PATH 抢占目标 Conda Python

- **触发：** `./lab experiment run` 自身由根 `.venv` 的 `uv run` 启动，再通过
  `conda run -n dsrl_pi0 python ...` 进入 FlowDAgger。
- **现象：** 第一次 MetaWorld-12 smoke 实际执行根 Python 3.12，导入阶段报
  `ModuleNotFoundError: No module named 'jax'`；尚未进入 GPU。
- **处理：** launcher 根据 `conda` 可执行文件与配置的环境名解析目标
  `<conda-root>/envs/<name>/bin`，将它显式放到子进程 PATH 首位。诊断确认实际 Python
  变为 `dsrl_pi0/bin/python`、JAX 0.8.0；后续 smoke 正常完成。
- **原因：** 当前环境中 `conda run` 不会可靠覆盖祖先进程显式传入且以根
  `.venv/bin` 开头的 PATH；不能仅凭命令包含 `conda run` 推断目标 Python 已生效。

## 2026-07-30：评估视频误用了 steering 的低清策略帧

- **触发：** `perform_control_eval` 将 `obs_to_img()` 的输出直接加入视频；该函数会按
  `resize_image=128` 缩放给 steering 网络使用，且沿用策略的 `corner3` 视角。
- **现象：** MP4 只有 128×128，画面偏俯视，无法清楚判断机械臂与对象交互。
- **处理：** 在 MetaWorld adapter 中新增共享同一 model/data 的独立 MuJoCo renderer；
  策略仍用 `corner3`，视频改用 `corner`、640×480、30 FPS，并只渲染配置要求保存的
  episode。用户已确认新视角与清晰度。
- **原因：** 模型输入和人类证据的优化目标不同；复用预处理帧会把模型分辨率和相机约束
  错误地施加到实验视频上。

## 2026-07-29：`lab experiment summarize` 因 wandb SDK API 变更而失败

- **触发：** `scripts/monitor.py::collect_wandb` 用 `run.scan_history(stream="system")`
  拉取 GPU system metrics，并用 `dict(run.summary)` 展开 run summary；当前锁定的
  `wandb==0.28.1` 已把 `stream` 参数移到 `history()`，`scan_history()` 不再接受该
  关键字，且 `run.summary` 顶层 `dict()` 转换后仍会保留嵌套字段（如 `_wandb`）为
  不可 JSON 序列化的 `SummarySubDict`。
- **现象：** `./lab experiment summarize <run_id>` 先报
  `TypeError: Run.scan_history() got an unexpected keyword argument 'stream'`；
  用 `run.history(stream="system", pandas=False)` 替换后又报
  `TypeError: Object of type SummarySubDict is not JSON serializable`。
- **处理：** 把 GPU system stream 调用改为 `run.history(stream="system",
  pandas=False)`；summary 展开改用 `getattr(run.summary, "_json_dict",
  run.summary)` 后再 `dict()`，同时兼容测试用的 plain-dict fake 和真实
  `HTTPSummary` 对象。`tests/test_monitor.py` 的 `FakeRun` 同步把
  `scan_history` 换成签名匹配的 `history`。
- **原因：** wandb 官方 Public API（`/wandb/wandb` 源码 `apis/public/runs.py`）
  在 `scan_history()` 里去掉了 `stream` 关键字，只有 `history()` 保留；`run.summary`
  是懒加载的 `HTTPSummary`，其 `_json_dict` 才是纯 dict 快照，直接 `dict()`
  顶层转换不会递归展开内部 `SummarySubDict`。

## 2026-07-28：Ray 从根 `uv run` 继承 working dir 后遗漏源码目录

- **触发：** 根 `lab` 通过 `uv run` 启动 RLinf 子进程，子进程再调用
  `ray.init()`；当前 Ray 默认启用 `RAY_ENABLE_UV_RUN_RUNTIME_ENV`。
- **现象：** Ray 自动将方法仓作为 working dir 打包，worker 从
  `/tmp/ray/.../working_dir_files/` 导入代码；LIBERO EnvWorker 报
  `ModuleNotFoundError: No module named 'rlinf.envs.venv'`，即使该目录在提交后的
  方法仓中存在。
- **处理：** 单节点共享源码实验在根配置中设置
  `RAY_ENABLE_UV_RUN_RUNTIME_ENV=0`，同时继续显式固定方法
  `UV_PROJECT_ENVIRONMENT`、`UV_NO_SYNC=1` 和方法入口；短 Ray worker probe
  已确认从提交后的 `methods/rlinf/rlinf/envs/venv/` 成功导入模块。
- **原因：** Ray 的 uv runtime-env hook 根据祖先 `uv run` 自动复制 driver
  环境；它与本项目“根 uv 环境只做编排、方法使用独立环境”的边界冲突，生成的
  working-dir 包并不等价于方法仓源码。

## 2026-07-27：Ray 工作目录导致 `uv` 误建第二套 RLinf 环境

- **触发：** 正式入口把 Ray `working_dir` 切换到根仓库的 RLinf 子模块，但只激活了
  `/root/RLinf/.venv`，未声明该路径也是 `uv` 的项目环境。
- **现象：** 第一次 worker 初始化在子模块下创建 `.venv` 并准备重新下载
  PyTorch/CUDA；改绑外部环境后，自动 sync 又改写了该环境并造成
  `huggingface-hub`/Transformers 版本冲突。两次均未进入 GPU 训练。
- **处理：** 安全中断运行并保留失败 run 记录；设置 `RLINF_VENV`、
  `UV_PROJECT_ENVIRONMENT=/root/RLinf/.venv` 和 `UV_NO_SYNC=1`，确认正式启动只解析
  现有 Python，不再自动同步或改写依赖。
- **原因：** 激活 `VIRTUAL_ENV` 不会改变 `uv` 默认按当前项目选择 `.venv` 的规则；
  Ray 改变工作目录后，两个环境路径不再一致。

## 2026-07-27：桌面工作区缺失只读挂载点导致 `apply_patch` 无法启动

- **触发：** 补丁工具在 bwrap 初始化阶段尝试挂载声明存在、实际缺失的 `.git`、
  `.agents` 和 `.codex` 目录。
- **现象：** `Can't mkdir ...: Read-only file system`，补丁尚未读取目标项目。
- **处理：** 只创建缺失的空 mount-point 目录后重试；未修改任何现有 Git 数据。
- **原因：** 桌面 workspace permission profile 与磁盘目录状态不一致，不是项目代码故障。

## 2026-07-27：`/mnt/data` 当前以只读方式挂载

- **触发：** `findmnt -T /mnt/data` 返回 `ro`。
- **影响：** 历史证据可读取，但新 `experiment run` 无法创建外部产物目录。
- **处理：** `lab doctor` 显示 WARN；运行入口在创建 metadata 前检查可写性并报错。
- **恢复标准：** DSW 将 OSS 重新以 `rw` 挂载后再启动任何新训练。

## 2026-07-27：`/mnt/data` 已恢复可写

- **验证：** `findmnt -T /mnt/data` 显示 `rw`，并通过 `test -w /mnt/data`。
- **影响：** 新实验可以创建 `/mnt/data/atticux/vla-post-train/<method>/<run-id>/` 产物目录。
