# Eight Ball YOLO 训练工程

所有命令均在 `eight-ball-devtool` 项目根目录运行。使用 Ultralytics 目标检测，默认从 YOLO11n 预训练权重开始微调；支持通过 `--base` 更换本地检测模型。当前不附带已训练模型，也没有创建假的空 `.pt` 文件。

## 固定目录

第一次做标注请先看 [新手标注步骤](ANNOTATION_QUICKSTART.md)，CVAT 的 17 类配置已放在 `configs/cvat-labels.json`。

```text
yolo/
├── configs/
│   ├── dataset.yaml                  # 数据集根目录与 17 类固定映射
│   ├── classes.txt                   # 标注工具导入用，每行对应 class_id
│   └── train.yaml                    # 训练超参数
├── datasets/eight-ball/
│   ├── images/{train,val,test}/       # 你的原始图片，可含子目录
│   └── labels/{train,val,test}/       # 相同相对路径、同名 .txt 标注
├── checkpoints/
│   ├── pretrained/yolo11n.pt          # 官方初始化权重，下载后出现
│   ├── yolo-eight-ball.pt             # 训练并发布后的固定应用权重
│   ├── yolo-eight-ball.json           # 类别、来源、校验摘要
│   └── archive/                      # 发布新权重前备份旧权重
├── runs/                             # 每次训练/验证结果，运行时生成
│   └── eight-ball/weights/
│       ├── best.pt                   # 本次最佳权重
│       └── last.pt                   # 中断续训用，包含训练状态
├── check_dataset.py
├── download_pretrained.py
├── train.py
├── validate.py
└── promote.py
```

图片、标签、训练结果和模型文件默认不提交 Git；空目录由 `.gitkeep` 保留。用你自己的存储备份数据和训练结果。

## 类别固定为 17 类

| class_id | 名称 | 标注对象 |
| --- | --- | --- |
| 0 | `cue_ball` | 母球 |
| 1–15 | `ball_1` … `ball_15` | 对应号码的整颗球 |
| 16 | `pocket` | 球洞 / 袋口可见开口区域 |

六个球洞都使用 `pocket`，是同一类别的六个实例，不是六种类别。不要交换 `ball_1` 与母球的顺序。运行时加载模型会检查完整名称和顺序，拒绝 COCO、单类别台球或其他类别顺序的权重。

## 标注格式与采集建议

