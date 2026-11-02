# 物理引擎与两个实验

计算层调用 **pooltool-billiards 0.6.0 的原版 Python 引擎**。本项目实现输入输出适配、坐标转换、基础方案检查、UI 后台计算，以及两个教学实验；没有自行重写碰撞求解器。许可证及改编记录在 [third_party/pooltool](../../third_party/pooltool/NOTICE.md)。

## 当前机器运行

已经从 `C:\Users\Administrator\Downloads\pooltool-main` 构建并安装到项目 `.venv`，下载的源码保持原样。使用这个环境启动：

```powershell
.\.venv\Scripts\python.exe main.py
```

在“计算层 → 击球参数”填写杆速、侧塞和高低杆，点击“应用并保存配置”，再点击场景预览上方的“物理仿真”。默认演示球位可以直接仿真；图片需要先四点标定、确认唯一母球和目标球号，移除重叠的误检球位。

UI 显示选中方案的采样轨迹及基础检查结果。黄色是母球、绿色是目标球。首次运行包含 Numba 编译，耗时较长；计算在后台完成。修改球位或保存参数后需重新仿真，旧请求的结果会被丢弃。

无界面检查：

```powershell
.\.venv\Scripts\python.exe main.py --check --physics
```

## 在其他机器安装

推荐 Python 3.11–3.13（pooltool 0.6 要求 Python <3.14）。Windows 引擎依赖的 Panda3D 特定开发版本来自官方 archive，依赖文件已经写好额外下载源：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-physics.txt
```

如果也从源码安装，可沿用本次方式，让 pip 优先选择本地源码包：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-physics.txt 'C:/Users/Administrator/Downloads/pooltool-main'
```

单独安装 `requirements.txt` 不包含物理引擎。不使用物理仿真时，原有几何流程仍可直接启动。适配器检查版本，避免 pooltool 接口变化造成错误结果。

## 代码与数据流

```text
图像检测 / 人工确认 → 毫米球位 → 几何候选（最多前三条）
  → pooltool 球桌、球和球杆状态 → 原版瞄准与事件式仿真
  → 碰撞 / 落袋事件 + 每球轨迹 → 基础检查与选择 → Canvas 绘制
```

- `computation/physics.py`：`PooltoolEngine.build_system / simulate / evaluate`。
- `computation/trajectory.py`：项目坐标为毫米，左上为原点；引擎坐标为米。转换为 `x_pt=(台宽-y)/1000, y_pt=x/1000`，方向也随坐标旋转。
- `models.py`：`CueAction / SimulationResult / PhysicsEvaluation` 数据契约。采样时间为秒，XYZ 为毫米；Z 是相对局部台呢的球心高度，不是空间融合的世界高度。
- `application/pipeline.py`：仿真请求快照、结果缓存及过期结果检查。
- `computation/pooltool_runtime.py`：仅将上游配置路径模块定向到本项目 `runtime/pooltool-config`，不修改用户已有的全局 pooltool 配置，不改引擎物理源码。

杆速是杆头碰撞速度，单位 m/s；`a` 为侧向击球偏移、`b` 为垂直偏移，均以球半径归一化。遵循 pooltool 杆向坐标：a 正为左塞、b 正为高杆；合成偏移不超过 0.8R。当前抬杆角固定 0，不提供跳球；这与 UI 的 2D / 3D 空间融合模式独立。

摩擦系数、恢复系数、袋口宽度和采样间隔在 `Config` / 配置 JSON 中可调。默认角袋 118 mm、中袋 137 mm 来自上游模型，其他袋角、袋深和袋口弧形等也采用上游默认；它们不是实际中式台球袋口的测量值。球洞检测目前用于图像叠加，尚未自动构建引擎袋口。

当前每个候选采用同一组用户杆速和旋转。引擎会模拟碰撞与反弹，但规划器尚未搜索翻袋、传球、杆速或加塞组合。基础检查覆盖首碰目标、目标进入所选模型袋口、母球落袋及额外黑 8 / 对方球 / 未确认球落袋等；并非完整八球裁判或真实球桌进球保证。

## The 30 Degree Rule

来源：[pooltool 原始示例](https://pooltool.readthedocs.io/en/latest/examples/30_degree_rule.html)。

```powershell
.\.venv\Scripts\python.exe examples/physics/run_experiments.py 30-degree
.\.venv\Scripts\python.exe examples/physics/run_experiments.py 30-degree --cuts 14 20 30 40 49 --speed 2.5
```

在 10×10 m 教学球桌上，使用无摩擦、完全弹性的球球模型，并检查母球在碰撞前已纯滚动。测量碰撞前与碰后再次进入滚动时的母球速度夹角，与理想公式比较。这个实验专用模型与工作台正常仿真的默认球球模型分开。

“30°”是约数，不能套用到任意低杆、加塞或滑动母球。本机默认试算：切角 14°、30°、49°，自然分离角约 27.11°、33.67°、27.05°，与公式差异小于 0.01°。公式只作为这个理想条件下的参考，不覆盖原版仿真轨迹。

输出包含 `cut_deg / hit_fraction / measured_carom_deg / theory_carom_deg / cue_speed_m_s`。

## Straight Shot Difficulty

来源：[pooltool 原始示例](https://pooltool.readthedocs.io/en/latest/examples/straight_shot.html)。

```powershell
.\.venv\Scripts\python.exe examples/physics/run_experiments.py straight-shot
.\.venv\Scripts\python.exe examples/physics/run_experiments.py straight-shot --distance 2 --positions 12 --trials 100 --errors 0.15 0.25 0.5 --seed 42
```

固定母球到袋口边缘的距离 D，将目标球沿直线放在不同的母球间距 d，向 45° 角袋击打。杆速 1 m/s、b=0.25，方向添加均匀随机误差 `[-error,+error]`；每个位置重复 trials 次。默认 12 个位置、3 档误差、每组 100 次，共 3,600 次真实引擎仿真。

CSV / JSON 分别记录 `pot_rate`（目标球进所选袋）、`scratch_rate`（母球落袋）、`safe_pot_rate`（进目标球且母球不落袋），以及 D、d、d/D、误差幅度、样本数和随机种子。固定相同种子可重复结果。概率是所选模型与误差分布下的模拟频率，不是模型输出的真实球桌命中率；不强制把 d=D/2 写成难度结论。

两个实验默认保存到 `runtime/physics-experiments/`，同名文件再次运行时覆盖；可用 `--output` 指定其他目录。

## 可选图表

默认 CSV / JSON 无需另装绘图库。需要 PNG 时再安装：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-experiments.txt
.\.venv\Scripts\python.exe examples/physics/run_experiments.py 30-degree --plot
.\.venv\Scripts\python.exe examples/physics/run_experiments.py straight-shot --plot
```

当前未额外安装 Matplotlib；数据导出和两个真实物理实验已运行验证。
