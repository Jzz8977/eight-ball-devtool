# Eight Ball — Python 开发工作台

独立、可继续开发内部逻辑的 **Python 原生桌面项目**。界面使用 Tkinter，核心代码使用 Python 标准库，无 Node.js、网页服务或浏览器依赖。不导入相邻 `eight-ball` 项目代码。

开发进度、后续执行顺序和各阶段验收条件见 [CHECKLIST.md](CHECKLIST.md)。

## 启动

需要 Python 3.11+（含 Tkinter；Windows 官方 Python 通常自带）。在当前目录执行：

```powershell
python main.py
```

启动示例界面无需第三方依赖。开发环境建议安装项目及图像依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

`requirements.txt` 安装当前项目（可编辑模式）以及 NumPy、OpenCV、Pillow，与 `pyproject.toml` 的 `vision` 依赖组保持一致。Tkinter 随 Python 安装，不通过 pip 安装；可用 `python -m tkinter` 检查。

仅需图片导入与手动球位流程时，也可单独安装 `python -m pip install Pillow`；完整依赖中的 OpenCV 提供圆形候选检测。图片解码至少需要 Pillow 或 OpenCV，示例模式仍不依赖第三方包。

训练和使用 17 类 YOLO 检测器时安装 `python -m pip install -r requirements-yolo.txt`。它增加 Ultralytics、PyYAML 及其传递依赖；安装依赖不会自动训练台球模型，相邻目录的旧单类别 YOLOv5 权重也不满足本项目 17 类约定。

以上图像 / YOLO 依赖使用最低版本声明，尚非完整锁定的环境；真实 YOLO 权重和精度仍需自行训练验证。

物理仿真复用 `pooltool-billiards==0.6.0`，已从本机下载的源码安装到本项目 `.venv`。启动 `.\.venv\Scripts\python.exe main.py` 后点击“物理仿真”；计算层可设置杆速、侧塞和高低杆。安装与模型边界见 [物理引擎及实验说明](examples/physics/README.md)。

可选安装为本地包：`python -m pip install -e .`，随后运行 `eight-ball-devtool` 或 `python -m eight_ball_devtool`。

## 项目结构

```text
eight-ball-devtool/
├── main.py                       # 无需安装即可启动
├── pyproject.toml                # Python 项目和可选依赖
├── requirements.txt              # 项目 + 图像 / OpenCV 开发依赖
├── requirements-yolo.txt         # 可选的后续 Ultralytics 开发依赖
├── requirements-physics.txt      # 可选 pooltool 0.6.0 及 Panda3D 下载源
├── requirements-experiments.txt  # 可选的实验绘图依赖
├── examples/physics/             # 30 度法则 / 直线球难度实验与说明
├── third_party/pooltool/         # 上游许可证及改编说明
├── configs/                      # 中式球桌配置和规格来源记录
├── yolo/                         # 17 类数据集、训练/验证代码、固定权重目录
├── src/eight_ball_devtool/
│   ├── ui.py                     # Tkinter 原生界面，只做交互与展示
│   ├── models.py                 # 帧、球位、路径、结果数据契约
│   ├── config.py                 # 参数验证和 JSON 持久化
│   ├── acquisition/              # 采集层
│   │   ├── __init__.py
│   │   ├── sources.py            # 采集源协议与示例帧
│   │   ├── camera.py             # 摄像头采集（空文件）
│   │   ├── screen.py             # 屏幕采集（空文件）
│   │   ├── image.py              # 真实图片解码、RGB 快照与图像 ID
│   │   └── depth.py              # 深度 / 3D 采集（空文件）
│   ├── perception/               # 感知层
│   │   ├── __init__.py
│   │   ├── detector.py           # 已有检测器协议与示例检测器
│   │   ├── opencv.py             # 真实图像圆形候选，不猜测球号
│   │   ├── yolo.py               # 17 类 YOLO 检测与权重类别检查
│   │   ├── ball_classifier.py    # 球号分类（空文件）
│   │   └── calibration.py        # OpenCV 标定（空文件）
│   ├── coordinates/              # 坐标层
│   │   ├── __init__.py
│   │   ├── transform.py          # 已有单应矩阵与坐标转换
│   │   ├── alignment.py          # 球桌对齐（空文件）
│   │   └── coordinate_system.py  # 坐标系定义（空文件）
│   ├── computation/              # 计算层
│   │   ├── __init__.py
│   │   ├── planner.py            # 已有幽灵球与直线规划
│   │   ├── aiming.py             # 纯滚动自然分离角参考公式
│   │   ├── trajectory.py         # 引擎米制坐标转换与轨迹采样
│   │   ├── collision.py          # 碰撞事件与基础进球 / 落袋检查
│   │   ├── physics.py            # pooltool 原版物理引擎适配
│   │   ├── pooltool_runtime.py   # 项目独立的引擎配置目录
│   │   └── experiments.py        # 两个可重复的原版物理实验
│   ├── fusion/                   # 融合层，仅 3D 启用
│   │   ├── __init__.py
│   │   ├── registration.py       # 已有手动刚体配准
│   │   ├── localization.py       # 空间定位（空文件）
│   │   └── coordinate_fusion.py  # 坐标融合（空文件）
│   ├── rendering/                # 渲染层
│   │   ├── __init__.py
│   │   ├── canvas.py             # 已有 Canvas 球桌绘制
│   │   ├── table_2d.py           # 2D 数字桌球扩展（空文件）
│   │   └── overlay_3d.py         # 3D 叠加（空文件）
│   └── application/              # 应用层
│       ├── __init__.py
│       ├── pipeline.py           # 已有流水线编排
│       ├── desktop.py            # 电脑终端输出扩展（空文件）
│       ├── mobile.py             # 手机终端（空文件）
│       └── glasses.py            # 眼镜终端（空文件）
├── tests/                        # 流水线与图片采集集成测试
├── runtime/                      # 运行生成的本地配置（不入库）
└── reference/web-prototype/       # 之前网页原型，仅保留视觉参考
```