采用 [Ultralytics YOLO 检测格式](https://docs.ultralytics.com/datasets/detect/)：一张图片配同名 txt，每个物体一行：

```text
class_id x_center y_center width height
```

坐标均除以图像宽高，范围为 0–1。例如 `scene001.jpg` 的 `scene001.txt` 可以包含：

```text
0 0.30 0.55 0.02 0.04
8 0.62 0.42 0.02 0.04
16 0.05 0.08 0.04 0.06
```

这只是说明格式的例子，不是可直接训练的完整标注。球框住整颗球，不只框数字；球洞框住可见开口，不框整段桌框。每张图标注所有可确认的球与所有可见球洞；裁剪、遮挡导致看不见的洞不补画。无目标图片也提供空 txt，作为负样本。

1. 训练图应包含实际使用视角的整桌画面，覆盖不同相机距离、斜视、光照、反光、遮挡、球面转向和球的摆放；不能只收集大幅球号特写，再期待整桌远距离识别。
2. 每个球号、母球与球洞都要有足够样本；先按每类数百个有效实例准备，再看逐类验证指标补充难例，这不是保证准确率的固定门槛。
3. 相同球号收集多个朝向。数字太小、被遮挡或转到背面时，单帧图像可能没有足够信息；采集时记录真值，不能凭猜测标号。实在无法确定的帧先移出训练集，不要随意漏标或乱标。
4. 同一段视频、同一局或同一采集场景按组分配 train/val/test；不要将相邻帧随机散到三组。脚本检测跨组完全相同文件，但不能识别所有相邻帧泄漏。
5. 可从按场景分组的 80/10/10 划分开始，关注 1–15 各球号及 `pocket` 的召回率、混淆矩阵。8 号球与黑色袋口、6/9 号及花色球是需要单独检查的难例。

训练集默认要求 17 类均出现；验证集缺类会在检查报告中列出，不应只凭一个汇总 mAP 判断所有球号都学会了。独立 test 集只用于最后评估。检查脚本验证标签格式、范围、配对和跨组文件重复；图像是否能解码仍由 Ultralytics 训练加载器检查。

## 安装与准备权重

```powershell
python -m pip install -r requirements-yolo.txt
python yolo/download_pretrained.py
```

第二条命令才会联网下载官方初始化权重到 `checkpoints/pretrained/yolo11n.pt`；它不是训练后的台球模型。也可从 [官方 YOLO11 模型页面](https://docs.ultralytics.com/models/yolo11/)手动下载，放到该路径。使用 CUDA 时，先按 [PyTorch 官方安装说明](https://pytorch.org/get-started/locally/)配置与你设备兼容的 PyTorch；脚本支持 `--device 0`、`cpu`、`mps`，不自动安装显卡驱动或改动已有 Torch。

## 检查、训练、验证和发布

先放入标注数据，再运行：

```powershell
python yolo/check_dataset.py
python yolo/train.py --check-only
python yolo/train.py --device 0
```

`--check-only` 不导入 Torch、不下载权重、不启动训练。空数据集会给出明确错误，不会生成演示训练结果。非 GPU 环境用 `--device cpu`，Apple Silicon 可用 `--device mps`。默认 100 轮、输入 1280、batch 4、workers 0；数字属于小目标，1280 作为起点而非准确率保证。内存不足可降低 batch / imgsz；代价是小目标细节可能减少。

改变参数或使用更大初始化模型：

```powershell
python yolo/download_pretrained.py --size s
python yolo/train.py --base yolo/checkpoints/pretrained/yolo11s.pt --imgsz 1280 --batch 4 --epochs 150 --name eight-ball-s --device 0
```

默认关闭水平/垂直镜像，减弱色相和饱和度变换，避免直接翻转数字和破坏区分球号的颜色。超参数在 `configs/train.yaml`，需根据你的真实数据验证调整。

每次训练使用独立 run，重名会由 Ultralytics 自动递增，不覆盖旧训练。脚本打印实际输出目录。假设本次为 `runs/eight-ball`：

```powershell
python yolo/validate.py --weights yolo/runs/eight-ball/weights/best.pt --device 0
python yolo/validate.py --weights yolo/runs/eight-ball/weights/best.pt --split test --device 0
python yolo/promote.py --weights yolo/runs/eight-ball/weights/best.pt
```

发布会验证模型类别，再复制到 **`yolo/checkpoints/yolo-eight-ball.pt`**；已有固定权重会先备份至 `archive/`。训练脚本不会自动替换当前应用权重，让你先看验证结果再发布。

中断续训使用 [Ultralytics resume](https://docs.ultralytics.com/modes/train/#resuming-interrupted-trainings)：

```powershell
python yolo/train.py --resume yolo/runs/eight-ball/weights/last.pt --device 0
```

resume 恢复原优化器、轮数和训练参数。训练已完成后增加轮数或更换数据，使用 `--base best.pt --name 新名字` 开始新的微调，不把它当作中断续训。数据配置会保存为 `runs/configs/` 下的绝对路径版本，以避免 Ultralytics 的全局 datasets_dir 导致目录漂移；迁移到另一台电脑时从本项目配置重新生成。

## 接入现有桌面工具

发布模型后运行：

```powershell
python main.py --detector yolo
python main.py --detector yolo --image "D:\images\台球.png"
```

也可用 `--weights 路径` 临时指定本地权重。预览使用同一张图片的真实像素，RGB 转 BGR 后交给模型，返回原图坐标及置信度。0–15 类作为球位，16 类保留为 `kind='pocket'` 并在原图上单独显示；**球洞不会成为障碍球或击打目标**。

现阶段球洞检测用于原图叠加，还未替换几何引擎的理想六袋位置；真实袋口配准与规划需要后续单独接入。模型球号仍可能出错，右键可修正。原有 OpenCV 模式继续作为默认，不会因为出现某个 `.pt` 文件就静默切换模型。

当前仓库没有真实标注数据、训练后的权重或精度指标；脚本检查和接口测试不等于已经完成训练或验证推理性能。
