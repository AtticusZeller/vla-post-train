# Command Reference

> 项目常用命令与用户侧验证入口。命令应可直接复制执行。

## Pending User Verification（Xense SDK 模态文档）

- **Status:** Passed（2026-08-27，用户已确认）
- **Purpose:** 确认 Xense SDK 模态表的名称、数据形态、推理依赖和封装边界表达清楚。
- **Prerequisites:** 无；在根仓库执行。
- **Commands:**

```bash
sed -n '83,113p' docs/lerobot-xense.md
```

- **Pass criteria:** 表格覆盖图像、深度、marker、力、网格和时间戳，并明确区分 SDK
  原生输出与当前 LeRobot 封装；没有把厂商内部转换算法写成仓库实现。
- **Return on failure:** 返回需要修正的行或术语，以及期望表述。

## Pending User Verification（Tabero 接入）

- **Status:** Pending
- **Purpose:** 验证 Tabero fork、submodule、分支、远端和根仓库注册信息一致。
- **Prerequisites:** 已安装 Git，并可访问 GitHub；在本次工作树根目录执行。
- **Commands:**

```bash
git submodule status methods/tabero
git -C methods/tabero status --short --branch
git -C methods/tabero remote -v
./lab method status
./lab doctor
```

- **Pass criteria:** `methods/tabero` 固定在 `1ad2078d25a7106084b9c2f247217c3f5be801e8`；分支为
  `workspace`；`origin` 指向 `AtticusZeller/Tabero.git`、`upstream` 指向
  `NathanWu7/Tabero.git`；Tabero 的 method status clean；`./lab doctor` 不因 Tabero 失败。
- **Return on failure:** 返回完整命令输出及首次失败命令。

## Pending User Verification

- **Status:** Pending
- **Purpose:** 验证 T-Rex fork、submodule、分支、远端和根仓库注册信息一致。
- **Prerequisites:** 已安装 Git，并可访问 GitHub；在本次工作树根目录执行。
- **Commands:**

```bash
git submodule status methods/t-rex
git -C methods/t-rex status --short --branch
git -C methods/t-rex remote -v
./lab method status
./lab doctor
```

- **Pass criteria:** `methods/t-rex` 固定在 `58bba48fd116a23a32989f4f362f02d8c7bc21a3`；分支为
  `workspace`；`origin` 指向 `AtticusZeller/T-Rex.git`、`upstream` 指向
  `ZhuoyangLiu2005/T-Rex.git`；T-Rex 的 method status clean；`./lab doctor` 不因 T-Rex 失败。
- **Return on failure:** 返回完整命令输出及首次失败命令。

## 常用命令

```bash
cd /root/vla-post-train
uv sync --python 3.12 --all-groups

./lab doctor
./lab method status
./lab config validate --all

# focus profile：只保留当前关注的 method（见 focus.yaml）
./lab method focus                  # 查看当前 profile 与各 method 状态
./lab method focus xense --dry-run  # 预览将删除的工作树
./lab method focus xense            # 收敛到 Xense 触觉线
./lab method focus all              # 还原全部

./lab experiment dry-run \
  experiments/flowdagger/configs/metaworld_assembly_smoke_b16_seed42.yaml
./lab experiment dry-run \
  experiments/dsrl-pi0/configs/libero90_task57_smoke_seed0.yaml
./lab experiment dry-run \
  experiments/rlinf/configs/libero10_task0_medium_seed0.yaml

uv run ruff format --check .
uv run ruff check .
uv run ty check scripts tests
uv run pytest
```

## UniVTAC 4090 跨机闭环（已验证）

- **Status:** Passed（2026-08-03）
- **Purpose:** 在实验室 RTX 4090 上运行 UniVTAC `insert_hole`，经 SSH 转发调用云端
  H20 的 N0-VTLA ZMQ 服务，并由用户电脑通过 WebRTC 查看，验证 5 个 episode 的完整
  跨机闭环。
- **Prerequisites:** 4090 推荐 Ubuntu 22.04、至少 32 GB RAM、可用 NVIDIA 驱动、
  Conda 与 `uv`；能通过 GitHub 拉取私有根仓；4090 能 SSH 访问当前 DSW；用户电脑能
  路由到 4090 的 TCP 49100 和 UDP 47998。云端 tmux `n0-vtla-zmq` 必须存活，服务只
  监听云端 `127.0.0.1:5557`。