后续采集、YOLO、分类器、OpenCV、物理引擎、SLAM 与终端通信的实现都放在此项目，不需要转移到其他目录。

七层均为 Python 包，`__init__.py` 保留公开导入方式；未接入的扩展文件暂为空。原生桌面 UI 仍在 `ui.py`，共享配置与数据模型仍在 `config.py` 和 `models.py`。

## 图片采集与后续逻辑

1. 启动后点击“导入图片”，选择本地图片。文件在本机解码，不上传服务器；导入成功后，`Controller.source` 从 `DemoSource` 切换为 `ImageSource`，旧球位和路线立即清除。解码或读取失败会保留原输入。
2. OpenCV 在真实像素上生成圆形候选，全部标为未知球号。检测存在误检与漏检，仅用于链路调试；没有 OpenCV 时也能通过 Pillow 导入图片并手动添加球位。
3. 点击“四点标定”，按**左上、右上、右下、左下**点选库边内沿所围台面的四角。标定前不生成毫米球位或路线。Esc 取消本轮选点。
4. 在采集画面中右键候选球，确认母球（0）和目标球号。右键空白处可补加球位，右键候选可移除误检。球号只由人工确认；未知球仅作障碍物。台面范围外的候选不进入物理计算。
5. 切换“数字球桌”，查看同一张图片转换后的球位和可行路线。目标组和最大切球角仍由计算层配置控制。当前使用理想六袋位置，不代表已识别实际袋口。
6. 点击“示例”恢复示例输入。3D 模式可对标定后的图像球位进行手动空间配准；原有 2D 融合旁路约束保持生效。

图片被解码为带路径、尺寸、RGB 字节和图像 ID 的不可变 `Frame`；预览和感知使用同一快照，不在周期计算时重复读取原文件。图片解码与候选检测在工作线程执行，候选按图片缓存；手动球号与候选编辑保存在当前会话中，重新导入时重新生成候选。四点标定和图像 ID 保存至配置，只有相同文件内容才复用；换图或旧配置没有绑定图像 ID 时要求重新标定。

也可直接用图片启动：

```powershell
python main.py --image "D:\images\台球.png"
python main.py --check --image "D:\images\台球.png"
```

`--check` 输出 `needs_calibration` 表示图片已接入、正在等待四点标定，并非回退到示例输入。

后续 YOLO 检测器实现 `Detector.detect(frame)` 即可接入 `Controller(image_detector=...)`，返回原图像素坐标下的 `Detection`。感知层不依赖 Tkinter；`Result.detections` 供原图叠加，`Result.balls/shots` 供数字球桌与计算结果显示。

## YOLO 训练与固定模型路径

训练工具和完整标注指南见 [yolo/README.md](yolo/README.md)。类别固定为 `0=cue_ball`、`1–15=ball_1…ball_15`、`16=pocket`，六个球洞标为同一类的多个实例。模型放在 `yolo/checkpoints/yolo-eight-ball.pt`；初始化权重在 `yolo/checkpoints/pretrained/`，每次训练的 best.pt / last.pt 在 `yolo/runs/`。

```powershell
python yolo/download_pretrained.py
python yolo/check_dataset.py
python yolo/train.py --device 0
python yolo/validate.py --weights yolo/runs/eight-ball/weights/best.pt --device 0
python yolo/promote.py --weights yolo/runs/eight-ball/weights/best.pt
python main.py --detector yolo
```

先安装 YOLO 依赖并填入标注数据再执行。下载初始化权重是显式步骤，训练完成后先验证再发布；本次没有下载或训练模型。YOLO 检测球洞会以独立类型显示，不进入台球障碍物计算，当前还未替换理想袋口规划。

## 283 × 155 × 84 cm 球桌规格

