import math
import time
import tkinter as tk
from tkinter import ttk, messagebox


APP_TITLE = "Растровые алгоритмы"
COORD_LIMIT = 200
RADIUS_LIMIT = 200
ZOOM_MIN = 1.5
ZOOM_MAX = 60.0

LINE_ALGORITHMS = ("Пошаговый", "ЦДА", "Брезенхем")
ALL_ALGORITHMS = "Все алгоритмы"
COLORS = {
    "Пошаговый": "#d97706",
    "ЦДА": "#16845b",
    "Брезенхем": "#2563b9",
    "Брезенхем (окружность)": "#7c3aed",
    "Кастл — Питвей": "#e11d48",
}


def round_half_away(value):
    tolerance = 1e-10
    if value >= 0:
        return int(math.floor(value + 0.5 + tolerance))
    return int(math.ceil(value - 0.5 - tolerance))


def raster_step(x0, y0, x1, y1):
    dx = x1 - x0
    dy = y1 - y0
    adx = abs(dx)
    ady = abs(dy)
    if adx == 0 and ady == 0:
        return [(x0, y0)]
    points = []
    if adx >= ady:
        direction = 1 if dx >= 0 else -1
        for i in range(adx + 1):
            x = x0 + direction * i
            y = round_half_away(y0 + dy * i / float(adx))
            points.append((x, y))
    else:
        direction = 1 if dy >= 0 else -1
        for i in range(ady + 1):
            y = y0 + direction * i
            x = round_half_away(x0 + dx * i / float(ady))
            points.append((x, y))
    points[0] = (x0, y0)
    points[-1] = (x1, y1)
    return points


def raster_dda(x0, y0, x1, y1):
    dx = x1 - x0
    dy = y1 - y0
    steps = max(abs(dx), abs(dy))
    if steps == 0:
        return [(x0, y0)]
    x_step = dx / float(steps)
    y_step = dy / float(steps)
    points = []
    for i in range(steps + 1):
        points.append((round_half_away(x0 + i * x_step), round_half_away(y0 + i * y_step)))
    points[0] = (x0, y0)
    points[-1] = (x1, y1)
    return points

def raster_castle_pitway(x0, y0, x1, y1, x2, y2):
  dx1 = x1 - x0
  dy1 = y1 - y0
  dx2 = x2 - x0
  dy2 = y2 - y0

  span = max(abs(dx1), abs(dy1), abs(dx2), abs(dy2))
  steps = max(1, span * 2)

  points = []
  prev = None
  for i in range(steps + 1):
    t = i / float(steps)
    inv_t = 1.0 - t
    wx = inv_t * inv_t * 0.0 + 2.0 * inv_t * t * dx1 + t * t * dx2
    wy = inv_t * inv_t * 0.0 + 2.0 * inv_t * t * dy1 + t * t * dy2
    px = x0 + round_half_away(wx)
    py = y0 + round_half_away(wy)
    pt = (px, py)
    if pt != prev:
      points.append(pt)
      prev = pt
  return points

def raster_bresenham(x0, y0, x1, y1):
    reverse = (x0, y0) > (x1, y1)
    if reverse:
        x0, y0, x1, y1 = x1, y1, x0, y0
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    error = dx + dy
    x = x0
    y = y0
    points = []
    while True:
        points.append((x, y))
        if x == x1 and y == y1:
            break
        twice_error = 2 * error
        if twice_error >= dy:
            error += dy
            x += sx
        if twice_error <= dx:
            error += dx
            y += sy
    if reverse:
        points.reverse()
    return points


def raster_circle(cx, cy, radius):
    if radius < 0:
        raise ValueError("Радиус не может быть отрицательным")
    x = 0
    y = radius
    decision = 3 - 2 * radius
    points = []
    seen = set()
    while x <= y:
        symmetric = (
            (cx + x, cy + y),
            (cx - x, cy + y),
            (cx + x, cy - y),
            (cx - x, cy - y),
            (cx + y, cy + x),
            (cx - y, cy + x),
            (cx + y, cy - x),
            (cx - y, cy - x),
        )
        for point in symmetric:
            if point not in seen:
                seen.add(point)
                points.append(point)
        if decision < 0:
            decision += 4 * x + 6
        else:
            decision += 4 * (x - y) + 10
            y -= 1
        x += 1
    return points


