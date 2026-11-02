"""Native Canvas rendering, separate from detection and computation."""
from ..models import Point
from ..computation import pockets

COLORS = {0: '#f8f5e6', 1: '#e6b840', 2: '#487fbe', 3: '#c36759', 4: '#9479ad', 5: '#d59253', 6: '#729766', 7: '#935f58', 8: '#24392f'}


class TableRenderer:
    def __init__(self, canvas):
        self.canvas = canvas
        self.hit_points = []

    def draw(self, result, config, selected=None):
        c = self.canvas
        c.delete('all')
        self.hit_points.clear()
        width, height = max(c.winfo_width(), 10), max(c.winfo_height(), 10)
        if width < 100 or height < 100:
            return
        available_w, available_h = width-100, height-95
        aspect = config.table_width/config.table_height
        tw = min(available_w, available_h*aspect)
        th = tw/aspect
        ox, oy = (width-tw)/2, (height-th)/2
        perspective = config.mode == '3d'

        def xy(p):
            u, v = p.x/config.table_width, p.y/config.table_height
            if perspective:
                return ox+tw*(.12+.76*u+.12*v), oy+th*(.13+.78*v-.06*u)
            return ox+u*tw, oy+v*th

        corners = [xy(Point(x, y)) for x, y in [(0, 0), (config.table_width, 0), (config.table_width, config.table_height), (0, config.table_height)]]
        flat = [value for p in corners for value in p]
        c.create_polygon([v + (6 if i % 2 else 0) for i, v in enumerate(flat)], fill='#cdd8cc', outline='#cdd8cc', width=36, joinstyle='round')
        c.create_polygon(flat, fill='#396f80' if config.blue_cloth else '#3f7562', outline='#3b5541', width=27, joinstyle='round')
        c.create_polygon(flat, fill='', outline='#91a580', width=2)
        if config.show_grid:
            for i in range(1, 10):
                p, q = xy(Point(config.table_width*i/10, 0)), xy(Point(config.table_width*i/10, config.table_height))
                c.create_line(*p, *q, fill='#538371', dash=(1, 7))
            for i in range(1, 5):
                p, q = xy(Point(0, config.table_height*i/5)), xy(Point(config.table_width, config.table_height*i/5))
                c.create_line(*p, *q, fill='#538371', dash=(1, 7))
        pr = max(7, tw*.021)
        for p in pockets(config.table_width, config.table_height):
            x, y = xy(p)
            c.create_oval(x-pr, y-pr, x+pr, y+pr, fill='#162e25', outline='#a0b088', width=2)
        if result and config.show_paths and result.shots:
            shot = result.shots[0]
            cue = next(b for b in result.balls if b.number == 0)
            c.create_line(*xy(cue.center), *xy(shot.ghost), fill='#e7cc7d', width=2, dash=(7, 5), arrow='last')
            c.create_line(*xy(shot.target.center), *xy(shot.pocket), fill='#c1dcab', width=2, dash=(5, 4), arrow='last')
            x, y = xy(shot.ghost)
            r = max(6, tw*config.ball_radius/config.table_width)
            c.create_oval(x-r, y-r, x+r, y+r, outline='#e8dfb2', dash=(3, 3), width=2)
        if result:
            for ball in result.balls:
                x, y = xy(ball.center)
                r = max(7, tw*ball.radius/config.table_width)
                self.hit_points.append((x, y, r+7, ball))
                color = COLORS.get(ball.number if ball.number is None or ball.number < 9 else ball.number-8, '#9ba991')
                c.create_oval(x-r+2, y-r+3, x+r+2, y+r+3, fill='#2c5747', outline='')
                c.create_oval(x-r, y-r, x+r, y+r, fill=color, outline='#cbd6b9' if selected == ball.number else color, width=2)
                if ball.number is not None and ball.number > 8:
                    c.create_arc(x-r, y-r, x+r, y+r, start=0, extent=180, style='chord', fill='#efefdb', outline='')
                if config.show_numbers and ball.number != 0:
                    c.create_oval(x-5, y-5, x+5, y+5, fill='#f4f1df', outline='')
                    c.create_text(x, y, text='?' if ball.number is None else ball.number, fill='#28392f', font=('Segoe UI', 6, 'bold'))
                c.create_oval(x-r*.45, y-r*.65, x-r*.1, y-r*.3, fill='#fff9e4', outline='')
        c.create_text(16, 16, anchor='nw', text='TABLE_01   /   3D 透视示意' if perspective else 'TABLE_01   /   2D DIGITAL TABLE', fill='#7a9077', font=('Consolas', 8))
        c.create_text(16, height-15, anchor='sw', text=f'{config.table_width:g} × {config.table_height:g} mm', fill='#819579', font=('Consolas', 8))
        c.create_text(width-16, height-15, anchor='se', text='母球路径 ┄ 黄色    目标路径 ┄ 绿色', fill='#819579', font=('Microsoft YaHei UI', 8))

    def hit(self, x, y):
        return next((b for bx, by, r, b in self.hit_points if (bx-x)**2+(by-y)**2 <= r*r), None)
