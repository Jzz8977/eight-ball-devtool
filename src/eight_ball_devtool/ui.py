"""Native Tkinter UI. All domain computation lives in sibling Python modules."""
from dataclasses import replace
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from .application import LAYERS
from .config import Config
from .coordinates import TableTransform, validate_quad
from .rendering import TableRenderer
from .models import Point

BG = '#f3f5f2'
FG = '#293d32'
MUTED = '#899888'
GREEN = '#2c7358'
LINE = '#e2e8df'
WHITE = '#ffffff'
FONT = 'Microsoft YaHei UI'


class Workbench(tk.Tk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.title('Eight Ball Developer Studio — Python 工作台')
        if controller.path.name != 'config.json':
            self.title(f'Eight Ball Developer Studio — Python 工作台 [{controller.path.stem}]')
        self.geometry('1360x900')
        self.minsize(1120, 790)
        self.configure(bg=BG)
        self.option_add('*Font', (FONT, 9))
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure('TCombobox', fieldbackground=BG, background=LINE, foreground=FG, padding=5)
        self.style.configure('TCheckbutton', background=WHITE, foreground=FG, padding=4)
        self.style.map('TCombobox', fieldbackground=[('readonly', '#f8faf6')])
        self.selected_layer = 0
        self.selected_ball = None
        self.running = True
        self.view = 'digital'
        self.image_path = None
        self.image_original = None
        self.image_display = None
        self.image_size = None
        self.image_rect = None
        self.calibrating = False
        self.points = []
        self.form_vars = {}
        self.loader = ThreadPoolExecutor(max_workers=1, thread_name_prefix='image-acquisition')
        self.image_job = None
        self.physics_job = None
        self.last_message = ''
        self._build()
        self.renderer = TableRenderer(self.canvas)
        self.canvas.bind('<Configure>', lambda e: self.draw())
        self.canvas.bind('<Button-1>', self.canvas_click)
        self.canvas.bind('<Button-3>', self.image_context_menu)
        self.bind('<Escape>', lambda e: self.cancel_calibration())
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.refresh_layer_cards()
        self.build_form()
        frame = self.controller.source.capture()
        if frame.source == 'image':
            self.install_image_preview(frame)
        self.run_pipeline()
        self.log('System', 'Python 原生桌面工作台已启动，七层模块位于本项目 src 目录')
        if self.controller.startup_warning:
            self.log('Config', self.controller.startup_warning)
        self.after(700, self.tick)

    def label(self, parent, text, size=9, color=FG, bg=WHITE, bold=False, **kw):
        return tk.Label(parent, text=text, font=(FONT, size, 'bold' if bold else 'normal'), fg=color, bg=bg, **kw)

    def button(self, parent, text, command, primary=False, **kw):
        return tk.Button(parent, text=text, command=command, bg=GREEN if primary else '#f6f8f3', fg=WHITE if primary else '#5d7654', activebackground='#3a815f' if primary else '#e9efe3', activeforeground=WHITE if primary else FG, relief='flat', bd=0, padx=14, pady=8, cursor='hand2', font=(FONT, 9), **kw)

    def panel(self, parent, **kw):
        return tk.Frame(parent, bg=WHITE, highlightbackground=LINE, highlightthickness=1, **kw)

    def _build(self):
        sidebar = tk.Frame(self, bg='#172e28', width=188)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        self.label(sidebar, '❽  EIGHT BALL', 17, '#edf4e7', '#172e28', True).pack(anchor='w', padx=18, pady=(30, 2))
        self.label(sidebar, 'PYTHON DEVELOPER STUDIO', 7, '#91a98b', '#172e28').pack(anchor='w', padx=21)
        box = tk.Frame(sidebar, bg='#263f32')
        box.pack(fill='x', padx=15, pady=(34, 25))
        self.label(box, 'Eight Ball 本地项目', 10, '#d7e4ca', '#263f32').pack(anchor='w', padx=13, pady=(12, 4))
        self.label(box, '原生桌面 · Python 3', 8, '#9cb395', '#263f32').pack(anchor='w', padx=13, pady=(0, 12))
        for text, action in [('◈   系统总览', self.overview), ('⌘   架构流水线', lambda: self.select_layer(0)), ('▣   场景调试', self.toggle_view), ('☷   模块配置', lambda: self.select_layer(self.selected_layer)), ('≡   清空日志', self.clear_logs)]:
            tk.Button(sidebar, text=text, command=action, anchor='w', bg='#2e4938' if '总览' in text else '#172e28', fg='#cadcba', activebackground='#304d3b', activeforeground=WHITE, relief='flat', bd=0, padx=17, pady=13, cursor='hand2').pack(fill='x', padx=12, pady=4)
        self.label(sidebar, '本地 Python 运行\n逻辑与 UI 均在当前目录', 8, '#7f9c7d', '#172e28', justify='left').pack(side='bottom', anchor='w', padx=22, pady=23)
        content = tk.Frame(self, bg=BG)
        content.pack(side='left', fill='both', expand=True)
        top = tk.Frame(content, bg='#fcfdfb', height=53)
        top.pack(fill='x')
        top.pack_propagate(False)
        self.label(top, '工作空间    /    系统总览', 9, '#7c8f75', '#fcfdfb').pack(side='left', padx=25)
        self.input_badge = self.label(top, '●  Python 本地引擎     /     示例输入', 8, '#7b9271', '#fcfdfb')
        self.input_badge.pack(side='right', padx=25)
        # Keep every control reachable on smaller screens and high-DPI desktops.
        scroll_area = tk.Frame(content, bg=BG)
        scroll_area.pack(fill='both', expand=True)
        viewport = tk.Canvas(scroll_area, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_area, orient='vertical', command=viewport.yview)
        scrollbar.pack(side='right', fill='y')
        viewport.pack(side='left', fill='both', expand=True)
        viewport.configure(yscrollcommand=scrollbar.set)
        outer = tk.Frame(viewport, bg=BG)
        body_window = viewport.create_window(0, 0, window=outer, anchor='nw')
        main = tk.Frame(outer, bg=BG)
        main.pack(fill='both', expand=True, padx=24, pady=(20, 12))

        def resize_body(event=None):
            viewport.itemconfigure(body_window, width=viewport.winfo_width())
            viewport.itemconfigure(body_window, height=max(viewport.winfo_height(), outer.winfo_reqheight()))
            viewport.configure(scrollregion=viewport.bbox('all'))

        viewport.bind('<Configure>', resize_body)
        outer.bind('<Configure>', lambda e: viewport.configure(scrollregion=viewport.bbox('all')))
        self.bind('<MouseWheel>', lambda e: viewport.yview_scroll(-int(e.delta/120), 'units') if not isinstance(e.widget, (ttk.Combobox, tk.Text)) else None)
        self.after_idle(resize_body)
        heading = tk.Frame(main, bg=BG)
        heading.pack(fill='x', pady=(0, 17))
        heading_left = tk.Frame(heading, bg=BG)
        heading_left.pack(side='left')
        self.label(heading_left, 'SYSTEM OVERVIEW / PYTHON', 8, '#809474', BG).pack(anchor='w')
        self.label(heading_left, '系统总览', 24, FG, BG, True).pack(anchor='w', pady=(3, 5))
        self.label(heading_left, '视觉感知、坐标变换与几何计算，在一个 Python 工程中协作。', 9, MUTED, BG).pack(anchor='w')
        self.run_button = self.button(heading, 'Ⅱ  暂停计算', self.toggle_running, True)
        self.run_button.pack(side='right', padx=(8, 0))
        self.button(heading, '↗  导出配置', self.export).pack(side='right')
        metrics = tk.Frame(main, bg=BG)
        metrics.pack(fill='x', pady=(0, 17))
        self.metric_labels = []
        for i, (title, value, subtitle) in enumerate([('输入来源', 'DEMO', '固定示例球位 · 不伪装识别结果'), ('流水线耗时', '— ms', 'Python 实测 · 不含绘制时间'), ('球位 / 可行方案', '8 / —', '直线入袋 · 含障碍物检测'), ('运行模块', '6 / 7', '2D 模式 · 融合层旁路')]):
            metrics.columnconfigure(i, weight=1, uniform='metrics')
            card = self.panel(metrics)
            card.grid(row=0, column=i, sticky='ew', padx=(0 if i == 0 else 6, 0 if i == 3 else 6))
            self.label(card, title, 9, MUTED).pack(anchor='w', padx=15, pady=(11, 5))
            val = self.label(card, value, 23, FG)
            val.pack(anchor='w', padx=15)
            sub = self.label(card, subtitle, 7, '#92a184')
            sub.pack(anchor='w', padx=15, pady=(5, 10))
            self.metric_labels.append((val, sub))
        architecture = self.panel(main)
        architecture.pack(fill='x', pady=(0, 17))
        arch_head = tk.Frame(architecture, bg=WHITE)
        arch_head.pack(fill='x', padx=17, pady=(12, 11))
        self.label(arch_head, '系统架构  /  七层处理链路', 10, FG, bold=True).pack(side='left')
        self.mode_var = tk.StringVar(value=self.controller.config.mode)
        for text, value in [('3D 空间', '3d'), ('2D 平面', '2d')]:
            tk.Radiobutton(arch_head, text=text, variable=self.mode_var, value=value, command=self.set_mode, bg=WHITE, fg=GREEN, selectcolor='#e6efdf', activebackground=WHITE, indicatoron=False, relief='flat', bd=0, padx=12, pady=5, cursor='hand2').pack(side='right', padx=2)
        self.layer_container = tk.Frame(architecture, bg=WHITE)
        self.layer_container.pack(fill='x', padx=15, pady=(0, 10))
        self.layer_cards = []
        for i, (name, en, detail) in enumerate(LAYERS):
            self.layer_container.columnconfigure(i, weight=1, uniform='layers')
            card = tk.Frame(self.layer_container, highlightthickness=1, highlightbackground=LINE, bg='#fafcf7', cursor='hand2')
            card.grid(row=0, column=i, sticky='nsew', padx=3)
            number = self.label(card, f'0{i+1}     {"◇" if i == 4 else "→"}', 11, '#8ca47b', '#fafcf7')
            number.pack(anchor='w', padx=10, pady=(10, 8))
            self.label(card, name, 10, FG, '#fafcf7', True).pack(anchor='w', padx=10)
            self.label(card, en, 6, '#95a388', '#fafcf7').pack(anchor='w', padx=10, pady=(3, 7))
            status = self.label(card, '示例链路', 7, '#759166', '#fafcf7')
            status.pack(anchor='w', padx=10, pady=(0, 10))
            for widget in [card, *card.winfo_children()]:
                widget.bind('<Button-1>', lambda event, index=i: self.select_layer(index))
            self.layer_cards.append((card, status))
        self.flow_label = self.label(architecture, '', 8, '#8a9b7b', '#fafcf7', anchor='w', padx=18, pady=8)
        self.flow_label.pack(fill='x')
        workspace = tk.Frame(main, bg=BG)
        workspace.pack(fill='both', expand=True, pady=(0, 15))
        workspace.columnconfigure(0, weight=1)
        workspace.columnconfigure(1, weight=0)
        workspace.rowconfigure(0, weight=1)
        scene = self.panel(workspace)
        scene.grid(row=0, column=0, sticky='nsew', padx=(0, 16))
        scene_head = tk.Frame(scene, bg=WHITE)
        scene_head.pack(fill='x', padx=17, pady=(12, 8))
        self.label(scene_head, '场景预览', 10, FG, bold=True).pack(side='left')
        self.scene_status = self.label(scene_head, '● 几何引擎运行中', 8, '#819b70')
        self.scene_status.pack(side='left', padx=12)
        self.button(scene_head, '导入图片', self.import_image).pack(side='right')
        self.physics_button = self.button(scene_head, '物理仿真', self.start_physics)
        self.physics_button.pack(side='right', padx=3)
        self.button(scene_head, '示例', self.use_demo).pack(side='right', padx=3)
        self.view_button = self.button(scene_head, '采集画面', self.toggle_view)
        self.view_button.pack(side='right', padx=5)
        self.canvas = tk.Canvas(scene, bg='#eff3eb', highlightthickness=1, highlightbackground=LINE, height=240)
        self.canvas.pack(fill='both', expand=True, padx=14)
        toolbar = tk.Frame(scene, bg=WHITE)
        toolbar.pack(fill='x', padx=16, pady=5)
        self.coordinate_text = self.label(toolbar, '点击球位查看球桌坐标', 8, '#8d9d7f')
        self.coordinate_text.pack(side='left')
        self.button(toolbar, '四点标定', self.start_calibration).pack(side='right')
        self.shot_label = self.label(scene, '等待计算…', 9, '#658054', '#f6f9f1', anchor='w', padx=17, pady=12)
        self.shot_label.pack(fill='x', side='bottom')
        config_panel = self.panel(workspace, width=276, height=440)
        config_panel.grid(row=0, column=1, sticky='ns')
        config_panel.grid_propagate(False)
        config_panel.pack_propagate(False)
        self.config_title = self.label(config_panel, '模块配置', 11, FG, bold=True, anchor='w', padx=18, pady=13)
        self.config_title.pack(fill='x')
        self.config_body = tk.Frame(config_panel, bg=WHITE)
        self.config_body.pack(fill='both', expand=True, padx=18)
        self.save_button = self.button(config_panel, '应用并保存配置', self.apply_config, True)
        self.save_button.pack(fill='x', padx=18, pady=13)
        logs_panel = self.panel(main)
        logs_panel.pack(fill='x')
        self.label(logs_panel, '运行日志  /  Python Console', 9, FG, bold=True, anchor='w', padx=15, pady=8).pack(fill='x')
        self.log_text = tk.Text(logs_panel, height=3, bg=WHITE, fg='#7c9070', relief='flat', font=('Consolas', 8), padx=15, pady=2, state='disabled', wrap='word')
        self.log_text.pack(fill='x', pady=(0, 8))
        self.label(main, 'Eight Ball Developer Studio  ·  v0.2.0     |     Tkinter 原生界面     |     YOLO / SLAM 尚未接入', 7, '#98a38f', BG, anchor='w').pack(fill='x', pady=(10, 0))

    def log(self, source, text):
        self.log_text.configure(state='normal')
        self.log_text.insert('end', f'{datetime.now():%H:%M:%S}  [{source}]  {text}\n')
        if int(self.log_text.index('end-1c').split('.')[0]) > 300:
            self.log_text.delete('1.0', '50.0')
        self.log_text.see('end')
        self.log_text.configure(state='disabled')

    def clear_logs(self):
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.configure(state='disabled')

    def overview(self):
        self.view = 'digital'
        self.view_button.configure(text='采集画面')
        self.select_layer(0)
        self.draw()

    def refresh_layer_cards(self):
        is_3d = self.controller.config.mode == '3d'
        for i, (card, status) in enumerate(self.layer_cards):
            bg = '#edf4e6' if i == self.selected_layer else '#fafcf7'
            card.configure(bg=bg, highlightbackground='#88a875' if i == self.selected_layer else LINE)
            for child in card.winfo_children():
                child.configure(bg=bg)
            image_mode = self.controller.source.capture().source == 'image'
            status.configure(text='已旁路 · 仅 3D' if i == 4 and not is_3d else ['真实图片' if image_mode else '示例输入', '图像候选 / 人工确认' if image_mode else '示例检测器', '单应矩阵', '直线规划', '手动配准', 'Canvas 绘制', '桌面已接入'][i])
        self.flow_label.configure(text='图像采集 → 感知识别 → 球桌坐标 → 几何计算 → ' + ('空间融合 → 三维示意 → 终端' if is_3d else '二维渲染 → 终端  ·  融合层已旁路'))
        self.metric_labels[3][0].configure(text='7 / 7' if is_3d else '6 / 7')
        self.metric_labels[3][1].configure(text='3D 模式 · 手动空间配准' if is_3d else '2D 模式 · 融合层旁路')

    def select_layer(self, index):
        self.selected_layer = index
        self.refresh_layer_cards()
        self.build_form()

    def set_mode(self):
        self.controller.config.mode = self.mode_var.get()
        self.refresh_layer_cards()
        self.build_form()
        self.run_pipeline()
        self.log('Pipeline', '3D 空间融合已启用（手动配准）' if self.mode_var.get() == '3d' else '2D 融合层已旁路')

    def build_form(self):
        for child in self.config_body.winfo_children():
            child.destroy()
        self.form_vars = {}
        config = self.controller.config
        index = self.selected_layer
        self.config_title.configure(text=f'0{index+1} / {LAYERS[index][0]}配置')
        disabled = index == 4 and config.mode != '3d'
        self.save_button.configure(state='disabled' if disabled else 'normal')
        self.label(self.config_body, LAYERS[index][2], 9, '#829371', wraplength=230, justify='left').pack(anchor='w', pady=(0, 14))

        form_parent = self.config_body

        def entry(name, title):
            self.label(form_parent, title, 8, '#809172').pack(anchor='w', pady=(0, 4))
            var = tk.StringVar(value=f'{getattr(config, name):g}')
            field = ttk.Entry(form_parent, textvariable=var, state='disabled' if disabled else 'normal')
            field.pack(fill='x', pady=(0, 10))
            self.form_vars[name] = (var, float)

        def check(name, title):
            var = tk.BooleanVar(value=getattr(config, name))
            ttk.Checkbutton(self.config_body, text=title, variable=var).pack(anchor='w', pady=3)
            self.form_vars[name] = (var, bool)

        def combo(name, title, choices):
            self.label(form_parent, title, 8, '#809172').pack(anchor='w', pady=(0, 4))
            var = tk.StringVar(value=next(label for label, value in choices.items() if value == getattr(config, name)))
            ttk.Combobox(form_parent, textvariable=var, values=list(choices), state='readonly').pack(fill='x', pady=(0, 12))
            self.form_vars[name] = (var, lambda value: choices[value])

        if index == 0:
            frame = self.controller.source.capture()
            source_text = f'当前输入：{Path(frame.path).name}\n原图：{frame.width} × {frame.height}\n\n图片已送入感知和坐标流水线。\n先标定台面四角，再右键确认球号。' if frame.source == 'image' else '当前输入：固定示例球位\n\n导入图片后将切换真实图片源。\n支持 PNG / JPEG / WebP 等格式。'
            self.label(self.config_body, source_text+'\n\n摄像头 / 屏幕 / 深度输入待接入。', 9, '#748b68', justify='left', wraplength=230).pack(anchor='w')
            self.button(self.config_body, '选择本地图片', self.import_image).pack(fill='x', pady=18)
        elif index == 1:
            detector_name = getattr(self.controller.image_detector, 'display_name', '自定义检测器')
            self.label(self.config_body, f'图片检测：{detector_name}\n\n右键可确认或修正球号，\n也可添加遗漏球位、移除误检。\n\nYOLO 模式需自行训练 17 类权重。\n球洞仅叠加展示，不作障碍球。\n四点坐标变换使用纯 Python 求解。', 9, '#748b68', justify='left', wraplength=230).pack(anchor='w')
            self.button(self.config_body, '开始四点标定', self.start_calibration).pack(fill='x', pady=18)
        elif index == 2:
            entry('table_width', '有效台面长度（库边内沿）/ mm')
            entry('table_height', '有效台面宽度（库边内沿）/ mm')
            entry('ball_radius', '台球半径 / mm')
            self.label(self.config_body, f'整桌外形：{config.table_outer_length:g} × {config.table_outer_width:g}\n× {config.table_outer_height:g} mm（不作坐标边界）\n内径当前为名义值，可按实测修改。', 8, MUTED, justify='left', wraplength=230).pack(anchor='w', pady=4)
            self.label(self.config_body, f'已保存标定点：{len(config.calibration)} / 4', 8, MUTED).pack(anchor='w', pady=8)
        elif index == 3:
            tabs = ttk.Notebook(self.config_body)
            tabs.pack(fill='both', expand=True)
            planning, striking = tk.Frame(tabs, bg=WHITE, padx=8, pady=12), tk.Frame(tabs, bg=WHITE, padx=8, pady=12)
            tabs.add(planning, text='几何规划')
            tabs.add(striking, text='击球参数')
            form_parent = planning
            combo('target_group', '可击打球组', {'全色球 1–7': 'solid', '花色球 9–15': 'stripe', '黑 8': 'eight', '任意球': 'any'})
            entry('max_cut_angle', '最大切球角 / °')
            self.label(planning, '几何候选 → pooltool 仿真\n检查首碰、模型进球与母球落袋。\n\n保存参数后点击“物理仿真”。\n袋口/摩擦参数仍需实测校准。', 8, '#8b9b7d', justify='left').pack(anchor='w', pady=8)
            form_parent = striking
            entry('cue_speed', '杆头碰撞速度 / m·s⁻¹')
            entry('cue_side_spin', '侧塞 a（-0.8～0.8）')
            entry('cue_top_spin', '高低杆 b（-0.8～0.8）')
            self.label(striking, 'a 正为左塞，b 正为高杆。\n遵循 pooltool 的杆向坐标约定。\n当前抬杆角固定为 0，不计算跳球。', 8, MUTED, justify='left').pack(anchor='w', pady=4)
        elif index == 4:
            if disabled:
                self.label(self.config_body, '当前 2D 模式已旁路本层。\n切换 3D 空间模式后可配置。', 9, MUTED, justify='left').pack(anchor='w', pady=5)
            else:
                for name, title in [('world_x', '世界平移 X / mm'), ('world_y', '世界平移 Y / mm'), ('world_z', '台面平移 Z（非外形高度）/ mm'), ('world_yaw', '台面朝向 / °')]:
                    entry(name, title)
                self.label(self.config_body, '手动刚体配准，尚未接入 SLAM。', 8, MUTED).pack(anchor='w')
        elif index == 5:
            check('show_paths', '显示瞄准 / 入袋路线')
            check('show_grid', '显示球桌网格')
            check('show_numbers', '显示球号')
            check('blue_cloth', '竞赛蓝台呢')
            self.label(self.config_body, '2D：Canvas 数字球桌\n3D：透视示意，非真实 AR 渲染', 8, MUTED, justify='left').pack(anchor='w', pady=18)
        else:
            combo('device', '目标终端', {'电脑': '电脑', '手机': '手机', '眼镜': '眼镜'})
            self.label(self.config_body, '电脑：本地桌面界面已接入\n手机 / 眼镜：预留输出目标\n\n终端选择会保存到本地配置，\n尚未实现设备通信与数据推送。', 9, '#819473', justify='left', wraplength=230).pack(anchor='w', pady=10)

    def apply_config(self):
        original = self.controller.config
        try:
            updated = replace(original, **{name: cast(var.get()) for name, (var, cast) in self.form_vars.items()})
            updated.validate()
            updated.save(self.controller.path)
        except (ValueError, OSError, tk.TclError) as error:
            messagebox.showerror('配置无法保存', str(error), parent=self)
            return
        self.controller.config = updated
        self.run_pipeline()
        self.log('Config', f'{LAYERS[self.selected_layer][0]}配置已保存：{self.controller.path}')

    def run_pipeline(self):
        try:
            result = self.controller.run()
        except (ValueError, RuntimeError, NotImplementedError) as error:
            self.log('Pipeline', str(error))
            self.metric_labels[2][0].configure(text='— / —')
            self.shot_label.configure(text=f'处理失败：{error}')
            self.draw()
            return
        image_mode = result.frame.source == 'image'
        self.metric_labels[0][0].configure(text='IMAGE' if image_mode else 'DEMO')
        self.metric_labels[0][1].configure(text=f'{result.frame.width} × {result.frame.height} · 真实图片' if image_mode else '固定示例球位 · 不伪装识别结果')
        self.input_badge.configure(text='●  Python 本地引擎     /     '+('真实图片输入' if image_mode else '示例输入'))
        self.metric_labels[1][0].configure(text=f'{result.elapsed_ms:.2f} ms')
        self.metric_labels[1][1].configure(text='检测按图片缓存 · 坐标/规划实测' if image_mode else 'Python 实测 · 不含绘制时间')
        self.metric_labels[2][0].configure(text='— / —' if result.status == 'needs_calibration' else f'{len(result.balls)} / {len(result.shots)}')
        self.metric_labels[2][1].configure(text=f'{len(result.detections)} 个候选 · 待标定' if result.status == 'needs_calibration' else ('未知球号仅作障碍物' if image_mode else '直线入袋 · 含障碍物检测'))
        if result.physics:
            simulation = result.physics.selected
            status = '通过基础检查' if simulation.accepted else '不推荐'
            self.shot_label.configure(text=f'pooltool · {status} · 目标 {simulation.shot.target.number} · 杆速 {simulation.action.speed_m_s:g} m/s · {simulation.reason}', wraplength=650)
        elif result.shots:
            shot = result.shots[0]
            self.shot_label.configure(text=f'{"图片球位方案（理想袋口）" if image_mode else "推荐示例方案"}  ·  目标 {shot.target.number} 号球    /    切球 {shot.cut_angle:.1f}°    /    路径 {shot.distance/1000:.2f} m')
        else:
            self.shot_label.configure(text=result.message or '当前配置下没有可行直线方案，请调整目标球组或最大切球角。')
        if result.message and result.message != self.last_message:
            self.log('Pipeline', result.message)
        self.last_message = result.message
        self.scene_status.configure(text='● '+('待四点标定' if result.status == 'needs_calibration' else ('图片球位' if image_mode else '示例球位'))+(' · 已暂停' if not self.running else ''))
        self.draw()

    def tick(self):
        if self.running:
            self.run_pipeline()
        self.after(700, self.tick)

    def start_physics(self):
        if self.physics_job is not None:
            return
        try:
            request = self.controller.physics_request()
        except ValueError as error:
            messagebox.showinfo('物理仿真', str(error), parent=self)
            return
        self.physics_button.configure(state='disabled', text='仿真中…')
        self.physics_job = self.loader.submit(self.controller.calculate_physics, request)
        self.log('Physics', 'pooltool 正在仿真几何候选；首次运行需编译物理计算内核')
        self.after(80, self.poll_physics)

    def poll_physics(self):
        if not self.physics_job.done():
            self.after(80, self.poll_physics)
            return
        job, self.physics_job = self.physics_job, None
        self.physics_button.configure(state='normal', text='物理仿真')
        try:
            key, evaluation = job.result()
            if not self.controller.accept_physics(key, evaluation):
                self.log('Physics', '球位或参数已变化，旧仿真结果已丢弃，请重新仿真')
                return
        except Exception as error:
            self.log('Physics', str(error))
            messagebox.showerror('物理仿真失败', str(error), parent=self)
            return
        self.log('Physics', f'已模拟 {len(evaluation.candidates)} 个候选：{evaluation.selected.reason}')
        self.run_pipeline()

    def toggle_running(self):
        self.running = not self.running
        self.run_button.configure(text='Ⅱ  暂停计算' if self.running else '▷  继续计算')
        self.scene_status.configure(text='● 几何引擎运行中' if self.running else '● 计算已暂停')
        self.log('Session', '继续周期计算' if self.running else '已暂停周期计算')

    def draw(self):
        if not hasattr(self, 'renderer'):
            return
        if self.view == 'source':
            self.draw_image()
        else:
            self.renderer.draw(self.controller.result, self.controller.config, self.selected_ball)

    def toggle_view(self):
        self.cancel_calibration()
        self.view = 'source' if self.view == 'digital' else 'digital'
        self.view_button.configure(text='数字球桌' if self.view == 'source' else '采集画面')
        self.draw()

    def import_image(self):
        path = filedialog.askopenfilename(parent=self, title='选择采集图片', filetypes=[('图像', '*.png *.jpg *.jpeg *.webp *.gif *.ppm'), ('所有文件', '*.*')])
        if not path:
            return
        if self.image_job is not None:
            self.image_job.cancel()
        self.image_job = self.loader.submit(self.controller.prepare_image, path)
        self.scene_status.configure(text='● 图片解码与候选检测中…')
        self.after(60, self.poll_image)

    def poll_image(self):
        job = self.image_job
        if job is None:
            return
        if not job.done():
            self.after(60, self.poll_image)
            return
        self.image_job = None
        try:
            prepared = job.result()
            self.install_image_preview(prepared[0].capture())
        except Exception as error:
            self.log('Source', f'导入失败，保留原输入：{error}')
            messagebox.showerror('无法加载图片', str(error), parent=self)
            return
        self.controller.use_image(*prepared)
        self.selected_ball = None
        self.refresh_layer_cards()
        self.build_form()
        self.run_pipeline()
        self.log('Source', f'已接入图片：{self.image_path}，{self.controller.source.capture().width} × {self.controller.source.capture().height}')

    def install_image_preview(self, frame):
        # The preview and downstream detector consume the SAME decoded snapshot.
        photo = tk.PhotoImage(data=f'P6\n{frame.width} {frame.height}\n255\n'.encode()+frame.rgb, format='PPM')
        self.image_original = photo
        self.image_size = (frame.width, frame.height)
        self.image_path = frame.path
        self.cancel_calibration()
        self.points = []
        self.view = 'source'
        self.view_button.configure(text='数字球桌')

    def use_demo(self):
        if self.image_job is not None:
            self.image_job.cancel()
            self.image_job = None
        self.controller.use_demo()
        self.cancel_calibration()
        self.image_original = None
        self.image_path = None
        self.image_rect = None
        self.view = 'digital'
        self.view_button.configure(text='采集画面')
        self.selected_ball = None
        self.refresh_layer_cards()
        self.build_form()
        self.run_pipeline()
        self.log('Source', '已恢复示例采集源')

    def close(self):
        self.loader.shutdown(wait=False, cancel_futures=True)
        self.destroy()

    def draw_image(self):
        c = self.canvas
        c.delete('all')
        self.image_rect = None
        w, h = c.winfo_width(), c.winfo_height()
        if self.image_original is None:
            c.create_text(w/2, h/2-14, text='导入本地图片，开始采集预览与四点标定', fill='#7e9473', font=(FONT, 11))
            c.create_text(w/2, h/2+14, text='导入后切换真实图片源；右键确认 / 添加球位', fill='#9ba991', font=(FONT, 8))
            return
        iw, ih = self.image_size
        scale = min(max(1, w-30)/iw, max(1, h-40)/ih, 1)
        if isinstance(self.image_original, tk.PhotoImage):
            import math
            divisor = max(1, math.ceil(1/scale))
            self.image_display = self.image_original.subsample(divisor)
            dw, dh = self.image_display.width(), self.image_display.height()
        else:
            from PIL import ImageTk
            dw, dh = max(1, int(iw*scale)), max(1, int(ih*scale))
            self.image_display = ImageTk.PhotoImage(self.image_original.resize((dw, dh)))
        x, y = (w-dw)/2, (h-dh)/2
        self.image_rect = (x, y, dw, dh)
        c.create_image(x, y, image=self.image_display, anchor='nw')
        points = self.points if self.calibrating else self.controller.config.calibration
        if len(points) > 1:
            flat = [value for px, py in points for value in (x+px*dw, y+py*dh)]
            if len(points) == 4:
                flat += flat[:2]
            c.create_line(*flat, fill='#f2ca64', width=2, dash=(5, 4))
        for i, (px, py) in enumerate(points):
            cx, cy = x+px*dw, y+py*dh
            c.create_oval(cx-7, cy-7, cx+7, cy+7, fill='#e5b14c', outline=WHITE)
            c.create_text(cx, cy, text=i+1, fill='#2e4129', font=('Segoe UI', 8, 'bold'))
        result = self.controller.result
        if result and result.frame.source == 'image' and not self.calibrating:
            for i, detection in enumerate(result.detections):
                cx = x+detection.center.x/result.frame.width*dw
                cy = y+detection.center.y/result.frame.height*dh
                radius = max(5, detection.radius/result.frame.width*dw)
                pocket = detection.kind == 'pocket'
                color = '#bb9fe5' if pocket else ('#e1bf65' if detection.number is None else '#a8efac')
                c.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, outline=color, width=2)
                label = '球洞' if pocket else ('?' if detection.number is None else str(detection.number))
                c.create_text(cx, cy-radius-8, text=f'#{i+1} {label}', fill=color, font=(FONT, 8, 'bold'))
        c.create_text(12, 10, anchor='nw', text='IMAGE SOURCE / 右键确认球号或添加球位', fill='#7d9273', font=(FONT, 8))

    def image_context_menu(self, event):
        if self.view != 'source' or self.calibrating or self.image_rect is None:
            return
        frame = self.controller.source.capture()
        if frame.source != 'image':
            return
        x, y, w, h = self.image_rect
        point = Point((event.x-x)/w*frame.width, (event.y-y)/h*frame.height)
        if not (0 <= point.x < frame.width and 0 <= point.y < frame.height):
            return
        detections = self.controller.result.detections if self.controller.result else ()
        hits = [(point.distance(d.center), i) for i, d in enumerate(detections) if point.distance(d.center) <= max(d.radius, 7/w*frame.width)]
        index = min(hits)[1] if hits else None
        if index is not None and detections[index].kind == 'pocket':
            self.coordinate_text.configure(text=f'球洞 · 原图像素 ({point.x:.0f}, {point.y:.0f})；不参与障碍球计算')
            return
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label='确认候选球号' if index is not None else '在此位置添加球', state='disabled')
        for number in [None, *range(16)]:
            label = '未知球 / 仅作障碍物' if number is None else ('母球 (0)' if number == 0 else f'{number} 号球')
            def select(value=number):
                if index is None:
                    self.controller.add_image_ball(point, value)
                else:
                    self.controller.label_image_ball(index, value)
                self.run_pipeline()
                self.log('Annotation', '已更新图片球位，球号由人工确认')
            menu.add_command(label=label, command=select)
        if index is not None:
            menu.add_separator()
            def remove():
                self.controller.remove_image_ball(index)
                self.run_pipeline()
            menu.add_command(label='移除误检候选', command=remove)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def start_calibration(self):
        if self.image_original is None:
            self.import_image()
        if self.image_original is None:
            return
        self.view = 'source'
        self.view_button.configure(text='数字球桌')
        self.calibrating = True
        self.points = []
        self.canvas.configure(cursor='crosshair')
        self.coordinate_text.configure(text='请点选左上角 (1/4)，Esc 取消')
        self.draw()

    def cancel_calibration(self):
        self.calibrating = False
        if hasattr(self, 'canvas'):
            self.canvas.configure(cursor='')
            self.coordinate_text.configure(text='点击球位查看球桌坐标')

    def canvas_click(self, event):
        if self.view == 'digital':
            ball = self.renderer.hit(event.x, event.y)
            if ball is not None:
                self.selected_ball = ball
                self.coordinate_text.configure(text=f'{"母球" if ball.number == 0 else ("未知球" if ball.number is None else str(ball.number)+" 号球")}  X={ball.center.x:.1f}, Y={ball.center.y:.1f} mm')
                self.draw()
            return
        if not self.calibrating or self.image_rect is None:
            return
        x, y, w, h = self.image_rect
        px, py = (event.x-x)/w, (event.y-y)/h
        if not (0 <= px <= 1 and 0 <= py <= 1):
            return
        self.points.append([px, py])
        if len(self.points) == 4:
            try:
                validate_quad(self.points)
                c = self.controller.config
                transform = TableTransform(self.points, c.table_width, c.table_height)
                self.controller.set_calibration(self.points)
                self.run_pipeline()
                self.log('Calibration', '单应矩阵已由 Python 求解并保存：' + ', '.join(f'{v:.3g}' for v in transform.h))
            except (ValueError, OSError) as error:
                self.log('Calibration', f'标定失败：{error}')
                messagebox.showerror('标定失败', str(error), parent=self)
            self.cancel_calibration()
        else:
            self.coordinate_text.configure(text=f'请点选{["左上", "右上", "右下", "左下"][len(self.points)]}角 ({len(self.points)+1}/4)，Esc 取消')
        self.draw()

    def export(self):
        path = filedialog.asksaveasfilename(parent=self, title='导出 Python 项目配置', initialdir=str(self.controller.path.parent), initialfile='eight-ball-config.json', defaultextension='.json', filetypes=[('JSON', '*.json')])
        if not path:
            return
        try:
            self.controller.config.save(Path(path))
            result = self.controller.result
            self.log('Export', f'已导出配置到 {path}；融合状态：{result.fused if result else False}')
        except (ValueError, OSError) as error:
            messagebox.showerror('导出失败', str(error), parent=self)