def benchmark(function, args, repetitions=1200):
    started = time.perf_counter()
    count = 0
    for unused in range(repetitions):
        result = function(*args)
        count = len(result)
    elapsed = time.perf_counter() - started
    return (elapsed * 1000000.0 / repetitions, count)


def parse_integer(value, field_name, minimum, maximum):
    raw = value.strip()
    if not raw or raw in ("+", "-"):
        raise ValueError("Поле «%s»: введите целое число" % field_name)
    digits = raw[1:] if raw[0] in "+-" else raw
    if not digits.isdigit():
        raise ValueError("Поле «%s»: нужно целое число" % field_name)
    number = int(raw)
    if number < minimum or number > maximum:
        raise ValueError("Поле «%s»: диапазон от %d до %d" % (field_name, minimum, maximum))
    return number


class RasterLabApp(object):
    def _screen_to_world(self, px, py):
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        left, right, top, bottom = 48.0, width - 18.0, 16.0, height - 38.0
        center_x = (left + right) / 2.0
        center_y = (top + bottom) / 2.0
        wx = self.view_x + (px - center_x) / self.zoom
        wy = self.view_y - (py - center_y) / self.zoom
        return wx, wy

    def _start_freehand(self, event):
        if not self.freehand_enabled.get():
            return
        pt = self._screen_to_world(event.x, event.y)
        self.freehand_raw = [pt]
        self.freehand_smooth = [pt]
        self.freehand_drawing = True
        self.redraw()

    def _draw_freehand(self, event):
        if not self.freehand_drawing or not self.freehand_enabled.get():
            return
        pt = self._screen_to_world(event.x, event.y)
        self.freehand_raw.append(pt)
        window = 5
        recent = self.freehand_raw[-window:]
        sx_val = sum(p[0] for p in recent) / float(len(recent))
        sy_val = sum(p[1] for p in recent) / float(len(recent))
        self.freehand_smooth.append((sx_val, sy_val))
        self.redraw()

    def _end_freehand(self, event):
        self.freehand_drawing = False

    def _draw_freehand_line(self, sx, sy):
        if len(self.freehand_smooth) < 2:
            return
        coords = []
        for wx, wy in self.freehand_smooth:
            coords.extend((sx(wx), sy(wy)))
        self.canvas.create_line(
            *coords,
            fill="#dc2626",
            width=2.5,
            smooth=True,
            splinesteps=12,
        )

    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1240x820")
        self.root.minsize(980, 680)
        self.root.option_add("*Font", ("Segoe UI", 10))
        self.root.option_add("*TCombobox*Listbox.Font", ("Segoe UI", 10))

        self.mode = tk.StringVar(value="line")
        self.algorithm = tk.StringVar(value="Брезенхем")
        self.line_values = {
            "x0": tk.StringVar(value="2"),
            "y0": tk.StringVar(value="2"),
            "x1": tk.StringVar(value="8"),
            "y1": tk.StringVar(value="5"),
        }
        self.circle_values = {
            "cx": tk.StringVar(value="0"),
            "cy": tk.StringVar(value="0"),
            "r": tk.StringVar(value="5"),
        }
        self.curve_values = {
            "x0": tk.StringVar(value="0"),
            "y0": tk.StringVar(value="0"),
            "x1": tk.StringVar(value="4"),
            "y1": tk.StringVar(value="8"),
            "x2": tk.StringVar(value="8"),
            "y2": tk.StringVar(value="0"),
        }
        self.zoom = 28.0
        self.view_x = 0.0
        self.view_y = 0.0
        self.current_sets = {}
        self.current_mode = "line"
        self.current_data = None
        self.drag_origin = None
        self.canvas_geometry = None

        self.freehand_enabled = tk.BooleanVar(value=False)
        self.freehand_raw = []
        self.freehand_smooth = []
        self.freehand_drawing = False

        self._build_style()
        self._build_layout()
        self._set_mode_widgets()
        self.draw_current(fit=True, show_errors=False)

    def _build_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#f4f6f9")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f4f6f9", foreground="#202938")
        style.configure("Panel.TLabel", background="#ffffff", foreground="#202938")
        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"), background="#ffffff", foreground="#172033")
        style.configure("Section.TLabelframe", background="#ffffff")
        style.configure("Section.TLabelframe.Label", background="#ffffff", foreground="#374151", font=("Segoe UI", 9, "bold"))
        style.configure("TButton", padding=(9, 6))
        style.configure("Accent.TButton", padding=(10, 7), font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", rowheight=24, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("TRadiobutton", background="#ffffff")
        style.configure("TCheckbutton", background="#ffffff")

    def _build_layout(self):
        self.root.configure(background="#f4f6f9")
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        self.panel_shell = ttk.Frame(outer, style="Panel.TFrame", width=300)
        self.panel_shell.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        self.panel_shell.grid_propagate(False)
        self.panel_shell.configure(width=300)
        self.panel_shell.rowconfigure(0, weight=1)
        self.panel_shell.columnconfigure(0, weight=1)
        self.panel_canvas = tk.Canvas(self.panel_shell, background="#ffffff", highlightthickness=0, borderwidth=0, width=280)
        self.panel_canvas.grid(row=0, column=0, sticky="nsew")
        self.panel_scrollbar = ttk.Scrollbar(self.panel_shell, orient=tk.VERTICAL, command=self.panel_canvas.yview)
        self.panel_scrollbar.grid(row=0, column=1, sticky="ns")
        self.panel_canvas.configure(yscrollcommand=self.panel_scrollbar.set)
        self.panel = ttk.Frame(self.panel_canvas, style="Panel.TFrame", padding=14)
        self.panel_window = self.panel_canvas.create_window((0, 0), window=self.panel, anchor="nw")
        self.panel.bind("<Configure>", self._panel_content_changed)
        self.panel_canvas.bind("<Configure>", self._panel_canvas_resized)

        self.workspace = ttk.Frame(outer, style="Panel.TFrame", padding=10)
        self.workspace.grid(row=0, column=1, sticky="nsew")
        self.workspace.rowconfigure(2, weight=1)
        self.workspace.columnconfigure(0, weight=1)

        ttk.Label(self.panel, text="Параметры", style="Title.TLabel").pack(anchor="w", pady=(0, 12))

        mode_frame = ttk.LabelFrame(self.panel, text="Режим", style="Section.TLabelframe", padding=8)
        mode_frame.pack(fill=tk.X, pady=(0, 9))
        ttk.Radiobutton(
            mode_frame,
            text="Кривая (Кастл — Питвей)",
            variable=self.mode,
            value="curve",
            command=self._set_mode_widgets,
        ).pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="Отрезок", variable=self.mode, value="line", command=self._set_mode_widgets).pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="Окружность", variable=self.mode, value="circle", command=self._set_mode_widgets).pack(anchor="w")

        algo_frame = ttk.Frame(self.panel, style="Panel.TFrame")
        algo_frame.pack(fill=tk.X, pady=(0, 9))
        ttk.Label(algo_frame, text="Алгоритм", style="Panel.TLabel").pack(anchor="w", pady=(0, 4))
        self.algo_combo = ttk.Combobox(algo_frame, textvariable=self.algorithm, state="readonly", values=LINE_ALGORITHMS + (ALL_ALGORITHMS,))
        self.algo_combo.pack(fill=tk.X)
        self.algo_combo.bind("<<ComboboxSelected>>", self._algorithm_changed)

        self.fields_container = ttk.Frame(self.panel, style="Panel.TFrame")
        self.fields_container.pack(fill=tk.X, pady=(0, 9))
        self.line_frame = ttk.LabelFrame(self.fields_container, text="Координаты отрезка", style="Section.TLabelframe", padding=8)
        self._add_entry(self.line_frame, "A x", self.line_values["x0"], 0, 0)
        self._add_entry(self.line_frame, "A y", self.line_values["y0"], 0, 1)
        self._add_entry(self.line_frame, "B x", self.line_values["x1"], 1, 0)
        self._add_entry(self.line_frame, "B y", self.line_values["y1"], 1, 1)

        self.circle_frame = ttk.LabelFrame(self.fields_container, text="Параметры окружности", style="Section.TLabelframe", padding=8)
        self._add_entry(self.circle_frame, "Центр x", self.circle_values["cx"], 0, 0)
        self._add_entry(self.circle_frame, "Центр y", self.circle_values["cy"], 0, 1)
        self._add_entry(self.circle_frame, "Радиус", self.circle_values["r"], 1, 0)
        self.curve_frame = ttk.LabelFrame(
            self.fields_container,
            text="Опорные точки кривой",
            style="Section.TLabelframe",
            padding=8,
        )
        self._add_entry(
            self.curve_frame, "P0 x", self.curve_values["x0"], 0, 0
        )
        self._add_entry(
            self.curve_frame, "P0 y", self.curve_values["y0"], 0, 1
        )
        self._add_entry(
            self.curve_frame, "P1 x", self.curve_values["x1"], 1, 0
        )
        self._add_entry(
            self.curve_frame, "P1 y", self.curve_values["y1"], 1, 1
        )
        self._add_entry(
            self.curve_frame, "P2 x", self.curve_values["x2"], 2, 0
        )
        self._add_entry(
            self.curve_frame, "P2 y", self.curve_values["y2"], 2, 1
        )

        action_frame = ttk.Frame(self.panel, style="Panel.TFrame")
        action_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(action_frame, text="Построить", style="Accent.TButton", command=self.draw_current).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(action_frame, text="Замерить", command=self.run_benchmark).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        zoom_frame = ttk.LabelFrame(self.panel, text="Масштаб", style="Section.TLabelframe", padding=8)
        zoom_frame.pack(fill=tk.X, pady=(0, 9))
        zoom_row = ttk.Frame(zoom_frame, style="Panel.TFrame")
        zoom_row.pack(fill=tk.X)
        ttk.Button(zoom_row, text="−", width=3, command=lambda: self.change_zoom(1.0 / 1.2)).pack(side=tk.LEFT)
        self.zoom_label = ttk.Label(zoom_row, text="28 px/ед.", style="Panel.TLabel", anchor="center")
        self.zoom_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(zoom_row, text="+", width=3, command=lambda: self.change_zoom(1.2)).pack(side=tk.RIGHT)
        self.zoom_scale = ttk.Scale(zoom_frame, from_=ZOOM_MIN, to=ZOOM_MAX, orient=tk.HORIZONTAL, command=self._zoom_changed)
        self.zoom_scale.set(self.zoom)
        self.zoom_scale.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(zoom_frame, text="Вписать рисунок", command=self.fit_current).pack(fill=tk.X, pady=(6, 0))

        self.stats_frame = ttk.LabelFrame(self.panel, text="Результат", style="Section.TLabelframe", padding=7)
        self.stats_frame.pack(fill=tk.X, pady=(0, 9))
        self.stats = ttk.Treeview(self.stats_frame, columns=("name", "count", "time"), show="headings", height=4)
        self.stats.heading("name", text="Метод")
        self.stats.heading("count", text="Точек")
        self.stats.heading("time", text="мкс")
        self.stats.column("name", width=132, anchor="w", stretch=True)
        self.stats.column("count", width=46, anchor="center", stretch=False)
        self.stats.column("time", width=58, anchor="center", stretch=False)
        self.stats.pack(fill=tk.X)
        self.stats_label = ttk.Label(self.stats_frame, text="", style="Panel.TLabel", wraplength=250, justify=tk.LEFT)
        self.stats_label.pack(anchor="w", pady=(5, 0))

        header = ttk.Frame(self.workspace, style="Panel.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Поле растрирования", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Перетаскивание — обзор · колесо — масштаб", style="Panel.TLabel").grid(row=0, column=1, sticky="e")

        self.legend_frame = ttk.Frame(self.workspace, style="Panel.TFrame")
        self.legend_frame.grid(row=1, column=0, sticky="w", pady=(0, 5))
        self.canvas = tk.Canvas(self.workspace, background="#ffffff", highlightthickness=1, highlightbackground="#d6dce5", borderwidth=0)
        self.canvas.grid(row=2, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self._canvas_resized)
        self.canvas.bind("<ButtonPress-1>", self._start_pan)
        self.canvas.bind("<B1-Motion>", self._pan)
        self.canvas.bind("<MouseWheel>", self._mousewheel)
        self.canvas.bind("<Button-4>", lambda event: self._mousewheel_step(event, 1))
        self.canvas.bind("<Button-5>", lambda event: self._mousewheel_step(event, -1))
        self.canvas.bind("<ButtonPress-3>", self._start_freehand)
        self.canvas.bind("<B3-Motion>", self._draw_freehand)
        self.canvas.bind("<ButtonRelease-3>", self._end_freehand)

        self.footer_var = tk.StringVar(value="Координаты задают центры ячеек; границы: ±0,5.")
        footer = ttk.Label(self.workspace, textvariable=self.footer_var, style="Panel.TLabel", anchor="w")
        footer.grid(row=3, column=0, sticky="ew", pady=(7, 0))


    def _add_entry(self, parent, label, variable, row, column):
        cell = ttk.Frame(parent, style="Panel.TFrame")
        cell.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 7, 0), pady=3)
        parent.columnconfigure(column, weight=1)
        ttk.Label(cell, text=label, style="Panel.TLabel").pack(anchor="w")
        entry = ttk.Entry(cell, textvariable=variable, width=10)
        entry.pack(fill=tk.X, pady=(2, 0))
        entry.bind("<Return>", lambda event: self.draw_current())

    def _set_mode_widgets(self):
        mode = self.mode.get()
        self.line_frame.pack_forget()
        self.circle_frame.pack_forget()
        self.curve_frame.pack_forget()

        if mode == "line":
            self.line_frame.pack(fill=tk.X)
            self.algo_combo.configure(
                values=LINE_ALGORITHMS + (ALL_ALGORITHMS,)
            )
            if self.algorithm.get() not in LINE_ALGORITHMS + (ALL_ALGORITHMS,):
                self.algorithm.set("Брезенхем")
        elif mode == "circle":
            self.circle_frame.pack(fill=tk.X)
            self.algo_combo.configure(values=("Брезенхем (окружность)",))
            self.algorithm.set("Брезенхем (окружность)")
        elif mode == "curve":
            self.curve_frame.pack(fill=tk.X)
            self.algo_combo.configure(values=("Кастл — Питвей",))
            self.algorithm.set("Кастл — Питвей")

        self.draw_current(fit=True, show_errors=False)

    def _algorithm_changed(self, event=None):
        self.draw_current(fit=True, show_errors=False)

    def _read_data(self):
        mode = self.mode.get()
        if mode == "line":
            x0 = parse_integer(
                self.line_values["x0"].get(), "A x", -COORD_LIMIT, COORD_LIMIT
            )
            y0 = parse_integer(
                self.line_values["y0"].get(), "A y", -COORD_LIMIT, COORD_LIMIT
            )
            x1 = parse_integer(
                self.line_values["x1"].get(), "B x", -COORD_LIMIT, COORD_LIMIT
            )
            y1 = parse_integer(
                self.line_values["y1"].get(), "B y", -COORD_LIMIT, COORD_LIMIT
            )
            return (x0, y0, x1, y1)
        if mode == "curve":
            x0 = parse_integer(
                self.curve_values["x0"].get(), "P0 x", -COORD_LIMIT, COORD_LIMIT
            )
            y0 = parse_integer(
                self.curve_values["y0"].get(), "P0 y", -COORD_LIMIT, COORD_LIMIT
            )
            x1 = parse_integer(
                self.curve_values["x1"].get(), "P1 x", -COORD_LIMIT, COORD_LIMIT
            )
            y1 = parse_integer(
                self.curve_values["y1"].get(), "P1 y", -COORD_LIMIT, COORD_LIMIT
            )
            x2 = parse_integer(
                self.curve_values["x2"].get(), "P2 x", -COORD_LIMIT, COORD_LIMIT
            )
            y2 = parse_integer(
                self.curve_values["y2"].get(), "P2 y", -COORD_LIMIT, COORD_LIMIT
            )
            return (x0, y0, x1, y1, x2, y2)
        cx = parse_integer(
            self.circle_values["cx"].get(), "Центр x", -COORD_LIMIT, COORD_LIMIT
        )
        cy = parse_integer(
            self.circle_values["cy"].get(), "Центр y", -COORD_LIMIT, COORD_LIMIT
        )
        radius = parse_integer(
            self.circle_values["r"].get(), "Радиус", 0, RADIUS_LIMIT
        )
        return (cx, cy, radius)

    def _calculate(self, data):
        if self.mode.get() == "line":
            x0, y0, x1, y1 = data
            return {
                "Пошаговый": raster_step(x0, y0, x1, y1),
                "ЦДА": raster_dda(x0, y0, x1, y1),
                "Брезенхем": raster_bresenham(x0, y0, x1, y1),
            }
        if self.mode.get() == "curve":
          x0, y0, x1, y1, x2, y2 = data
          return {
              "Кастл — Питвей": raster_castle_pitway(x0, y0, x1, y1, x2, y2)
          }
        cx, cy, radius = data
        return {"Брезенхем (окружность)": raster_circle(cx, cy, radius)}

    def draw_current(self, fit=False, show_errors=True):
        try:
            data = self._read_data()
            sets = self._calculate(data)
        except ValueError as error:
            if show_errors:
                messagebox.showerror("Проверка данных", str(error), parent=self.root)
            return
        self.current_mode = self.mode.get()
        self.current_data = data
        self.current_sets = sets
        if fit:
            self._fit_to_points()
        self._update_stats()
        self._update_legend()
        self.redraw()

    def _visible_algorithms(self):
        if self.current_mode == "circle":
            return list(self.current_sets.keys())
        if self.current_mode == "curve":
            return list(self.current_sets.keys())
        selected = self.algorithm.get()
        if selected == ALL_ALGORITHMS:
            return list(LINE_ALGORITHMS)
        return [selected]

    def _update_legend(self):
        for child in self.legend_frame.winfo_children():
            child.destroy()
        for name in self._visible_algorithms():
            swatch = tk.Label(self.legend_frame, text=" ", background=COLORS[name], width=2, height=1, relief=tk.FLAT)
            swatch.pack(side=tk.LEFT, padx=(0, 3))
            label = ttk.Label(self.legend_frame, text=name, style="Panel.TLabel")
            label.pack(side=tk.LEFT, padx=(0, 12))

    def _update_stats(self):
        for item in self.stats.get_children():
            self.stats.delete(item)
        for name, color in COLORS.items():
            self.stats.tag_configure(name, foreground=color)
        selected = self._visible_algorithms()
        for name in selected:
            count = len(self.current_sets[name])
            self.stats.insert("", tk.END, values=(name, count, "—"), tags=(name,))
        if self.current_mode == "line" and self.algorithm.get() == ALL_ALGORITHMS:
            sets = [set(self.current_sets[name]) for name in LINE_ALGORITHMS]
            common = len(set.intersection(*sets))
            union = len(set.union(*sets))
            self.stats_label.configure(text="Общих: %d · всего: %d" % (common, union))
        else:
            name = selected[0]
            self.stats_label.configure(text="Пикселей: %d" % len(self.current_sets[name]))

    def _fit_to_points(self):
        all_points = []
        for points in self.current_sets.values():
            all_points.extend(points)
        if not all_points:
            self.view_x = 0.0
            self.view_y = 0.0
            self._set_zoom(28.0)
            return
        min_x = min(point[0] for point in all_points)
        max_x = max(point[0] for point in all_points)
        min_y = min(point[1] for point in all_points)
        max_y = max(point[1] for point in all_points)
        self.view_x = (min_x + max_x) / 2.0
        self.view_y = (min_y + max_y) / 2.0
        width = max(self.canvas.winfo_width(), 600)
        height = max(self.canvas.winfo_height(), 400)
        available_width = max(100, width - 100)
        available_height = max(100, height - 90)
        span_x = max(1.0, max_x - min_x + 4.0)
        span_y = max(1.0, max_y - min_y + 4.0)
        fitted = min(available_width / span_x, available_height / span_y, ZOOM_MAX)
        self._set_zoom(max(ZOOM_MIN, fitted))

    def fit_current(self):
        if self.current_sets:
            self._fit_to_points()
            self.redraw()

    def _set_zoom(self, value):
        self.zoom = max(ZOOM_MIN, min(ZOOM_MAX, float(value)))
        self.zoom_scale.set(self.zoom)
        self.zoom_label.configure(text="%.1f px/ед." % self.zoom)

    def _zoom_changed(self, value):
        self.zoom = max(ZOOM_MIN, min(ZOOM_MAX, float(value)))
        self.zoom_label.configure(text="%.1f px/ед." % self.zoom)
        self.redraw()

    def change_zoom(self, factor):
        self._set_zoom(self.zoom * factor)
        self.redraw()

    def _mousewheel(self, event):
        self._zoom_at(1.15 if event.delta > 0 else 1.0 / 1.15, event.x, event.y)

    def _mousewheel_step(self, event, direction):
        self._zoom_at(1.15 if direction > 0 else 1.0 / 1.15, event.x, event.y)

    def _zoom_at(self, factor, px, py):
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        left, right, top, bottom = 48, width - 18, 16, height - 38
        center_x = (left + right) / 2.0
        center_y = (top + bottom) / 2.0
        world_x = self.view_x + (px - center_x) / self.zoom
        world_y = self.view_y - (py - center_y) / self.zoom
        old_zoom = self.zoom
        self._set_zoom(old_zoom * factor)
        self.view_x = world_x - (px - center_x) / self.zoom
        self.view_y = world_y + (py - center_y) / self.zoom
        self.redraw()

    def _start_pan(self, event):
        self.drag_origin = (event.x, event.y, self.view_x, self.view_y)

    def _pan(self, event):
        if self.drag_origin is None:
            return
        old_x, old_y, start_view_x, start_view_y = self.drag_origin
        self.view_x = start_view_x - (event.x - old_x) / self.zoom
        self.view_y = start_view_y + (event.y - old_y) / self.zoom
        self.redraw()

    def _canvas_resized(self, event=None):
        self.redraw()

    def redraw(self):
        if not hasattr(self, "canvas"):
            return
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width < 100 or height < 100:
            return
        self.canvas.delete("all")
        left, right, top, bottom = 48.0, width - 18.0, 16.0, height - 38.0
        center_x = (left + right) / 2.0
        center_y = (top + bottom) / 2.0
        scale = self.zoom

        def sx(x):
            return center_x + (x - self.view_x) * scale

        def sy(y):
            return center_y - (y - self.view_y) * scale

        min_x = self.view_x - (center_x - left) / scale
        max_x = self.view_x + (right - center_x) / scale
        min_y = self.view_y - (bottom - center_y) / scale
        max_y = self.view_y + (center_y - top) / scale

        start_x = int(math.floor(min_x - 0.5))
        end_x = int(math.ceil(max_x - 0.5))
        for coordinate in range(start_x, end_x + 1):
            x = sx(coordinate + 0.5)
            major = (coordinate + 1) % 5 == 0
            self.canvas.create_line(x, top, x, bottom, fill="#e1e6ed" if not major else "#cbd3df", width=1)

        start_y = int(math.floor(min_y - 0.5))
        end_y = int(math.ceil(max_y - 0.5))
        for coordinate in range(start_y, end_y + 1):
            y = sy(coordinate + 0.5)
            major = (coordinate + 1) % 5 == 0
            self.canvas.create_line(left, y, right, y, fill="#e1e6ed" if not major else "#cbd3df", width=1)

        label_step = max(1, int(math.ceil(30.0 / scale)))
        x_first = int(math.ceil(min_x))
        x_last = int(math.floor(max_x))
        for coordinate in range(x_first, x_last + 1):
            if coordinate % label_step == 0:
                x = sx(coordinate)
                self.canvas.create_line(x, bottom - 3, x, bottom + 2, fill="#64748b")
                self.canvas.create_text(x, bottom + 14, text=str(coordinate), fill="#556274", font=("Segoe UI", 8))

        y_first = int(math.ceil(min_y))
        y_last = int(math.floor(max_y))
        for coordinate in range(y_first, y_last + 1):
            if coordinate % label_step == 0:
                y = sy(coordinate)
                self.canvas.create_line(left - 3, y, left + 2, y, fill="#64748b")
                self.canvas.create_text(left - 17, y, text=str(coordinate), fill="#556274", font=("Segoe UI", 8), anchor=tk.E)

        axis_x = sx(0)
        axis_y = sy(0)
        if left <= axis_x <= right:
            self.canvas.create_line(axis_x, top, axis_x, bottom, fill="#64748b", width=2)
            self.canvas.create_text(axis_x + 10, top + 9, text="Y", fill="#334155", font=("Segoe UI", 9, "bold"), anchor=tk.W)
        if top <= axis_y <= bottom:
            self.canvas.create_line(left, axis_y, right, axis_y, fill="#64748b", width=2)
            self.canvas.create_text(right - 8, axis_y - 10, text="X", fill="#334155", font=("Segoe UI", 9, "bold"), anchor=tk.E)
        if left <= axis_x <= right and top <= axis_y <= bottom:
            self.canvas.create_text(axis_x + 8, axis_y + 11, text="0", fill="#334155", font=("Segoe UI", 8, "bold"), anchor=tk.NW)

        self._draw_pixels(sx, sy, scale)
        self.canvas.create_rectangle(left, top, right, bottom, outline="#cbd3df", width=1)

        self._draw_freehand_line(sx, sy)

    def _draw_pixels(self, sx, sy, scale):
        algorithms = self._visible_algorithms()
        if not algorithms:
            return
        memberships = {}
        for name in algorithms:
            for point in self.current_sets.get(name, []):
                memberships.setdefault(point, []).append(name)

        inset = min(1.2, max(0.25, scale * 0.035))
        for point, names in memberships.items():
            x, y = point
            left = sx(x - 0.5) + inset
            right = sx(x + 0.5) - inset
            top = sy(y + 0.5) + inset
            bottom = sy(y - 0.5) - inset
            if len(names) == 1:
                self.canvas.create_rectangle(left, top, right, bottom, fill=COLORS[names[0]], outline=COLORS[names[0]])
            else:
                width = max(0.5, (right - left) / float(len(names)))
                for index, name in enumerate(names):
                    x_left = left + index * width
                    x_right = right if index == len(names) - 1 else left + (index + 1) * width
                    self.canvas.create_rectangle(x_left, top, x_right, bottom, fill=COLORS[name], outline="")
                self.canvas.create_rectangle(left, top, right, bottom, outline="#334155", width=0.6)

        if self.current_mode == "line" and self.current_data:
            x0, y0, x1, y1 = self.current_data
            self._draw_endpoint(sx(x0), sy(y0), "A")
            self._draw_endpoint(sx(x1), sy(y1), "B")
        elif self.current_mode == "circle" and self.current_data:
            cx, cy, radius = self.current_data
            px = sx(cx)
            py = sy(cy)
            self.canvas.create_line(px - 5, py, px + 5, py, fill="#111827", width=1.5)
            self.canvas.create_line(px, py - 5, px, py + 5, fill="#111827", width=1.5)

    def _draw_endpoint(self, x, y, label):
        radius = max(2.5, min(5.0, self.zoom * 0.13))
        self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill="#ffffff", outline="#111827", width=1.2)
        self.canvas.create_text(x + 7, y - 9, text=label, fill="#111827", font=("Segoe UI", 8, "bold"), anchor=tk.SW)

    def run_benchmark(self):
        try:
            data = self._read_data()
        except ValueError as error:
            messagebox.showerror("Проверка данных", str(error), parent=self.root)
            return
        self.draw_current(fit=False, show_errors=False)
        if self.mode.get() == "line":
            algorithms = (
                ("Пошаговый", raster_step),
                ("ЦДА", raster_dda),
                ("Брезенхем", raster_bresenham),
            )
        elif self.mode.get() == "curve":
            algorithms = (("Кастл — Питвей", raster_castle_pitway),)
        else:
            algorithms = (("Брезенхем (окружность)", raster_circle),)
        for item in self.stats.get_children():
            self.stats.delete(item)
        for name, color in COLORS.items():
            self.stats.tag_configure(name, foreground=color)
        result_lines = []
        for name, function in algorithms:
            microseconds, count = benchmark(function, data)
            self.stats.insert("", tk.END, values=(name, count, "%.2f" % microseconds), tags=(name,))
            result_lines.append("%s: %.2f мкс" % (name, microseconds))
        self.stats_label.configure(text=" · ".join(result_lines))

    def _panel_content_changed(self, event=None):
        self.panel_canvas.configure(scrollregion=self.panel_canvas.bbox("all"))

    def _panel_canvas_resized(self, event):
        self.panel_canvas.itemconfigure(self.panel_window, width=event.width)


def main():
    root = tk.Tk()
    RasterLabApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