- **Commands:**

```bash
# 云端 H20：启动策略服务。已有同名 tmux 时不要重复启动。
cd /root/vla-post-train/methods/n0-vtla
mkdir -p /mnt/data/atticux/vla-post-train/n0-vtla/logs
tmux new-session -d -s n0-vtla-zmq \
  "set -o pipefail; cd /root/vla-post-train/methods/n0-vtla && \
env CUDA_VISIBLE_DEVICES=0 \
N0VTLA_DATA_HOME=/mnt/data/atticux/vla-post-train/n0-vtla/cache \
HF_HOME=/mnt/data/atticux/vla-post-train/n0-vtla/huggingface \
VTLA_ASSET_ID=n0_insert_hole_norm \
/root/miniconda3/envs/vtla/bin/python scripts/serve_zmq.py \
--config sim_single_arm_tactile \
--ckpt /mnt/data/atticux/vla-post-train/n0-vtla/checkpoints/n0_VTLA_insert_hole \
--addr tcp://127.0.0.1:5557 --default-prompt 'insert hole' \
2>&1 | tee -a /mnt/data/atticux/vla-post-train/n0-vtla/logs/serve-zmq.log"
tmux capture-pane -p -t n0-vtla-zmq -S -80
ss -ltnp 'sport = :5557'

# 4090：通过 GitHub 同步根仓与 UniVTAC 子模块候选提交。
cd /path/to/vla-post-train
git pull --ff-only
git submodule update --init --recursive

uv sync --python 3.12 --all-groups
set -o pipefail
bash methods/univtac/scripts/install.sh 2>&1 | tee "$HOME/univtac-install.log"

source /home/atticux/miniforge3/etc/profile.d/conda.sh
conda activate UniVTAC
python -m pip install msgpack==1.1.2 pyzmq==27.1.0

# 首次交互运行 isaacsim，阅读并接受 EULA；退出后：
export ACCEPT_EULA=Y
bash methods/univtac/scripts/install.sh --gpu-smoke \
  2>&1 | tee "$HOME/univtac-4090-gpu-smoke.log"

# 4090 另开终端并保持运行：
ssh -N -L 5557:127.0.0.1:5557 \
  -p 1022 root@nlb-q4893rwy28q2gtmo1a.cn-beijing.nlb.aliyuncsslb.com

# 4090 回到根仓终端；用户电脑用 WebRTC Client 连接 4090 IP：
./lab config validate experiments/univtac/configs/insert_hole_n0_vtla_zmq_smoke.yaml
./lab experiment dry-run experiments/univtac/configs/insert_hole_n0_vtla_zmq_smoke.yaml
./lab experiment run experiments/univtac/configs/insert_hole_n0_vtla_zmq_smoke.yaml
```

- **Pass criteria:** 五个 episode 均结束且无 ZMQ timeout、缺图像键、动作 shape 或
  非有限值错误；日志持续输出 `N0-VTLA chunk` 延迟、逐 seed success/failed 与最终
  `Final Result`；run 的视频和日志写入
  `~/vla-post-train-artifacts/univtac/<run-id>/`。5-episode 成功率只作为 smoke
  方向性证据。
- **Return on failure:** 返回根 run ID、`run.json`、`logs/console.log`、首次 traceback
  前后各 100 行、`nvidia-smi`，以及云端 `tmux capture-pane -p -t n0-vtla-zmq -S -200`。
- **Observed:** 用户通过 WebRTC 观察 5 个 episode 全部成功；文本直接记录 4/4 成功及
  第五回合运行，根摘要为 exit code 0 / completed。最终 `Final Result` 未进入日志，故
  `results={}`；详见 `experiments/univtac/report.md`。这是仿真闭环，不是真机验证。

## UniVTAC 云端 H20 smoke（已验证不可用）

- **Status:** Failed as expected（2026-08-02；安装成功，当前 DSW 的 Vulkan/RTX runtime
  不可用，修订后的 smoke 已正确返回 exit 1）
- **Purpose:** 验证当前 DSW 的 2×H20 能否真正启动 Isaac Sim 4.5 headless，并加载
  TacEx 与 `tacex_uipc`；该检查用于区分“安装/编译完成”和“RTX 仿真运行兼容”。
- **Prerequisites:** 以下命令是已完成验证的复现入口。执行前确认 GPU 空闲；首次运行先
  启动 `isaacsim`，在交互式终端阅读并接受 NVIDIA Omniverse EULA，退出后再设置
  `ACCEPT_EULA=Y`。安装器不会代替用户接受许可证。
