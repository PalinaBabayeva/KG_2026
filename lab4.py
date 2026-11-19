import math
import random
import statistics
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "Алгоритмы отсечения"
COORD_LIMIT = 10000.0
MAX_SEGMENTS = 1000
MAX_VERTICES = 100
EPS = 1e-10

DEFAULT_SEGMENTS = """-8 0 8 0
-6 -4 6 5
-4 5 5 -3
0 -8 0 8
-7 5 -5 7
2 2 2 2"""
DEFAULT_RECT = (-4.0, -3.0, 4.0, 3.0)
DEFAULT_SUBJECT_POLYGON = "-6,-1; -1,-5; 6,-2; 4,4; -3,5"
DEFAULT_CLIP_POLYGON = "-4,-2; 3,-3; 5,1; 1,4; -3,3"

INSIDE = 0
LEFT = 1
RIGHT = 2
BOTTOM = 4
TOP = 8


def _scale_eps(*values):
    scale = max([1.0] + [abs(float(v)) for v in values])
    return EPS * scale


def _finite_number(value, label="координата"):
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s должна быть числом" % label)
    if not math.isfinite(result):
        raise ValueError("%s должна быть конечным числом" % label)
    if abs(result) > COORD_LIMIT:
        raise ValueError("%s выходит за пределы ±%.0f" % (label, COORD_LIMIT))
    return result


def validate_rectangle(rect):
    if len(rect) != 4:
        raise ValueError("Для прямоугольника нужны xmin, ymin, xmax, ymax")
    xmin, ymin, xmax, ymax = [float(v) for v in rect]
    if not all(math.isfinite(v) and abs(v) <= COORD_LIMIT for v in (xmin, ymin, xmax, ymax)):
        raise ValueError("Координаты окна должны быть конечными и лежать в диапазоне ±%.0f" % COORD_LIMIT)
    if xmax - xmin <= _scale_eps(xmin, xmax) or ymax - ymin <= _scale_eps(ymin, ymax):
        raise ValueError("Окно должно иметь положительную ширину и высоту")
    return xmin, ymin, xmax, ymax


def _cross(ax, ay, bx, by):
    return ax * by - ay * bx


def _orientation(a, b, c):
    return _cross(b[0] - a[0], b[1] - a[1], c[0] - a[0], c[1] - a[1])


def _point_on_segment(p, a, b, eps):
    if abs(_orientation(a, b, p)) > eps:
        return False
    return (min(a[0], b[0]) - eps <= p[0] <= max(a[0], b[0]) + eps and
            min(a[1], b[1]) - eps <= p[1] <= max(a[1], b[1]) + eps)


def _segments_intersect(a, b, c, d, eps):
    o1 = _orientation(a, b, c)
    o2 = _orientation(a, b, d)
    o3 = _orientation(c, d, a)
    o4 = _orientation(c, d, b)
    if ((o1 > eps and o2 < -eps) or (o1 < -eps and o2 > eps)) and ((o3 > eps and o4 < -eps) or (o3 < -eps and o4 > eps)):
        return True
    return (_point_on_segment(c, a, b, eps) or _point_on_segment(d, a, b, eps) or
            _point_on_segment(a, c, d, eps) or _point_on_segment(b, c, d, eps))