已查询规格来源：[星牌官网](https://www.xingpaibilliard.com/tqzcc/2020/12/01/11872.html)将 2830 × 1550 × 840 mm 列为中式球桌的**外径尺寸**；[同规格产品参数](https://uaegamer.com/products/9-6-billiard-table-2830-x-1550-x-840mm)同时列出有效台面 2540 × 1270 mm。这支持先使用该名义内径，但不能据此识别你实际球桌的品牌或证明它已被实测。

| 参数 | 项目中的用途 |
| --- | --- |
| 外形 2830 × 1550 × 840 mm | 单独记录为 `table_outer_length/width/height`，保存和导出；可供后续整桌建模、空间占位与采集构图使用 |
| 名义有效台面 2540 × 1270 mm | `table_width/table_height`，用于图像到毫米坐标转换、路径长度、碰撞边界与数字球桌比例 |
| 台呢平面在世界坐标中的位置 | `world_x/y/z` 与 `world_yaw`，仅供 3D 手动空间配准；实际台呢离地高度目前未知 |

项目以毫米为单位。坐标层界面已明确标注“有效台面”，并单独展示整桌外形，防止把桌框也算入可运动区域。

可直接使用内置配置：

```powershell
python main.py --config configs/chinese-eight-ball.json
```

该文件可被界面保存修改；规格依据保存在 `configs/table-measurements.json`，后者是资料记录，不作为运行配置加载。旧配置缺少外形字段时仍可加载，并补入默认值。

840 mm 是整桌外形高度，不能自动当成台呢平面或球心的 Z。现有 `world_z=750` 仍只是演示配准值，不是对你的球桌高度的推断；2D 模式不使用它。后续 AR 配准需要确定真实台呢平面；球心三维建模还需另加球半径。

已知尺寸能建立物理尺度，但不能单靠外形规格推导真实袋口、摩擦系数、库边弹性、相机位姿或识别模型。当前六袋仍为理想位置，实际袋口须检测或标定。

## 七层架构

采集（平面图 / 3D 图）→ 感知（YOLO 检测、球号分类、OpenCV 标定）→ 坐标（球桌坐标对齐与转换）→ 计算（瞄准、路径、碰撞预测）→ 融合（空间定位与坐标融合，仅 3D）→ 渲染（2D 数字桌球 / 3D 叠加）→ 应用（电脑 / 手机 / 眼镜）。

`application/pipeline.py` 中的 `Controller.run()` 是流水线入口。2D 在编排层跳过 `fusion.fuse()`，融合实现也拒绝 2D 调用；3D 使用可配置的平移和水平旋转完成台面至世界坐标配准。

## 已实现

- 原生桌面窗口、七层模块选择、2D / 3D 模式、周期计算暂停 / 恢复、日志。
- 示例检测器提供固定球位；后续可通过 `Detector` 协议替换，不依赖 UI。
- 纯 Python 高斯消元求解单应矩阵，图像像素经归一化映射到毫米球桌坐标。
- 幽灵球瞄准与六袋直线规划：排除障碍球、不可达碰撞点、过大切球角，排序前三条可行路线。
- 球组筛选；未知球只作为障碍物，不作为击打目标。
- Canvas 球位 / 路径 / 网格显示，球位点击查看坐标，3D 透视示意。
- 图片采集 → 圆形候选 / 人工球号确认 → 四点坐标变换 → 直线规划 → 数字球桌渲染，换图自动清除不匹配的标定和旧结果。
- 配置验证、原子写入本项目 `runtime/config.json`、JSON 导出。可用 `python main.py --config 路径` 指定配置。

## 待接入

真实摄像头、屏幕和深度采集；真实台球数据采集、YOLO 训练及逐类精度验证；OpenCV 相机畸变校正；真实袋口和摩擦参数校准；自动搜索反弹球、杆速与旋转；完整八球规则；SLAM 定位；真实 3D / AR 渲染；手机 / 眼镜通信。

已接入的 pooltool 负责给定击球参数下的球球碰撞、库边响应、旋转 / 速度演化与模型落袋。UI 在后台仿真前三个直线几何候选，并绘制选中方案的轨迹；球位或参数变化会使旧结果失效。当前袋口仍是上游模型，不代表中式球桌实测袋口。

示例模式和真实图片模式独立。默认真实图片候选来自 OpenCV 或人工添加，不使用示例球位；显式选择 `--detector yolo` 并提供合格权重后，球号和球洞由模型预测，可人工修正。3D 融合当前是手动配准，不是 SLAM。手机 / 眼镜仅是保留的输出配置项。

## 检查

```powershell
python main.py --check
python -m unittest discover -s tests -v
.\.venv\Scripts\python.exe main.py --check --physics
.\.venv\Scripts\python.exe examples/physics/run_experiments.py 30-degree
.\.venv\Scripts\python.exe examples/physics/run_experiments.py straight-shot
```

示例模式与几何测试无需第三方包；图片采集测试需要 Pillow 或 OpenCV，候选检测测试需要 OpenCV，数据集检查测试需要 PyYAML，真实物理集成测试需要 pooltool 0.6.0，未安装时对应测试会明确跳过。YOLO 接口测试使用模拟模型，不代表已经进行了真实训练或推理精度验证。