- **Commands:**

```bash
cd /root/vla-post-train
nvidia-smi

source /root/miniconda3/etc/profile.d/conda.sh
conda activate UniVTAC
export CUDA_HOME="$CONDA_PREFIX"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

"$CONDA_PREFIX/bin/python" -m pip check
"$CONDA_PREFIX/bin/python" -c 'import uipc; print(uipc.__version__)'

# 仅在你已经阅读并接受 NVIDIA Omniverse EULA 后执行：
export ACCEPT_EULA=Y
bash methods/univtac/scripts/install.sh --gpu-smoke \
  2>&1 | tee /mnt/data/atticux/vla-post-train/univtac/h20-gpu-smoke.log
```

- **Observed result:** Conda Python 的 `pip check` 与 `uipc 0.9.0` 通过；Kit 显示
  `Driver Version: 0`、空 GPU 表和 `No device could be created`。旧安装器误报成功，
  修订后相同故障明确输出 `Isaac Sim could not create a Vulkan/RTX graphics device`
  并 exit 1。NVIDIA 已明确 H20 没有 RT Cores、不受 Isaac Sim 支持；该结果不影响
  云端模型训练与推理，但当前机器不能承担 Isaac Sim 仿真。
- **Evidence:** `/mnt/data/atticux/vla-post-train/univtac/h20-gpu-smoke.log`、
  `gpu-foundation-probe.log`、`gpu-smoke-negative-verification.log`。不要在当前 H20 上
  混装 graphics 驱动或手工注入 ICD；云端仿真只在换用受支持 RTX GPU 后重新验证。

## UniVTAC 本地验证（已通过）

- **Status:** Passed（2026-08-02；Ubuntu 本地单环境 GUI 与触觉仿真已通过）
- **Purpose:** 从远端恢复 UniVTAC `dev@9ffd768` 安装器与资产修订，在本地 RTX 4060
  Laptop GPU 上完成依赖安装、最小 GPU smoke 与 GUI 启动。
- **Prerequisites:** GitHub 私有仓库访问权限、Conda、可用 NVIDIA 驱动和至少约 50 GB
  空间。Isaac Sim 4.5 官方只列出 Ubuntu 20.04/22.04，最低内存为 32 GB；当前
  Ubuntu 24.04、16 GB RAM 和 8 GB VRAM 属于未覆盖/最低边缘配置，首次验证时关闭其他
  高内存程序，并避免 4K 多相机或大规模并行场景。
- **Commands:**

```bash
git clone --recurse-submodules \
  https://github.com/AtticusZeller/vla-post-train.git
cd vla-post-train

git -C methods/univtac status --short --branch
git -C methods/univtac remote -v

set -o pipefail
bash methods/univtac/scripts/install.sh 2>&1 | tee "$HOME/univtac-install.log"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate UniVTAC
export CUDA_HOME="$CONDA_PREFIX"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
"$CONDA_PREFIX/bin/python" -m pip check
# 先运行 isaacsim，在交互式终端阅读并接受 EULA；退出后再设置：
export ACCEPT_EULA=Y
bash methods/univtac/scripts/install.sh --gpu-smoke \
  2>&1 | tee "$HOME/univtac-gpu-smoke.log"

# GPU smoke 通过后再验证 GUI；关闭窗口即可结束。
isaacsim

# 可选：单环境 TacEx 可视化，不先跑 UniVTAC 数据采集或 512-env 训练。
cd methods/univtac/third_party/TacEx
"$CONDA_PREFIX/bin/python" scripts/demos/tactile_sim_approaches/check_taxim_sim.py \
  --num_envs 1 \
  --debug_vis \
  --rendering_mode performance
```

- **Pass criteria:** UniVTAC revision 为 `9ffd768`（包含资产恢复提交 `4423bb7`）且工作树
  干净；安装命令以
  exit code 0 结束；`pip check` 无 broken requirements；
  `--gpu-smoke` 能创建并关闭 Isaac Sim、导入 `tacex` 与 `tacex_uipc`；`isaacsim`
  出现可交互窗口；可选 TacEx demo 能显示单环境触觉可视化，且无 CUDA OOM 或崩溃。