def normalize_convex_polygon(vertices):
    points = []
    for index, vertex in enumerate(vertices):
        if len(vertex) != 2:
            raise ValueError("Вершина %d должна содержать две координаты" % (index + 1))
        point = (_finite_number(vertex[0], "x вершины %d" % (index + 1)),
                 _finite_number(vertex[1], "y вершины %d" % (index + 1)))
        if not points or math.hypot(point[0] - points[-1][0], point[1] - points[-1][1]) > _scale_eps(*point, *points[-1]):
            points.append(point)
    if len(points) > 1 and math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1]) <= _scale_eps(*points[0], *points[-1]):
        points.pop()
    if len(points) < 3:
        raise ValueError("У многоугольника должно быть не менее трёх различных вершин")
    changed = True
    while changed and len(points) >= 3:
        changed = False
        cleaned = []
        n = len(points)
        for i in range(n):
            a, b, c = points[(i - 1) % n], points[i], points[(i + 1) % n]
            eps = _scale_eps(*a, *b, *c)
            if abs(_orientation(a, b, c)) <= eps:
                dot = (b[0] - a[0]) * (b[0] - c[0]) + (b[1] - a[1]) * (b[1] - c[1])
                if dot <= eps:
                    changed = True
                    continue
                raise ValueError("В многоугольнике есть вырожденное ребро или возврат по одной прямой")
            cleaned.append(b)
        points = cleaned
    if len(points) < 3:
        raise ValueError("После удаления повторяющихся/лишних вершин многоугольник вырождается")
    scale_eps = _scale_eps(*(coord for point in points for coord in point))
    area2 = sum(points[i][0] * points[(i + 1) % len(points)][1] -
                points[(i + 1) % len(points)][0] * points[i][1] for i in range(len(points)))
    if abs(area2) <= scale_eps:
        raise ValueError("Площадь многоугольника должна быть ненулевой")
    turn_sign = 0
    for i in range(len(points)):
        value = _orientation(points[i - 1], points[i], points[(i + 1) % len(points)])
        if abs(value) <= scale_eps:
            continue
        current = 1 if value > 0 else -1
        if turn_sign and current != turn_sign:
            raise ValueError("Многоугольник не является выпуклым или вершины заданы не по контуру")
        turn_sign = current
    if turn_sign == 0:
        raise ValueError("Невозможно определить направление обхода многоугольника")
    n = len(points)
    for i in range(n):
        a, b = points[i], points[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i or j == (i + 1) % n or (j + 1) % n == i:
                continue
            c, d = points[j], points[(j + 1) % n]
            if _segments_intersect(a, b, c, d, scale_eps):
                raise ValueError("Контур самопересекается или касается несмежных рёбер")
    return tuple(points), (1 if area2 > 0 else -1)


def _compute_outcode(x, y, xmin, ymin, xmax, ymax, tol):
    code = INSIDE
    if x < xmin - tol:
        code |= LEFT
    elif x > xmax + tol:
        code |= RIGHT
    if y < ymin - tol:
        code |= BOTTOM
    elif y > ymax + tol:
        code |= TOP
    return code


def sutherland_cohen(segment, rectangle):
    x0, y0, x1, y1 = [float(v) for v in segment]
    xmin, ymin, xmax, ymax = validate_rectangle(rectangle)
    tol = _scale_eps(x0, y0, x1, y1, xmin, ymin, xmax, ymax)

    orig_x0, orig_y0 = x0, y0
    dx = x1 - x0
    dy = y1 - y0

    code0 = _compute_outcode(x0, y0, xmin, ymin, xmax, ymax, tol)
    code1 = _compute_outcode(x1, y1, xmin, ymin, xmax, ymax, tol)

    for _ in range(16):
        if (code0 | code1) == 0:
            return (x0, y0), (x1, y1)
        if (code0 & code1) != 0:
            return None

        outcode = code0 if code0 != 0 else code1

        if outcode & TOP:
            if abs(dy) <= tol:
                return None
            x = orig_x0 + dx * (ymax - orig_y0) / dy
            y = ymax
        elif outcode & BOTTOM:
            if abs(dy) <= tol:
                return None
            x = orig_x0 + dx * (ymin - orig_y0) / dy
            y = ymin
        elif outcode & RIGHT:
            if abs(dx) <= tol:
                return None
            y = orig_y0 + dy * (xmax - orig_x0) / dx
            x = xmax
        elif outcode & LEFT:
            if abs(dx) <= tol:
                return None
            y = orig_y0 + dy * (xmin - orig_x0) / dx
            x = xmin

        if outcode == code0:
            x0, y0 = x, y
            code0 = _compute_outcode(x0, y0, xmin, ymin, xmax, ymax, tol)
        else:
            x1, y1 = x, y
            code1 = _compute_outcode(x1, y1, xmin, ymin, xmax, ymax, tol)

    return None


def _sutherland_hodgman_normalized(subject_poly, clip_poly, clip_orientation):
    output = list(subject_poly)
    tol = _scale_eps(
        *(c for p in subject_poly for c in p),
        *(c for p in clip_poly for c in p)
    )

    def is_inside(p, edge_a, edge_b):
        return _orientation(edge_a, edge_b, p) * clip_orientation >= -tol

    def intersect_lines(s, e, a, b):
        x1, y1 = s
        x2, y2 = e
        x3, y3 = a
        x4, y4 = b
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) <= tol * tol:
            return e
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    n_clip = len(clip_poly)
    for i in range(n_clip):
        if not output:
            return ()
        edge_a = clip_poly[i]
        edge_b = clip_poly[(i + 1) % n_clip]
        input_list = output
        output = []
        s = input_list[-1]
        for e in input_list:
            e_in = is_inside(e, edge_a, edge_b)
            s_in = is_inside(s, edge_a, edge_b)
            if e_in:
                if not s_in:
                    output.append(intersect_lines(s, e, edge_a, edge_b))
                output.append(e)
            elif s_in:
                output.append(intersect_lines(s, e, edge_a, edge_b))
            s = e

    cleaned = []
    for pt in output:
        if not cleaned or math.hypot(pt[0] - cleaned[-1][0], pt[1] - cleaned[-1][1]) > tol:
            cleaned.append(pt)
    if len(cleaned) > 1 and math.hypot(cleaned[0][0] - cleaned[-1][0], cleaned[0][1] - cleaned[-1][1]) <= tol:
        cleaned.pop()
    if len(cleaned) < 3:
        return ()
    return tuple(cleaned)


def sutherland_hodgman(subject_vertices, clip_vertices):
    subject_poly, _ = normalize_convex_polygon(subject_vertices)
    clip_poly, clip_orientation = normalize_convex_polygon(clip_vertices)
    return _sutherland_hodgman_normalized(subject_poly, clip_poly, clip_orientation)


def parse_segment_text(text):
    segments = []
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        tokens = line.replace(",", " ").replace(";", " ").split()
        if len(tokens) != 4:
            raise ValueError("Строка %d: ожидались четыре координаты" % line_number)
        values = tuple(_finite_number(token, "координата в строке %d" % line_number) for token in tokens)
        segments.append(values)
        if len(segments) > MAX_SEGMENTS:
            raise ValueError("Допускается не более %d отрезков" % MAX_SEGMENTS)
    if not segments:
        raise ValueError("Добавьте хотя бы один отрезок")
    return tuple(segments)


