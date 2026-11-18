from __future__ import annotations

import argparse
import json
import math
import traceback
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
except Exception:
    raise SystemExit("Ошибка импорта модулей\n" + traceback.format_exc())


TEXT = "BABAYEVA"
TEXTURES = ("Дерево", "Скалк", "Камень", "Вода")


def rotation_x(angle: float) -> np.ndarray:
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]], dtype=float)


def rotation_y(angle: float) -> np.ndarray:
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]], dtype=float)


def rotation_z(angle: float) -> np.ndarray:
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=float)


def transformation_matrix(rx: float, ry: float, rz: float, scale: float, tx: float, ty: float, tz: float) -> np.ndarray:
    scaling = np.diag([scale, scale, scale, 1.0])
    translation = np.array([[1, 0, 0, tx], [0, 1, 0, ty], [0, 0, 1, tz], [0, 0, 0, 1]], dtype=float)
    return translation @ rotation_z(rz) @ rotation_y(ry) @ rotation_x(rx) @ scaling


def locate_font():
    for candidate in [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ]:
        if Path(candidate).exists():
            return candidate
    return None


def make_text_mask(text: str = TEXT, max_width: int = 150, max_height: int = 40) -> np.ndarray:
    font_path = locate_font()
    if font_path:
        font = ImageFont.truetype(font_path, 180)
    else:
        font = ImageFont.load_default()
    probe = Image.new("L", (1800, 360), 0)
    draw = ImageDraw.Draw(probe)
    bounds = draw.textbbox((0, 0), text, font=font, stroke_width=0)
    pad = 18
    crop = Image.new("L", (bounds[2] - bounds[0] + 2 * pad, bounds[3] - bounds[1] + 2 * pad), 0)
    ImageDraw.Draw(crop).text((pad - bounds[0], pad - bounds[1]), text, fill=255, font=font)
    ratio = min(max_width / crop.width, max_height / crop.height)
    size = (max(1, round(crop.width * ratio)), max(1, round(crop.height * ratio)))
    resized = crop.resize(size, Image.Resampling.LANCZOS)
    return np.asarray(resized, dtype=np.uint8) >= 110