- **Return on failure:** 返回 `$HOME/univtac-install.log` 或
  `$HOME/univtac-gpu-smoke.log`；若 GUI 失败，附终端末尾 200 行、`nvidia-smi`、
  `free -h` 与是否使用 Wayland。如果首错是 tinygltf `unexpected hash`，不要直接采用
  控制台 `Actual` 值或盲目重跑；先保留归档、验证 gzip/源码内容/tar commit，并参考
  `docs/bug.md` 的 2026-08-02 条目。失败 manifest 的 build cache 会让下一次重跑表现为
  Eigen3 缺失。不要在失败后直接启动数据采集。

## 最近用户验证

- **UniVTAC 单环境触觉仿真**：Passed（2026-08-02）。RTX 4060 Laptop 8 GB 上以
  `--num_envs 1 --rendering_mode performance` 进入 `Setup complete`，GelSight
  tactile debug view 可见并连续完成多次 reset；证据见
  [`docs/univtac-smoke-20260802.md`](docs/univtac-smoke-20260802.md)。

- **状态**：Passed（2026-07-30，用户确认 `corner` 视角与 640×480 清晰度可用）
- **目的**：人工确认 FlowDAgger MetaWorld-12 冒烟运行生成的视频可播放，
  且画面确实是 Assembly 任务而非黑屏、静帧或错误任务。
- **前置条件**：可在 Codex 桌面端播放本次回复中的视频，或本机可使用 `ffplay`。
- **命令**：

```bash
ffplay -autoexit \
  /mnt/data/atticux/vla-post-train/flowdagger/20260730-035402__metaworld12-assembly-smoke-seed42/mw12-assembly-smoke_2026_07_30_11_54_14_0000--s-42/videos/eval_step0_rollout0.mp4

ffplay -autoexit \
  /mnt/data/atticux/vla-post-train/flowdagger/20260730-035402__metaworld12-assembly-smoke-seed42/mw12-assembly-smoke_2026_07_30_11_54_14_0000--s-42/videos/eval_step1_rollout0.mp4
```

- **通过标准**：两段视频都能完整播放约 10 秒；可见 MetaWorld Assembly 场景和机械臂
  连续运动；无黑屏、静帧、花屏或截断。Smoke 成功率不作为本次视觉验收标准。
- **失败时返回**：失败视频名、播放器报错，或能说明异常的时间戳/截图。

## 历史验证记录

STEAM medium 两卡复现、RLToken 无墙钟长跑和 RLToken progressive 中等预算三项
用户侧验证均已 Passed，命令、通过标准和实际结果记录在 [`docs/log.md`](docs/log.md)
对应条目中，不在本文件重复保留。

## RLToken 运行与汇总

```bash
cd /root/vla-post-train

./lab config validate \
  experiments/rlinf/configs/rlt_maniskill_stage2_progressive_seed2026.yaml
./lab experiment dry-run \
  experiments/rlinf/configs/rlt_maniskill_stage2_progressive_seed2026.yaml

./lab experiment status 20260729-021706__rlt-maniskill-stage2-progressive-seed2026
```

## Pending User Verification
- **Status:** Pending（运行中，预计约 23–30 小时后结束）
- **Purpose:** 确认 RLToken progressive-full run 把 `actor_weight_ramp_progress`
  真正跑到 1.0（`rlt/update_step≥70,000`），而不是像 progressive-100 那样中途
  停在 0.316。
- **Prerequisites:** 无需额外操作；run 已在两张 H20 上以
  tmux 会话 `rlt-maniskill` 窗口 `stage2-progressive-full` 后台运行。
- **Commands:**
```bash
cd /root/vla-post-train
./lab experiment status 20260805-100651__rlt-maniskill-stage2-progressive-full-seed2026
tmux attach -t rlt-maniskill  # 切到 stage2-progressive-full 窗口看实时进度
```
或直接看 W&B：<https://wandb.ai/atticux/rlt-maniskill/runs/hndbuens>
- **Pass criteria:** 本地退出码 0；W&B summary 中
  `rlt/update_step≥70,000` 且 `rlt/actor_weight_ramp_progress` 达到/接近
  1.0；`global_step=220`。
- **Return on failure:** 本地 traceback／非 0 退出码，或 W&B run 状态、
  `rlt/update_step` 与 `actor_weight_ramp_progress` 实际数值。

汇总某个 run 前，需要先把该 run 的 W&B URL 临时写入配置的 `tracking.run_urls`
（`primary_metrics` 同理），再执行下面两条命令，完成后按惯例把配置还原为空模板：

