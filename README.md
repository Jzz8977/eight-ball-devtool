# Eight Ball — Python 开发工作台

独立、可继续开发内部逻辑的 **Python 原生桌面项目**。界面使用 Tkinter，核心代码使用 Python 标准库，无 Node.js、网页服务或浏览器依赖。不导入相邻 `eight-ball` 项目代码。

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

仅需 JPEG / WebP 图片预览时也可单独安装 `python -m pip install Pillow`；未安装时支持 Tk 自带的 PNG / GIF / PPM。

后续开发新版 Ultralytics YOLO 检测器时使用可选的 `python -m pip install -r requirements-yolo.txt`。它增加 Ultralytics 及其传递依赖；安装依赖不会自动完成检测器或球号分类器的接入，也不代表相邻目录的旧 YOLOv5 权重可直接使用。

以上是最低版本依赖声明，尚非精确锁定的环境；本次没有执行联网安装或验证模型推理环境。

可选安装为本地包：`python -m pip install -e .`，随后运行 `eight-ball-devtool` 或 `python -m eight_ball_devtool`。

## 项目结构

```text
eight-ball-devtool/
├── main.py                       # 无需安装即可启动
├── pyproject.toml                # Python 项目和可选依赖
├── requirements.txt              # 项目 + 图像 / OpenCV 开发依赖
├── requirements-yolo.txt         # 可选的后续 Ultralytics 开发依赖
├── configs/                      # 中式球桌配置和规格来源记录
├── src/eight_ball_devtool/
│   ├── ui.py                     # Tkinter 原生界面，只做交互与展示
│   ├── models.py                 # 帧、球位、路径、结果数据契约
│   ├── config.py                 # 参数验证和 JSON 持久化
│   ├── acquisition/              # 采集层
│   │   ├── __init__.py
│   │   ├── sources.py            # 已有示例帧、图片帧
│   │   ├── camera.py             # 摄像头采集（空文件）
│   │   ├── screen.py             # 屏幕采集（空文件）
│   │   ├── image.py              # 图像采集扩展（空文件）
│   │   └── depth.py              # 深度 / 3D 采集（空文件）
│   ├── perception/               # 感知层
│   │   ├── __init__.py
│   │   ├── detector.py           # 已有检测器协议与示例检测器
│   │   ├── yolo.py               # YOLO 检测（空文件）
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
│   │   ├── aiming.py             # 瞄准（空文件）
│   │   ├── trajectory.py         # 路径（空文件）
│   │   ├── collision.py          # 碰撞预测（空文件）
│   │   └── physics.py            # 物理引擎（空文件）
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
├── tests/test_pipeline.py        # 标准库 unittest
├── runtime/                      # 运行生成的本地配置（不入库）
└── reference/web-prototype/       # 之前网页原型，仅保留视觉参考
```

后续采集、YOLO、分类器、OpenCV、物理引擎、SLAM 与终端通信的实现都放在此项目，不需要转移到其他目录。

七层均为 Python 包，`__init__.py` 保留原有公开导入方式；已有逻辑移动到对应实现文件，新增扩展文件暂为空。原生桌面 UI 仍在 `ui.py`，共享配置与数据模型仍在 `config.py` 和 `models.py`。

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
- 图片预览、左上 → 右上 → 右下 → 左下四点标定，求解矩阵并保存归一化点。新图片清除旧图的标定点。
- 配置验证、原子写入本项目 `runtime/config.json`、JSON 导出。可用 `python main.py --config 路径` 指定配置。

## 待接入

真实摄像头、屏幕和深度采集；YOLO 模型与球号分类；OpenCV 相机畸变校正；库边反弹、旋转和速度仿真；SLAM 定位；真实 3D / AR 渲染；手机 / 眼镜通信。

图片当前仅用于预览和标定，不会将示例检测结果冒充为真实识别结果。数字球桌使用固定示例输入；路线和耗时则由 Python 实时计算。3D 融合当前是手动配准，不是 SLAM。手机 / 眼镜仅是保留的输出配置项。

## 检查

```powershell
python main.py --check
python -m unittest discover -s tests -v
```

所有基础检查和界面均无需第三方包；可选的 `vision` 依赖组为下一阶段接入 OpenCV 预留，安装它不会自动启用尚未实现的识别器。