def make_texture(name: str, width: int, height: int) -> np.ndarray:
    x = np.linspace(0, 1, width, dtype=float)[None, :]
    y = np.linspace(0, 1, height, dtype=float)[:, None]
    xx = np.broadcast_to(x, (height, width))
    yy = np.broadcast_to(y, (height, width))
    rng = np.random.default_rng(27)
    noise = rng.normal(0, 1, (height, width))

    if name == "Дерево":
        wave = 0.5 + 0.5 * np.sin(2 * np.pi * (1.2 * xx + 0.10 * np.sin(8 * yy)))
        bands = 0.5 + 0.5 * np.sin(2 * np.pi * (13 * yy + 0.8 * xx))
        red = 135 + 90 * wave + 18 * bands + 5 * noise
        green = 66 + 92 * wave + 12 * bands + 3 * noise
        blue = 12 + 42 * wave + 2 * noise
    elif name == "Скалк":
        grid = np.maximum(np.exp(-((np.mod(xx * 11, 1) - 0.04) / 0.035) ** 2),
                          np.exp(-((np.mod(yy * 7, 1) - 0.04) / 0.035) ** 2))
        glow = 0.5 + 0.5 * np.sin(2 * np.pi * (xx * 2.5 + yy * 1.3))
        red = 8 + 55 * grid + 18 * glow + 2 * noise
        green = 24 + 155 * grid + 65 * glow + 4 * noise
        blue = 48 + 175 * grid + 68 * glow + 4 * noise
    elif name == "Камень":
        veins = np.sin(19 * xx + 4 * np.sin(9 * yy) + 1.8 * np.sin(15 * yy + 4 * xx))
        veins = np.clip((veins + 0.35) * 0.62, 0, 1)
        grain = 5 * noise
        red = 105 + 105 * veins + grain
        green = 115 + 105 * veins + grain
        blue = 132 + 105 * veins + grain
    else:
        rings = 0.5 + 0.5 * np.sin(17 * np.sqrt((xx - 0.45) ** 2 + (yy - 0.48) ** 2) + 6 * xx)
        red = 5 + 25 * rings + 2 * noise
        green = 78 + 125 * rings + 4 * noise
        blue = 92 + 142 * rings + 4 * noise

    rgb = np.stack([red, green, blue], axis=-1)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def build_mesh(mask: np.ndarray):
    height, width = mask.shape
    vertex_map: dict[tuple[int, int, int], int] = {}
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    face_types: list[tuple[str, int, int]] = []
    cell = 3.8 / width

    def vertex(c: int, r: int, zside: int) -> int:
        key = (c, r, zside)
        if key not in vertex_map:
            x = (c - width / 2) * cell
            y = -float(zside)
            z = (height / 2 - r) * cell
            vertex_map[key] = len(vertices)
            vertices.append([x, y, z, 1.0])
        return vertex_map[key]

    neighbors = [(-1, 0, "top"), (1, 0, "bottom"), (0, -1, "left"), (0, 1, "right")]
    for r, c in np.argwhere(mask):
        r, c = int(r), int(c)
        faces.append([vertex(c, r, 1), vertex(c + 1, r, 1), vertex(c + 1, r + 1, 1), vertex(c, r + 1, 1)])
        face_types.append(("front", r, c))
        faces.append([vertex(c, r + 1, 0), vertex(c + 1, r + 1, 0), vertex(c + 1, r, 0), vertex(c, r, 0)])
        face_types.append(("back", r, c))
        for dr, dc, side in neighbors:
            rr, cc = r + dr, c + dc
            if 0 <= rr < height and 0 <= cc < width and mask[rr, cc]:
                continue
            if side == "top":
                quad = [(c, r, 1), (c + 1, r, 1), (c + 1, r, 0), (c, r, 0)]
            elif side == "bottom":
                quad = [(c, r + 1, 1), (c + 1, r + 1, 1), (c + 1, r + 1, 0), (c, r + 1, 0)]
            elif side == "left":
                quad = [(c, r, 1), (c, r + 1, 1), (c, r + 1, 0), (c, r, 0)]
            else:
                quad = [(c + 1, r, 1), (c + 1, r + 1, 1), (c + 1, r + 1, 0), (c + 1, r, 0)]
            faces.append([vertex(*p) for p in quad])
            face_types.append(("side", r, c))

    return np.asarray(vertices, dtype=float), np.asarray(faces, dtype=np.int32), np.asarray(face_types, dtype=object)


def color_faces(face_types: np.ndarray, texture: np.ndarray) -> np.ndarray:
    colors = np.empty((len(face_types), 4), dtype=float)
    for i, (kind, row, col) in enumerate(face_types):
        rgb = texture[int(row), int(col)].astype(float) / 255.0
        if kind == "back":
            rgb *= 0.36
        elif kind == "side":
            rgb *= 0.62
        colors[i] = (*np.clip(rgb, 0, 1), 1.0)
    return colors