```bash
./lab experiment summarize <run-id>
./lab report build rlinf
```

## Pending User Verification（新增 submodule 可恢复性）

- **Status:** Pending
- **Purpose:** 验证 `methods/xense-openpi` 与 `methods/lerobot-xense` 两个新增
  submodule 可从远端递归恢复（含两者共 12 个 `third_party/*` 嵌套 submodule）。
- **Prerequisites:** 可访问 GitHub（AtticusZeller fork 及 XenseRobotics-AI / Vertax42
  上游均为公开仓库），磁盘可用空间充足。
- **Commands:**
```bash
rm -rf /tmp/vpt-clone-check && git clone --recurse-submodules \
  https://github.com/AtticusZeller/vla-post-train.git /tmp/vpt-clone-check
cd /tmp/vpt-clone-check
git submodule status --recursive | grep -E 'xense-openpi|lerobot-xense'
./lab doctor
./lab method status
```
- **Pass criteria:** 两个新 submodule 状态行首无 `-`/`+` 前缀；`lab doctor`
  全部 OK；`lab method status` 中 xense-openpi、lerobot-xense 分支为 `main`，
  upstream 分别为 XenseRobotics-AI 与 Vertax42 仓库。
- **Return on failure:** clone/update 的错误输出、`git submodule status` 结果与
  `lab doctor` 输出。

## Pending User Verification（focus profile 切换与还原）

- **Status:** Pending
- **Purpose:** 验证 `./lab method focus` 能把工作树收敛到 Xense 触觉线的 6 个
  method、再无损还原，且 `doctor` / `method status` 正确识别 inactive 状态。
- **Prerequisites:** 在根仓库 `/home/atticuszz/DevSpace/vla-post-train` 下执行；
  可访问 GitHub（还原步骤只重新 checkout，不需要重新 clone）。
  **先确认能接受删除 `methods/univtac/third_party/` 下 `curobo`、`IsaacLab`、
  `TacEx/**/build` 共约 1.3G 的 gitignore 内容——它们无法从 git 恢复，重装需重跑
  UniVTAC 安装器。**
- **Commands:**
```bash
cd /home/atticuszz/DevSpace/vla-post-train
du -sh methods/                      # 记录切换前体积
git submodule status > /tmp/vpt-submodule-before.txt

./lab method focus xense --dry-run   # 先看清单
./lab method focus xense             # 确认清单后输入 y

./lab doctor; echo "doctor exit=$?"
./lab method status
du -sh methods/

./lab method focus all               # 还原
git submodule status > /tmp/vpt-submodule-after.txt
diff /tmp/vpt-submodule-before.txt /tmp/vpt-submodule-after.txt
./lab doctor; echo "doctor exit=$?"
```
- **Pass criteria:** 收敛后 `ls methods/` 只剩 6 个目录（停用的目录会被删掉，不留
  空壳），`git status` 中不出现 ` D methods/*`；`lab doctor`
  中 7 个停用方法显示 `SKIP`、`focus` 行显示 `xense (6/13 active)`；`lab method
  status` 中它们显示 `inactive` 且 6 个活跃方法分支/upstream 正常。还原后
  `diff` 无输出（`methods/rlinf` 行的 `+` 前缀在两侧一致即可），`lab doctor` 中
  `focus` 行回到 `all (13/13 active)`。
  两次 `doctor exit` 均为 `1` 且唯一 FAIL 项是 `artifact mount not mounted` 属
  已知的本机 `/mnt/data` 未挂载，不算失败；若 `/mnt/data` 已挂载则应为 `0`。
- **Return on failure:** `./lab method focus` 的完整输出、`diff` 结果、
  `./lab doctor` 与 `./lab method status` 输出。

## 待用户验证（FastWAM fork 与 submodule 可恢复性）

- **Status:** Passed（2026-09-02，用户已确认）
- **Purpose:** 验证 `methods/fastwam` 指向个人 fork 的 `workspace` 分支、`upstream` 指向
  官方仓库，并固定到已推送、可从远端恢复的 revision。