def parse_polygon_text(text):
    vertices = []
    for line_number, raw_line in enumerate(text.replace(";", "\n").splitlines(), 1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        tokens = line.replace(",", " ").split()
        if len(tokens) != 2:
            raise ValueError("Строка %d: ожидались две координаты вершины" % line_number)
        vertices.append((_finite_number(tokens[0], "x вершины"), _finite_number(tokens[1], "y вершины")))
        if len(vertices) > MAX_VERTICES:
            raise ValueError("Допускается не более %d вершин" % MAX_VERTICES)
    polygon, _ = normalize_convex_polygon(vertices)
    return polygon


def _parse_poly_lines(block_lines):
  vertices = []
  for raw in block_lines:
    for part in raw.split(";"):
      part = part.strip()
      if not part:
        continue
      tokens = part.replace(",", " ").split()
      if len(tokens) % 2 != 0:
        raise ValueError("В строке многоугольника должно быть чётное число координат (пары x y)")
      for idx in range(0, len(tokens), 2):
        vertices.append((
            _finite_number(tokens[idx], "x вершины"),
            _finite_number(tokens[idx + 1], "y вершины"),
        ))
        if len(vertices) > MAX_VERTICES:
          raise ValueError("Допускается не более %d вершин" % MAX_VERTICES)
  poly, _ = normalize_convex_polygon(vertices)
  return poly


def read_input_file(path, mode):
  with open(path, "r", encoding="utf-8-sig") as stream:
    raw_lines = [line.split("#", 1)[0].strip() for line in stream]

  if mode == "rect":
    lines = [line for line in raw_lines if line]
    if len(lines) < 2:
      raise ValueError("В файле должны быть хотя бы один отрезок и последняя строка окна (xmin ymin xmax ymax)")
    if len(lines) - 1 > MAX_SEGMENTS:
      raise ValueError("Допускается не более %d отрезков" % MAX_SEGMENTS)

    segments = []
    for idx, line in enumerate(lines[:-1], 1):
      tokens = line.replace(",", " ").replace(";", " ").split()
      if len(tokens) != 4:
        raise ValueError("Строка %d: ожидались 4 координаты отрезка (x1 y1 x2 y2)" % idx)
      segments.append(tuple(_finite_number(t, "координата отрезка") for t in tokens))

    rect_tokens = lines[-1].replace(",", " ").replace(";", " ").split()
    if len(rect_tokens) != 4:
      raise ValueError("Последняя строка: ожидались 4 координаты окна (xmin ymin xmax ymax)")
    rect = validate_rectangle(tuple(_finite_number(t, "координата окна") for t in rect_tokens))
    return tuple(segments), rect

  if mode == "polygon":
    blocks = []
    current = []
    for line in raw_lines:
      if not line:
        if current:
          blocks.append(current)
          current = []
      else:
        current.append(line)
    if current:
      blocks.append(current)

    if len(blocks) == 2:
      subj_poly = _parse_poly_lines(blocks[0])
      clip_poly = _parse_poly_lines(blocks[1])
      return subj_poly, clip_poly

    non_empty = [line for line in raw_lines if line]
    if len(non_empty) == 2:
      subj_poly = _parse_poly_lines([non_empty[0]])
      clip_poly = _parse_poly_lines([non_empty[1]])
      return subj_poly, clip_poly

    raise ValueError(
        "Для многоугольников разделите вершины первого и второго многоугольников пустой строкой "
        "(или запишите каждый многоугольник в отдельной строке)"
    )

  raise ValueError("Неизвестный режим отсечения")

def run_benchmarks():
    rng = random.Random(271828)
    segments = [tuple(rng.uniform(-40, 40) for _ in range(4)) for _ in range(300)]
    rect = (-5.0, -4.0, 6.0, 5.0)
    samples_sc = []
    for _ in range(9):
        t0 = time.perf_counter_ns()
        vis = 0
        for _ in range(150):
            for seg in segments:
                if sutherland_cohen(seg, rect) is not None:
                    vis += 1
        dt = (time.perf_counter_ns() - t0) / 150 / 1000.0
        samples_sc.append((dt, vis // 150))
    med_sc = statistics.median(s[0] for s in samples_sc)
    print("Сазерленд—Коэн: 300 отрезков, видимых %d, %.2f мкс за пакет, %.3f мкс на отрезок" %
          (samples_sc[4][1], med_sc, med_sc / len(segments)))

    subj_poly = ((-6.0, -2.0), (2.0, -6.0), (7.0, 0.0), (3.0, 6.0), (-4.0, 5.0))
    clip_poly = ((-5.0, -3.0), (4.0, -4.0), (7.0, 1.0), (2.0, 6.0), (-4.0, 4.0))
    samples_sh = []
    for _ in range(9):
        t0 = time.perf_counter_ns()
        for _ in range(1500):
            res = sutherland_hodgman(subj_poly, clip_poly)
        dt = (time.perf_counter_ns() - t0) / 1500
        samples_sh.append(dt)
    med_sh = statistics.median(samples_sh)
    print("Сазерленд—Ходжмен (5x5 вершин -> %d вершин): %.3f мкс на многоугольник" %
          (len(res), med_sh / 1000.0))


def run_self_tests():
    rect = (-2.0, -1.0, 6.0, 5.0)
    close = lambda a, b: abs(a - b) < 1e-8
    result = sutherland_cohen((-4, -4, 8, 8), rect)
    assert result is not None and close(result[0][0], -1) and close(result[0][1], -1) and close(result[1][0], 5) and close(result[1][1], 5)
    assert sutherland_cohen((-4, 6, 8, 6), rect) is None
    edge = sutherland_cohen((-5, 5, 8, 5), rect)
    assert edge is not None and close(edge[0][0], -2) and close(edge[1][0], 6)
    tangent = sutherland_cohen((-1, 0, 0, 1), (0, 0, 2, 2))
    assert tangent is not None and close(tangent[0][0], 0) and close(tangent[1][0], 0)
    point_inside = sutherland_cohen((1, 1, 1, 1), rect)
    assert point_inside is not None and point_inside[0] == point_inside[1]
    assert sutherland_cohen((8, 8, 8, 8), rect) is None

    subj = ((-3, -2), (3, -2), (3, 2), (-3, 2))
    clip = ((-2, -3), (2, -3), (2, 3), (-2, 3))
    poly_res = sutherland_hodgman(subj, clip)
    assert len(poly_res) == 4
    xs = sorted(p[0] for p in poly_res)
    ys = sorted(p[1] for p in poly_res)
    assert close(xs[0], -2) and close(xs[-1], 2) and close(ys[0], -2) and close(ys[-1], 2)

    assert sutherland_hodgman(((10, 10), (12, 10), (11, 12)), clip) == ()
    poly_res_rev = sutherland_hodgman(subj, tuple(reversed(clip)))
    assert len(poly_res_rev) == 4
    print("OK: тесты Сазерленда—Коэна и Сазерленда—Ходжмена пройдены успешно")


def _nice_step(value):
    if value <= 0 or not math.isfinite(value):
        return 1.0
    power = 10 ** math.floor(math.log10(value))
    normalized = value / power
    if normalized <= 1:
        factor = 1
    elif normalized <= 2:
        factor = 2
    elif normalized <= 5:
        factor = 5
    else:
        factor = 10
    return factor * power


def _fmt(value):
    if abs(value) < 5e-10:
        value = 0.0
    return ("%.4f" % value).rstrip("0").rstrip(".")


class ClippingApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1320x860")
        self.root.minsize(1040, 700)
        self.root.option_add("*Font", ("Segoe UI", 10))
        self.mode = tk.StringVar(value="rect")
        self.rect_vars = [tk.StringVar(value=_fmt(v)) for v in DEFAULT_RECT]
        self.segments_text = None
        self.subject_poly_text = None
        self.clip_poly_text = None
        self.current_segments = ()
        self.current_subject_poly = ()
        self.current_clip = DEFAULT_RECT
        self.current_results = []
        self.current_poly_result = ()
        self.current_mode = "rect"
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.base_scale = 30.0
        self.drag_origin = None
        self._build_style()
        self._build_ui()
        self.root.after(180, lambda: self.run_clipping(fit=True))

    def _build_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#f3f5f8")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f3f5f8", foreground="#202938")
        style.configure("Panel.TLabel", background="#ffffff", foreground="#202938")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"),
                        background="#ffffff", foreground="#172033")
        style.configure("Sub.TLabel", font=("Segoe UI", 9),
                        background="#ffffff", foreground="#64748b")
        try:
            style.configure("Error.TLabel", font=("Segoe UI", 9, "bold"),
                            background="#ffffff", foreground="#dc2626")
        except tk.TclError:
            pass
        style.configure("TButton", padding=(9, 6))
        style.configure("Accent.TButton", padding=(10, 7),
                        font=("Segoe UI", 10, "bold"))
        style.configure("TLabelframe", background="#ffffff")
        style.configure("TLabelframe.Label", background="#ffffff",
                        foreground="#475569", font=("Segoe UI", 9, "bold"))
        style.configure("TRadiobutton", background="#ffffff")

    def _build_ui(self):
        self.root.configure(background="#f3f5f8")
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)
        left = ttk.Frame(outer, style="Panel.TFrame", padding=14, width=375)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        left.grid_propagate(False)
        right = ttk.Frame(outer, style="Panel.TFrame", padding=10)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        ttk.Label(left, text="Отсечение (Вариант 1)", style="Title.TLabel").pack(anchor="w")
        ttk.Label(left, text="Сазерленд—Коэн и Сазерленд—Ходжмен", style="Sub.TLabel").pack(anchor="w", pady=(2, 12))

        mode_box = ttk.LabelFrame(left, text="Алгоритм", padding=8)
        mode_box.pack(fill=tk.X, pady=(0, 9))
        ttk.Radiobutton(mode_box, text="Сазерленд—Коэн (отрезки)", value="rect", variable=self.mode, command=self._mode_changed).pack(anchor="w", pady=2)
        ttk.Radiobutton(mode_box, text="Сазерленд—Ходжмен (многоугольник)", value="polygon", variable=self.mode, command=self._mode_changed).pack(anchor="w", pady=2)

        self.part1_frame = ttk.Frame(left, style="Panel.TFrame")
        self.part1_frame.pack(fill=tk.BOTH, expand=True)

        segment_box = ttk.LabelFrame(self.part1_frame, text="Отрезки · x₁ y₁ x₂ y₂", padding=8)
        segment_box.pack(fill=tk.BOTH, expand=True, pady=(0, 9))
        self.segments_text = tk.Text(segment_box, height=8, width=34, font=("Consolas", 10), wrap="none", undo=True, relief=tk.SOLID, borderwidth=1)
        self.segments_text.pack(fill=tk.BOTH, expand=True)
        self.segments_text.insert("1.0", DEFAULT_SEGMENTS)

        rect_box = ttk.LabelFrame(self.part1_frame, text="Прямоугольное окно", padding=8)
        rect_box.pack(fill=tk.X, pady=(0, 9))
        rect_grid = ttk.Frame(rect_box, style="Panel.TFrame")
        rect_grid.pack(fill=tk.X)
        for col, label in enumerate(("xmin", "ymin", "xmax", "ymax")):
            ttk.Label(rect_grid, text=label, style="Panel.TLabel").grid(row=0, column=col, padx=3, sticky="w")
            ttk.Entry(rect_grid, textvariable=self.rect_vars[col], width=8, font=("Segoe UI", 10)).grid(row=1, column=col, padx=3, pady=(2, 0), sticky="ew")
            rect_grid.columnconfigure(col, weight=1)

        self.part2_frame = ttk.Frame(left, style="Panel.TFrame")

        subj_box = ttk.LabelFrame(self.part2_frame, text="Отсекаемый выпуклый многоугольник", padding=8)
        subj_box.pack(fill=tk.BOTH, expand=True, pady=(0, 9))
        ttk.Label(subj_box, text="Вершины: x,y; x,y; ...", style="Sub.TLabel").pack(anchor="w", pady=(0, 4))
        self.subject_poly_text = tk.Text(subj_box, height=4, width=34, font=("Consolas", 10), wrap="word", undo=True, relief=tk.SOLID, borderwidth=1)
        self.subject_poly_text.pack(fill=tk.BOTH, expand=True)
        self.subject_poly_text.insert("1.0", DEFAULT_SUBJECT_POLYGON)

        clip_box = ttk.LabelFrame(self.part2_frame, text="Отсекающий выпуклый многоугольник", padding=8)
        clip_box.pack(fill=tk.BOTH, expand=True, pady=(0, 9))
        ttk.Label(clip_box, text="Вершины: x,y; x,y; ...", style="Sub.TLabel").pack(anchor="w", pady=(0, 4))
        self.clip_poly_text = tk.Text(clip_box, height=4, width=34, font=("Consolas", 10), wrap="word", undo=True, relief=tk.SOLID, borderwidth=1)
        self.clip_poly_text.pack(fill=tk.BOTH, expand=True)
        self.clip_poly_text.insert("1.0", DEFAULT_CLIP_POLYGON)

        actions = ttk.Frame(left, style="Panel.TFrame")
        actions.pack(fill=tk.X, pady=(1, 8))
        ttk.Button(actions, text="Загрузить файл", command=self.load_file).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions, text="Экспорт", command=self.export_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="Сбросить", command=self.reset_defaults).pack(side=tk.RIGHT)
        self.run_btn = ttk.Button(left, text="Выполнить отсечение", style="Accent.TButton", command=self.run_clipping)
        self.run_btn.pack(fill=tk.X)

        self.stats_var = tk.StringVar(value="Ожидание расчёта")
        self.stats_label = ttk.Label(left, textvariable=self.stats_var,
                                    style="Sub.TLabel", wraplength=340,
                                    justify=tk.LEFT)
        self.stats_label.pack(anchor="w", pady=(10, 0))
        header = ttk.Frame(right, style="Panel.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Координатное поле", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="Вписать", command=self.fit_view).grid(row=0, column=1, padx=3)
        ttk.Button(header, text="−", width=3, command=lambda: self.zoom_at(0.8)).grid(row=0, column=2, padx=3)
        ttk.Button(header, text="+", width=3, command=lambda: self.zoom_at(1.25)).grid(row=0, column=3, padx=3)

        self.canvas = tk.Canvas(right, background="#fbfcfe", highlightthickness=1, highlightbackground="#d8dee8")
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda event: self.draw())
        self.canvas.bind("<ButtonPress-1>", self._pan_start)
        self.canvas.bind("<B1-Motion>", self._pan_move)
        self.canvas.bind("<MouseWheel>", self._wheel_zoom)
        self.canvas.bind("<Button-4>", lambda event: self._wheel_zoom_factor(1.15, event.x, event.y))
        self.canvas.bind("<Button-5>", lambda event: self._wheel_zoom_factor(1 / 1.15, event.x, event.y))

        legend = ttk.Frame(right, style="Panel.TFrame")
        legend.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self._legend_item(legend, "#2563eb", "Отсекающее окно")
        self._legend_item(legend, "#94a3b8", "Исходный объект")
        self._legend_item(legend, "#16a36a", "Видимая часть")
        ttk.Label(legend, text="Перетаскивание — сдвиг · колёсико — масштаб", style="Sub.TLabel").pack(side=tk.RIGHT)
        self.root.bind("<Configure>", self._root_configure)

    def _legend_item(self, parent, color, text):
        item = ttk.Frame(parent, style="Panel.TFrame")
        item.pack(side=tk.LEFT, padx=(0, 14))
        swatch = tk.Canvas(item, width=18, height=10, bg="#ffffff", highlightthickness=0)
        swatch.pack(side=tk.LEFT, padx=(0, 5))
        swatch.create_line(1, 5, 17, 5, fill=color, width=3)
        ttk.Label(item, text=text, style="Sub.TLabel").pack(side=tk.LEFT)

    def _root_configure(self, event):
        if event.widget is self.root:
            self.root.after_idle(self.draw)

    def _mode_changed(self):
        mode = self.mode.get()
        actions_widget = self.run_btn.master.winfo_children()[-3]
        if mode == "rect":
            self.part2_frame.pack_forget()
            self.part1_frame.pack(fill=tk.BOTH, expand=True, before=actions_widget)
        else:
            self.part1_frame.pack_forget()
            self.part2_frame.pack(fill=tk.BOTH, expand=True, before=actions_widget)
        self.run_clipping(fit=True, silent=True)

    def reset_defaults(self):
        self.mode.set("rect")
        for variable, value in zip(self.rect_vars, DEFAULT_RECT):
            variable.set(_fmt(value))
        self.segments_text.delete("1.0", tk.END)
        self.segments_text.insert("1.0", DEFAULT_SEGMENTS)
        self.subject_poly_text.delete("1.0", tk.END)
        self.subject_poly_text.insert("1.0", DEFAULT_SUBJECT_POLYGON)
        self.clip_poly_text.delete("1.0", tk.END)
        self.clip_poly_text.insert("1.0", DEFAULT_CLIP_POLYGON)
        self._mode_changed()
        self.fit_view()

    def run_clipping(self, fit=False, silent=False):
        mode = self.mode.get()
        try:
            if mode == "rect":
                segments = parse_segment_text(self.segments_text.get("1.0", tk.END))
                clip_region = validate_rectangle(tuple(
                    _finite_number(v.get(), name) for v, name in zip(self.rect_vars, ("xmin", "ymin", "xmax", "ymax"))
                ))
                started = time.perf_counter_ns()
                results = [sutherland_cohen(seg, clip_region) for seg in segments]
                elapsed_us = (time.perf_counter_ns() - started) / 1000.0

                self.current_segments = segments
                self.current_clip = clip_region
                self.current_results = results
                self.current_mode = mode

                visible = sum(item is not None for item in results)
                fully_inside = 0
                partial = 0
                for segment, clipped in zip(segments, results):
                    if clipped is None:
                        continue
                    same_start = math.hypot(clipped[0][0] - segment[0], clipped[0][1] - segment[1]) <= _scale_eps(*segment)
                    same_end = math.hypot(clipped[1][0] - segment[2], clipped[1][1] - segment[3]) <= _scale_eps(*segment)
                    if same_start and same_end:
                        fully_inside += 1
                    else:
                        partial += 1
                self.stats_var.set("Сазерленд—Коэн · Отрезков: %d · Видимых: %d (внутри: %d, отсечено: %d) · Время: %.2f мкс" %
                                   (len(segments), visible, fully_inside, partial, elapsed_us))
            else:
                subj_poly = parse_polygon_text(self.subject_poly_text.get("1.0", tk.END))
                clip_poly = parse_polygon_text(self.clip_poly_text.get("1.0", tk.END))
                started = time.perf_counter_ns()
                poly_result = sutherland_hodgman(subj_poly, clip_poly)
                elapsed_us = (time.perf_counter_ns() - started) / 1000.0

                self.current_subject_poly = subj_poly
                self.current_clip = clip_poly
                self.current_poly_result = poly_result
                self.current_mode = mode

                self.stats_var.set("Сазерленд—Ходжмен · Исходных вершин: %d · Отсекающих: %d · Итоговых вершин: %d · Время: %.2f мкс" %
                                   (len(subj_poly), len(clip_poly), len(poly_result), elapsed_us))
        except ValueError as error:
            self.stats_var.set(
                "Ошибка: %s" % error
            )
            self.stats_label.configure(style="Error.TLabel")
            if not silent:
                messagebox.showerror("Ошибка ввода данных", str(error))
            self.draw()
            return
        self.stats_label.configure(style="Sub.TLabel")
        self.draw(fit=fit)

    def load_file(self):
        path = filedialog.askopenfilename(title="Загрузить исходные данные", filetypes=(("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")))
        if not path:
            return
        try:
            data1, data2 = read_input_file(path, self.mode.get())
        except (OSError, ValueError) as error:
            messagebox.showerror("Ошибка загрузки", str(error))
            return
        if self.mode.get() == "rect":
            self.segments_text.delete("1.0", tk.END)
            self.segments_text.insert("1.0", "\n".join("%s %s %s %s" % tuple(_fmt(v) for v in seg) for seg in data1))
            for variable, value in zip(self.rect_vars, data2):
                variable.set(_fmt(value))
        else:
            self.subject_poly_text.delete("1.0", tk.END)
            self.subject_poly_text.insert("1.0", "; ".join("%s,%s" % (_fmt(p[0]), _fmt(p[1])) for p in data1))
            self.clip_poly_text.delete("1.0", tk.END)
            self.clip_poly_text.insert("1.0", "; ".join("%s,%s" % (_fmt(p[0]), _fmt(p[1])) for p in data2))
        self.run_clipping(fit=True)

    def export_results(self):
        if self.current_mode == "rect" and not self.current_results:
            messagebox.showwarning("Нет результата", "Сначала выполните отсечение")
            return
        if self.current_mode == "polygon" and not self.current_poly_result:
            messagebox.showwarning("Нет результата", "Видимая область многоугольника пуста или не рассчитана")
            return

        path = filedialog.asksaveasfilename(
            title="Сохранить результат отсечения",
            defaultextension=".txt",
            filetypes=(("Текстовые файлы", "*.txt"),),
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as stream:
                if self.current_mode == "rect":
                    for seg in self.current_segments:
                        stream.write(" ".join(_fmt(v) for v in seg) + "\n")
                    xmin, ymin, xmax, ymax = self.current_clip
                    stream.write(" ".join(_fmt(v) for v in (xmin, ymin, xmax, ymax)) + "\n")
                    stream.write("\n# Видимые части отрезков:\n")
                    for result in self.current_results:
                        if result is not None:
                            stream.write("# " + " ".join(
                                _fmt(v) for v in (result[0][0], result[0][1],
                                                result[1][0], result[1][1])
                            ) + "\n")
                else:
                    stream.write("; ".join(
                        "%s,%s" % (_fmt(p[0]), _fmt(p[1]))
                        for p in self.current_subject_poly
                    ) + "\n\n")
                    stream.write("; ".join(
                        "%s,%s" % (_fmt(p[0]), _fmt(p[1]))
                        for p in self.current_clip
                    ) + "\n")
                    if self.current_poly_result:
                        stream.write("\n# Результат отсечения:\n# ")
                        stream.write("; ".join(
                            "%s,%s" % (_fmt(p[0]), _fmt(p[1]))
                            for p in self.current_poly_result
                        ) + "\n")
        except OSError as error:
            messagebox.showerror("Ошибка сохранения", str(error))
            return

        self.stats_var.set(self.stats_var.get() + " · Сохранено")

    def _world_bounds(self):
        xs = []
        ys = []
        if self.current_mode == "rect":
            for segment in self.current_segments:
                xs.extend((segment[0], segment[2]))
                ys.extend((segment[1], segment[3]))
            xmin, ymin, xmax, ymax = self.current_clip
            xs.extend((xmin, xmax))
            ys.extend((ymin, ymax))
        else:
            for x, y in self.current_subject_poly:
                xs.append(x)
                ys.append(y)
            for x, y in self.current_clip:
                xs.append(x)
                ys.append(y)
        if not xs:
            return -10, -10, 10, 10
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        dx = max(1.0, xmax - xmin)
        dy = max(1.0, ymax - ymin)
        margin_x = dx * 0.12
        margin_y = dy * 0.12
        return xmin - margin_x, ymin - margin_y, xmax + margin_x, ymax + margin_y

    def fit_view(self):
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.draw(fit=True)

    def zoom_at(self, factor):
        self._wheel_zoom_factor(factor, self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2)

    def _wheel_zoom(self, event):
        self._wheel_zoom_factor(1.15 if event.delta > 0 else 1 / 1.15, event.x, event.y)

    def _wheel_zoom_factor(self, factor, x, y):
        old = self.zoom
        new = min(12.0, max(0.12, old * factor))
        if abs(new - old) < 1e-12:
            return
        self.pan_x = x - (x - self.pan_x) * (new / old)
        self.pan_y = y - (y - self.pan_y) * (new / old)
        self.zoom = new
        self.draw()

    def _pan_start(self, event):
        self.drag_origin = (event.x, event.y, self.pan_x, self.pan_y)

    def _pan_move(self, event):
        if self.drag_origin is None:
            return
        x, y, pan_x, pan_y = self.drag_origin
        self.pan_x = pan_x + event.x - x
        self.pan_y = pan_y + event.y - y
        self.draw()

    def _transform(self, x, y):
        return self.canvas_center_x + self.pan_x + x * self.scale, self.canvas_center_y + self.pan_y - y * self.scale

    def draw(self, fit=False):
        if not hasattr(self, "canvas"):
            return
        width = max(2, self.canvas.winfo_width())
        height = max(2, self.canvas.winfo_height())
        self.canvas.delete("all")
        self.canvas_center_x = width / 2
        self.canvas_center_y = height / 2
        xmin, ymin, xmax, ymax = self._world_bounds()
        if fit or not hasattr(self, "scale"):
            scale_x = (width - 110) / max(1e-9, xmax - xmin)
            scale_y = (height - 110) / max(1e-9, ymax - ymin)
            self.base_scale = min(80.0, max(2.0, min(scale_x, scale_y)))
            self.pan_x = 0.0
            self.pan_y = 0.0
        self.scale = self.base_scale * self.zoom
        self._draw_grid(width, height)

        if self.current_mode == "rect":
            x0, y0, x1, y1 = self.current_clip
            coords = [self._transform(x0, y0), self._transform(x1, y0), self._transform(x1, y1), self._transform(x0, y1)]
            flat = [value for pair in coords for value in pair]
            self.canvas.create_polygon(*flat, fill="#dbeafe", stipple="gray25", outline="#2563eb", width=2)
            for index, segment in enumerate(self.current_segments):
                sx0, sy0, sx1, sy1 = segment
                a = self._transform(sx0, sy0)
                b = self._transform(sx1, sy1)
                self.canvas.create_line(a[0], a[1], b[0], b[1], fill="#94a3b8", width=2, dash=(5, 4), capstyle=tk.ROUND)
                self.canvas.create_oval(a[0] - 2.5, a[1] - 2.5, a[0] + 2.5, a[1] + 2.5, fill="#64748b", outline="")
                self.canvas.create_oval(b[0] - 2.5, b[1] - 2.5, b[0] + 2.5, b[1] + 2.5, fill="#64748b", outline="")
                clipped = self.current_results[index] if index < len(self.current_results) else None
                if clipped is not None:
                    p = self._transform(*clipped[0])
                    q = self._transform(*clipped[1])
                    self.canvas.create_line(p[0], p[1], q[0], q[1], fill="#16a36a", width=4, capstyle=tk.ROUND)
                    self.canvas.create_oval(p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3, fill="#087443", outline="")
                    self.canvas.create_oval(q[0] - 3, q[1] - 3, q[0] + 3, q[1] + 3, fill="#087443", outline="")
        else:
            if len(self.current_clip) >= 3:
                clip_coords = [self._transform(x, y) for x, y in self.current_clip]
                flat_clip = [v for pair in clip_coords for v in pair]
                self.canvas.create_polygon(*flat_clip, fill="#dbeafe", stipple="gray25", outline="#2563eb", width=2)

            if len(self.current_subject_poly) >= 3:
                subj_coords = [self._transform(x, y) for x, y in self.current_subject_poly]
                flat_subj = [v for pair in subj_coords for v in pair]
                self.canvas.create_polygon(*flat_subj, fill="", outline="#94a3b8", width=2, dash=(6, 4))
                for sx, sy in subj_coords:
                    self.canvas.create_oval(sx - 2.5, sy - 2.5, sx + 2.5, sy + 2.5, fill="#64748b", outline="")

            if len(self.current_poly_result) >= 3:
                res_coords = [self._transform(x, y) for x, y in self.current_poly_result]
                flat_res = [v for pair in res_coords for v in pair]
                self.canvas.create_polygon(*flat_res, fill="#bbf7d0", stipple="gray50", outline="#16a36a", width=3.5)
                for rx, ry in res_coords:
                    self.canvas.create_oval(rx - 3.5, ry - 3.5, rx + 3.5, ry + 3.5, fill="#087443", outline="")

        self.canvas.create_text(12, 10, anchor="nw", fill="#64748b", font=("Segoe UI", 9),
                                text="Масштаб: %.1f px/ед. · Сетка привязана к целым координатам" % self.scale)

    def _draw_grid(self, width, height):
        step = _nice_step(70.0 / max(self.scale, 1e-9))
        left_x = (0 - self.canvas_center_x - self.pan_x) / self.scale
        right_x = (width - self.canvas_center_x - self.pan_x) / self.scale
        top_y = (self.canvas_center_y + self.pan_y - 0) / self.scale
        bottom_y = (self.canvas_center_y + self.pan_y - height) / self.scale
        x_start = math.floor(left_x / step) * step
        x_end = math.ceil(right_x / step) * step
        y_start = math.floor(bottom_y / step) * step
        y_end = math.ceil(top_y / step) * step
        count = 0
        value = x_start
        while value <= x_end + step * 1e-7 and count < 1000:
            x, _ = self._transform(value, 0)
            color = "#94a3b8" if abs(value) < step * 1e-8 else "#e7ebf1"
            width_line = 1.4 if abs(value) < step * 1e-8 else 1
            self.canvas.create_line(x, 0, x, height, fill=color, width=width_line)
            if abs(x) < width - 35 and abs(value) > step * 1e-8:
                self.canvas.create_text(x + 3, self.canvas_center_y + self.pan_y + 5, text=_fmt(value), anchor="nw", fill="#8390a3", font=("Segoe UI", 8))
            value += step
            count += 1
        count = 0
        value = y_start
        while value <= y_end + step * 1e-7 and count < 1000:
            _, y = self._transform(0, value)
            color = "#94a3b8" if abs(value) < step * 1e-8 else "#e7ebf1"
            width_line = 1.4 if abs(value) < step * 1e-8 else 1
            self.canvas.create_line(0, y, width, y, fill=color, width=width_line)
            if abs(y) < height - 25 and abs(value) > step * 1e-8:
                self.canvas.create_text(self.canvas_center_x + self.pan_x + 5, y - 3, text=_fmt(value), anchor="sw", fill="#8390a3", font=("Segoe UI", 8))
            value += step
            count += 1
        origin = self._transform(0, 0)
        self.canvas.create_text(origin[0] + 7, origin[1] - 7, text="0", fill="#475569", anchor="sw", font=("Segoe UI", 8, "bold"))


def main():
    if "--self-test" in sys.argv:
        run_self_tests()
        return
    if "--benchmark" in sys.argv:
        run_benchmarks()
        return
    root = tk.Tk()
    ClippingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()