def parse_vertices(source: str) -> np.ndarray:
    rows: list[list[float]] = []
    column_counts: set[int] = set()
    for line_number, raw_line in enumerate(source.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = [p for p in line.replace(",", " ").replace(";", " ").split() if p]
        if len(parts) not in (3, 4):
            raise ValueError(f"Строка {line_number}: нужно 3 или 4 числа, получено {len(parts)}.")
        values = [float(p) for p in parts]
        if not np.all(np.isfinite(values)):
            raise ValueError(f"Строка {line_number}: NaN/Inf не допускаются.")
        column_counts.add(len(values))
        rows.append(values)

    if not rows:
        raise ValueError("В тексте нет ни одной строки с координатами.")
    if len(column_counts) != 1:
        raise ValueError("Во всех строках должно быть одинаковое число координат (3 или 4).")

    vertices = np.asarray(rows, dtype=float)
    if vertices.shape[1] == 3:
        vertices = np.column_stack((vertices, np.ones(len(vertices), dtype=float)))
    return vertices


class Text3DApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("3D объектс текстурами")
        self.root.geometry("1450x920")
        self.root.minsize(1160, 760)
        self.root.configure(bg="#FFFFFF")

        self.mask = make_text_mask()
        vertices, faces, face_types = build_mesh(self.mask)

        self.initial_vertices = vertices.copy()
        self.initial_faces = faces.copy()
        self.initial_face_types = face_types.copy()

        self.vertices = vertices.copy()
        self.faces = faces.copy()
        self.face_types = face_types.copy()

        self.depth = tk.DoubleVar(value=0.42)
        self.texture_name = tk.StringVar(value="Скалк")
        self.vars = {
            "rx": tk.DoubleVar(value=12), "ry": tk.DoubleVar(value=-8), "rz": tk.DoubleVar(value=0),
            "scale": tk.DoubleVar(value=1.0),
            "tx": tk.DoubleVar(value=0.0), "ty": tk.DoubleVar(value=0.0), "tz": tk.DoubleVar(value=0.0),
        }
        self.values: dict[str, ttk.Label] = {}
        self.scatter = None

        self._build_style()
        self._build_ui()
        self._install_mesh()
        self.update_model()
        self.canvas.mpl_connect("scroll_event", self._on_scroll)

    def _build_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#FFFFFF")
        style.configure("Panel.TFrame", background="#FFFFFF")
        style.configure("TLabel", background="#FFFFFF", foreground="#212121", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#FFFFFF", foreground="#111111", font=("Segoe UI", 18, "bold"))
        style.configure("Section.TLabel", background="#FFFFFF", foreground="#1565C0", font=("Segoe UI", 10, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(9, 6))
        style.configure("TCombobox", padding=5)

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=(18, 14, 18, 8))
        header.pack(fill="x")
        ttk.Label(header, text="3D объект с текстурами", style="Title.TLabel").pack(anchor="w")

        body = ttk.Frame(self.root, padding=(14, 6, 14, 14))
        body.pack(fill="both", expand=True)
        panel = ttk.Frame(body, style="Panel.TFrame", padding=14, width=310)
        panel.pack(side="left", fill="y", padx=(0, 12))
        panel.pack_propagate(False)
        work = ttk.Frame(body, style="Panel.TFrame", padding=10)
        work.pack(side="left", fill="both", expand=True)

        ttk.Label(panel, text="ТЕКСТУРА", style="Section.TLabel").pack(anchor="w", pady=(2, 8))
        combo = ttk.Combobox(panel, textvariable=self.texture_name, values=TEXTURES, state="readonly")
        combo.pack(fill="x", pady=(0, 11))
        combo.bind("<<ComboboxSelected>>", lambda _e: self.change_texture())

        ttk.Label(panel, text="ПОВОРОТ", style="Section.TLabel").pack(anchor="w", pady=(4, 5))
        self._add_scale(panel, "rx", "X", -180, 180, 1, "°")
        self._add_scale(panel, "ry", "Y", -180, 180, 1, "°")
        self._add_scale(panel, "rz", "Z", -180, 180, 1, "°")

        ttk.Label(panel, text="РАЗМЕР И ПОЛОЖЕНИЕ", style="Section.TLabel").pack(anchor="w", pady=(9, 5))
        self._add_scale(panel, "scale", "Масштаб", 0.45, 1.8, 2, "×")
        self._add_scale(panel, "tx", "Сдвиг X", -1.2, 1.2, 2, "")
        self._add_scale(panel, "ty", "Сдвиг Y", -1.2, 1.2, 2, "")
        self._add_scale(panel, "tz", "Сдвиг Z", -1.2, 1.2, 2, "")

        ttk.Label(panel, text="ПАРАМЕТРЫ МЕША", style="Section.TLabel").pack(anchor="w", pady=(9, 5))
        self.depth_label = ttk.Label(panel, text="Глубина: 0.42")
        self.depth_label.pack(anchor="w")
        ttk.Scale(panel, from_=0.12, to=0.9, variable=self.depth, command=self._depth_changed).pack(fill="x", pady=(2, 11))
        
        self.vertex_count_label = ttk.Label(panel, text=f"Вершин: {len(self.vertices)}")
        self.vertex_count_label.pack(anchor="w", pady=(0, 4))
        
        ttk.Button(panel, text="Редактор вершин…", command=self.edit_vertices).pack(fill="x", pady=(0, 7))

        buttons = ttk.Frame(panel, style="Panel.TFrame")
        buttons.pack(fill="x", pady=(9, 0))
        ttk.Button(buttons, text="Сбросить", command=self.reset).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(buttons, text="Сохранить PNG", command=self.save_image).pack(side="left", fill="x", expand=True, padx=(4, 0))

        io_frame = ttk.Frame(panel, style="Panel.TFrame")
        io_frame.pack(fill="x", pady=(8, 0))
        ttk.Button(io_frame, text="Сохранить проект", command=self.save_project).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(io_frame, text="Загрузить проект", command=self.load_project).pack(side="left", fill="x", expand=True, padx=(4, 0))

        ttk.Button(panel, text="Скопировать матрицу", command=self.copy_matrix).pack(fill="x", pady=(8, 0))

        self.figure = Figure(figsize=(9.2, 5.8), dpi=100, facecolor="#FFFFFF")
        self.ax = self.figure.add_subplot(111, projection="3d")
        self._style_axes()
        self.canvas = FigureCanvasTkAgg(self.figure, master=work)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        matrix_frame = ttk.Frame(work, style="Panel.TFrame", padding=(4, 8, 4, 4))
        matrix_frame.pack(fill="x")
        ttk.Label(matrix_frame, text="ИТОГОВАЯ МАТРИЦА ПРЕОБРАЗОВАНИЯ", style="Section.TLabel").pack(anchor="w")
        self.matrix_text = tk.Text(
            matrix_frame, height=6, bg="#F5F5F5", fg="#212121", insertbackground="#000000",
            font=("Consolas", 10), relief="flat", wrap="none", padx=10, pady=8,
            highlightthickness=1, highlightbackground="#E0E0E0",
        )
        self.matrix_text.pack(fill="x", pady=(5, 0))
        self.matrix_text.configure(state="disabled")
        
        self.status = ttk.Label(work, text="Готово", foreground="#555555")
        self.status.pack(anchor="w", pady=(5, 0))

    def _style_axes(self) -> None:
        self.ax.set_facecolor("#FFFFFF")
        self.ax.set_xlim(-2.8, 2.8)
        self.ax.set_ylim(-1.55, 1.55)
        self.ax.set_zlim(-1.5, 1.8)
        self.ax.set_box_aspect((5.6, 3.1, 3.3))
        self.ax.view_init(elev=15, azim=-70)
        self.ax.set_xlabel("X", color="#333333", labelpad=5)
        self.ax.set_ylabel("Y", color="#333333", labelpad=5)
        self.ax.set_zlabel("Z", color="#333333", labelpad=5)
        self.ax.tick_params(colors="#555555", labelsize=8)
        for axis in (self.ax.xaxis, self.ax.yaxis, self.ax.zaxis):
            axis.pane.set_facecolor((0.97, 0.97, 0.97, 1.0))
            axis.pane.set_edgecolor((0.85, 0.85, 0.85, 1.0))
        self.ax.grid(True, color="#E0E0E0")

    def _add_scale(self, parent, key, label, low, high, digits, suffix):
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=label).pack(side="left")
        value_label = ttk.Label(row, text=f"{self.vars[key].get():.{digits}f}{suffix}", foreground="#777777")
        value_label.pack(side="right")
        self.values[key] = value_label
        ttk.Scale(
            parent, from_=low, to=high, variable=self.vars[key],
            command=lambda v, k=key, d=digits, s=suffix: self._slider_changed(k, float(v), d, s),
        ).pack(fill="x", pady=(0, 5))

    def _install_mesh(self) -> None:
        self.texture = make_texture(self.texture_name.get(), self.mask.shape[1], self.mask.shape[0])
        self.face_colors = color_faces(self.face_types, self.texture)
        self.collection = Poly3DCollection(
            [], facecolors=self.face_colors,
            edgecolors="#8A8A8A", linewidths=0.1, zsort="average",
        )
        self.ax.add_collection3d(self.collection)

    def _matrix(self) -> np.ndarray:
        return transformation_matrix(
            self.vars["rx"].get(), self.vars["ry"].get(), self.vars["rz"].get(),
            self.vars["scale"].get(), self.vars["tx"].get(), self.vars["ty"].get(), self.vars["tz"].get(),
        )

    def update_model(self) -> None:
        try:
            if len(self.vertices) == 0:
                self.collection.set_visible(False)
                self.canvas.draw_idle()
                return

            local = self.vertices.copy()
            local[:, 1] *= self.depth.get()
            matrix = self._matrix()
            transformed = (matrix @ local.T).T

            if len(self.faces) > 0 and self.faces.max() < len(transformed):
                self.collection.set_verts(transformed[self.faces, :3])
                self.collection.set_visible(True)
            else:
                self.collection.set_visible(False)

            self._update_matrix_text(matrix)
            self.status.configure(text=f"Вершин: {len(self.vertices)} · граней: {len(self.faces)}")
            self.canvas.draw_idle()
        except Exception:
            raise SystemExit("Ошибка в update_model:\n" + traceback.format_exc())

    def _update_matrix_text(self, matrix: np.ndarray) -> None:
        lines = ["[ " + "   ".join(f"{v: .4f}" for v in row) + " ]" for row in matrix]
        self.matrix_text.configure(state="normal")
        self.matrix_text.delete("1.0", "end")
        self.matrix_text.insert("1.0", "\n".join(lines))
        self.matrix_text.configure(state="disabled")

    def _slider_changed(self, key: str, value: float, digits: int, suffix: str) -> None:
        self.vars[key].set(value)
        self.values[key].configure(text=f"{value:.{digits}f}{suffix}")
        self.update_model()

    def _depth_changed(self, value: str) -> None:
        depth = float(value)
        self.depth_label.configure(text=f"Глубина: {depth:.2f}")
        self.update_model()

    def change_texture(self) -> None:
        self.texture = make_texture(self.texture_name.get(), self.mask.shape[1], self.mask.shape[0])
        self.face_colors = color_faces(self.face_types, self.texture)
        self.collection.set_facecolor(self.face_colors)
        self.canvas.draw_idle()

    def reset(self) -> None:
        defaults = {"rx": 12, "ry": -8, "rz": 0, "scale": 1.0, "tx": 0.0, "ty": 0.0, "tz": 0.0}
        for key, value in defaults.items():
            self.vars[key].set(value)
        self.depth.set(0.42)
        self.depth_label.configure(text="Глубина: 0.42")
        for key, value in defaults.items():
            suffix = "°" if key in ("rx", "ry", "rz") else ("×" if key == "scale" else "")
            digits = 1 if suffix == "°" else 2
            self.values[key].configure(text=f"{value:.{digits}f}{suffix}")
        
        self.vertices = self.initial_vertices.copy()
        self.faces = self.initial_faces.copy()
        self.face_types = self.initial_face_types.copy()
        self.vertex_count_label.configure(text=f"Вершин: {len(self.vertices)}")
        
        self.texture = make_texture(self.texture_name.get(), self.mask.shape[1], self.mask.shape[0])
        self.face_colors = color_faces(self.face_types, self.texture)
        self.collection.set_facecolor(self.face_colors)

        self.ax.view_init(elev=15, azim=-70)
        self.update_model()

    def _on_scroll(self, event) -> None:
        current = self.vars["scale"].get()
        value = min(1.8, max(0.45, current * (1.08 if event.button == "up" else 1 / 1.08)))
        self.vars["scale"].set(value)
        self.values["scale"].configure(text=f"{value:.2f}×")
        self.update_model()

    def copy_matrix(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(" ".join(f"{v:.8f}" for v in row) for row in self._matrix()))
        self.status.configure(text="Матрица скопирована в буфер")

    def save_image(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Сохранить изображение", defaultextension=".png",
            filetypes=[("PNG", "*.png")], initialfile="3d_BABAYEVA.png",
        )
        if not path:
            return
        try:
            self.figure.savefig(path, dpi=180, facecolor=self.figure.get_facecolor(), bbox_inches="tight")
            self.status.configure(text=f"Сохранено: {Path(path).name}")
        except OSError as exc:
            messagebox.showerror("Ошибка", str(exc))

    def save_project(self) -> None:
        """Сохранить полностью всё: текстуру, ползунки, глубину и массив вершин в JSON файл."""
        path = filedialog.asksaveasfilename(
            title="Сохранить проект", defaultextension=".json",
            filetypes=[("JSON проект", "*.json")], initialfile="babayeva_project.json",
        )
        if not path:
            return
        try:
            data = {
                "texture": self.texture_name.get(),
                "sliders": {k: v.get() for k, v in self.vars.items()},
                "depth": self.depth.get(),
                "vertices": self.vertices.tolist(),
                "faces": self.faces.tolist(),
                "face_types": self.face_types.tolist()
            }
            Path(path).write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
            self.status.configure(text=f"Проект сохранен: {Path(path).name}")
        except Exception as exc:
            messagebox.showerror("Ошибка сохранения", str(exc))

    def load_project(self) -> None:
        """Загрузить проект (текстуру, все ползунки, глубину и меш) из JSON файла."""
        path = filedialog.askopenfilename(
            title="Загрузить проект",
            filetypes=[("JSON проекты", "*.json"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            content = Path(path).read_text(encoding="utf-8")
            data = json.loads(content)
            
            # Текстура
            if "texture" in data and data["texture"] in TEXTURES:
                self.texture_name.set(data["texture"])
                self.change_texture()

            # Ползунки
            if "sliders" in data:
                for k, val in data["sliders"].items():
                    if k in self.vars:
                        self.vars[k].set(val)
                        suffix = "°" if k in ("rx", "ry", "rz") else ("×" if k == "scale" else "")
                        digits = 1 if suffix == "°" else 2
                        if k in self.values:
                            self.values[k].configure(text=f"{val:.{digits}f}{suffix}")
            
            # Глубина
            if "depth" in data:
                d = float(data["depth"])
                self.depth.set(d)
                self.depth_label.configure(text=f"Глубина: {d:.2f}")

            # Геометрия
            if "vertices" in data:
                self.vertices = np.array(data["vertices"], dtype=float)
            if "faces" in data:
                self.faces = np.array(data["faces"], dtype=int)
            if "face_types" in data:
                self.face_types = np.array(data["face_types"], dtype=object)

            self.vertex_count_label.configure(text=f"Вершин: {len(self.vertices)}")
            self.face_colors = color_faces(self.face_types, self.texture)
            self.collection.set_facecolor(self.face_colors)

            self.update_model()
            self.status.configure(text=f"Проект загружен: {Path(path).name}")
        except Exception as exc:
            messagebox.showerror("Ошибка загрузки", str(exc))

    def edit_vertices(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Редактор вершин")
        dialog.geometry("850x650")
        dialog.minsize(600, 400)
        dialog.configure(bg="#FFFFFF")
        dialog.transient(self.root)

        outer = ttk.Frame(dialog, style="Panel.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Каждая строка: X Y Z W", style="Section.TLabel").pack(anchor="w", pady=(0, 6))

        editor_frame = ttk.Frame(outer, style="Panel.TFrame")
        editor_frame.pack(fill="both", expand=True)
        
        editor = tk.Text(
            editor_frame, wrap="none", undo=True,
            font=("Consolas", 10), bg="#FFFFFF", fg="#212121",
            insertbackground="#000000", relief="flat", padx=8, pady=8,
            highlightthickness=1, highlightbackground="#E0E0E0",
        )
        y_scroll = ttk.Scrollbar(editor_frame, orient="vertical", command=editor.yview)
        x_scroll = ttk.Scrollbar(editor_frame, orient="horizontal", command=editor.xview)
        editor.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        
        editor.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(0, weight=1)

        editor.insert("1.0", "\n".join(" ".join(f"{v:.6f}" for v in row) for row in self.vertices))

        actions = ttk.Frame(outer, style="Panel.TFrame")
        actions.pack(fill="x", pady=(10, 0))

        def apply_new_vertices() -> None:
            try:
                new_v = parse_vertices(editor.get("1.0", "end-1c"))
            except Exception as exc:
                messagebox.showerror("Ошибка формата", str(exc), parent=dialog)
                return
            self.vertices = new_v
            
            if len(new_v) == len(self.initial_vertices):
                self.faces = self.initial_faces.copy()
                self.face_types = self.initial_face_types.copy()
                self.face_colors = color_faces(self.face_types, self.texture)
                self.collection.set_facecolor(self.face_colors)
            else:
                self.faces = np.empty((0, 4), dtype=int)
                self.face_types = np.empty((0, 3), dtype=object)

            self.vertex_count_label.configure(text=f"Вершин: {len(self.vertices)}")
            self.update_model()
            dialog.destroy()

        ttk.Button(actions, text="Применить", command=apply_new_vertices).pack(side="right")
        ttk.Button(actions, text="Отмена", command=dialog.destroy).pack(side="right", padx=(0, 6))
        dialog.grab_set()


def main() -> None:
    root = tk.Tk()
    Text3DApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()