- **Prerequisites:** 可访问 GitHub；不需要 GPU、conda 环境、数据集或 checkpoint。
- **Commands:**
```bash
cd /home/atticuszz/DevSpace/vla-post-train
./lab method status
./lab doctor
git config --get submodule.methods/fastwam.branch
git -C methods/fastwam remote -v
git -C methods/fastwam status --short --branch
git submodule status --recursive | grep 'methods/fastwam'
git ls-remote https://github.com/AtticusZeller/FastWAM.git refs/heads/workspace
```
- **Pass criteria:** `lab method status` 显示 `fastwam` 为 `workspace`、revision
  `f109f8f863fe`、clean=yes；`git config` 返回 `workspace`；`origin` 为
  `https://github.com/AtticusZeller/FastWAM.git`、`upstream` 为
  `https://github.com/yuantianyuan01/FastWAM.git`；submodule 状态行无 `-`/`+` 前缀；
  远端 `refs/heads/workspace` 与本地 `HEAD` 均为
  `f109f8f863feb49575cbcae9e6e069d38d7c5df0`；`./lab doctor` 不因 fastwam 失败。
- **Return on failure:** 上述命令的完整输出，尤其是首次失败的命令。

## 待用户验证（移除 Cosmos-Framework 与 TacWAM submodule）[已被 2026-09-03 重新接入取代]

- **Status:** Superseded（2026-09-03：`methods/tacwam` 已重新接入，本块的 grep
  pass criteria——不应命中 `tacwam`——不再成立；保留仅作历史记录，不要按本块验证）
- **Status（历史）:** Waived（2026-09-02，用户直接授权提交；用户侧验证未执行，仅有 Agent 侧证据）
- **Purpose:** 确认 `methods/cosmos` 与 `methods/tacwam` 已从根仓完全移除，且不影响其余
  method 与 focus 切换。
- **Prerequisites:** 在本工作树根目录执行；不需要 GPU 或数据。
- **Commands:**
```bash
cd /home/atticuszz/DevSpace/vla-post-train
./lab method status
./lab method focus xense
./lab doctor
git config --get-all submodule.active
grep -rn -iE 'cosmos|tacwam' .gitmodules scripts/lab.py README.md focus.yaml AGENTS.md CLAUDE.md cmd.md docs/
ls methods/
```
- **Pass criteria:** `lab method status` 与 `lab doctor` 都不再出现 `cosmos` 或 `tacwam`
  行；`./lab method focus xense` 输出「无需变更」且不报 `--skip-worktree` 错误；
  `submodule.active` 为 fastwam / lerobot / lerobot-xense / xense-openpi 四项；
  `grep` 只命中 `docs/log.md` 中的历史条目，其余文件无命中；`methods/` 下没有 `cosmos`
  和 `tacwam` 目录；`doctor` 唯一 FAIL 仍是既有的 `artifact mount not mounted`。
- **Return on failure:** 上述命令的完整输出，尤其是首次失败的命令。

## 待用户验证（重新接入 TacWAM 直接协作仓库与 submodule 可恢复性）

- **Status:** Pending
- **Purpose:** 验证 `methods/tacwam` 重新以 `Hubo1231/TacWAM` 的 `main` 分支直接接入
  （无个人 fork），固定到已推送、可从远端恢复的 revision，且不影响其余 method 与 focus
  切换。
- **Prerequisites:** 当前 GitHub 身份可读取 `Hubo1231/TacWAM`；不需要 Cosmos、PyTorch、
  模型权重或真机设备。
- **Commands:**
```bash
cd /home/atticuszz/DevSpace/vla-post-train
./lab method status
git config --get submodule.methods/tacwam.branch
git -C methods/tacwam remote -v
git -C methods/tacwam status --short --branch
git -C methods/tacwam rev-parse HEAD
git submodule status --recursive | grep 'methods/tacwam'
git ls-remote https://github.com/Hubo1231/TacWAM.git refs/heads/main
./lab doctor
```
- **Pass criteria:** `lab method status` 显示 `tacwam` 为 `main`、revision
  `ba42007cfa31`、clean=yes；`git config` 返回 `main`；`origin` 与 `upstream` 均为
  `https://github.com/Hubo1231/TacWAM.git`；submodule 状态行无 `-`/`+` 前缀；本地
  `HEAD` 与远端 `main` 均为 `ba42007cfa310ec51291359245474887cdba8f27`；`./lab doctor`
  中 `method:tacwam OK`（唯一预期 FAIL 仍是既有的 `artifact mount not mounted`）。
- **Return on failure:** 上述命令的完整输出，尤其是 TacWAM 的 remote、branch、revision
  和 submodule status。
