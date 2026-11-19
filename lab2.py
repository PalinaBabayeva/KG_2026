import tkinter as tk
from tkinter import filedialog, ttk
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class Lab2App:

  def __init__(self, root):
    self.root = root
    self.root.title('Обработка и изображений и поэлементные операции')
    self.root.geometry('1500x950')
    self.root.minsize(1200, 800)

    style = ttk.Style()
    style.configure('.', font=('Segoe UI', 15))
    style.configure('Heading.TLabel', font=('Segoe UI', 16, 'bold'))

    self.image_original = None
    self.image_processed = None

    self.create_widgets()

  def create_widgets(self):
    main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
    main_paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    control_frame = ttk.Frame(main_paned, padding=12)
    main_paned.add(control_frame, weight=1)

    display_frame = ttk.Frame(main_paned, padding=12)
    main_paned.add(display_frame, weight=4)

    ttk.Label(
        control_frame, text='Изображение', style='Heading.TLabel'
    ).pack(anchor='w', pady=(0, 6))
    ttk.Button(control_frame, text='Загрузить', command=self.load_image).pack(
        fill=tk.X, pady=4
    )
    ttk.Button(control_frame, text='Тестовое', command=self.load_demo_image).pack(
        fill=tk.X, pady=4
    )

    ttk.Separator(control_frame, orient=tk.HORIZONTAL).pack(
        fill=tk.X, pady=14
    )

    ttk.Label(
        control_frame, text='Гистограмма и контраст', style='Heading.TLabel'
    ).pack(anchor='w', pady=(0, 6))
    self.method_var = tk.StringVar(value='linear')
    ttk.Radiobutton(
        control_frame,
        text='Линейное контрастирование',
        variable=self.method_var,
        value='linear',
    ).pack(anchor='w', pady=3)
    ttk.Radiobutton(
        control_frame,
        text='Эквализация RGB',
        variable=self.method_var,
        value='eq_rgb',
    ).pack(anchor='w', pady=3)
    ttk.Radiobutton(
        control_frame,
        text='Эквализация HSV (V)',
        variable=self.method_var,
        value='eq_hsv',
    ).pack(anchor='w', pady=3)
    ttk.Button(control_frame, text='Применить', command=self.run_part1).pack(
        fill=tk.X, pady=(6, 12)
    )

    ttk.Separator(control_frame, orient=tk.HORIZONTAL).pack(
        fill=tk.X, pady=14
    )
    ttk.Label(
      control_frame, text='Поэлементные операции', style='Heading.TLabel'
    ).pack(anchor='w', pady=(0, 6))
    self.point_var = tk.StringVar(value='invert')
    ttk.Radiobutton(
      control_frame,
      text='Инверсия яркости',
      variable=self.point_var,
      value='invert',
    ).pack(anchor='w', pady=2)
    ttk.Radiobutton(
      control_frame,
      text='Гамма-коррекция',
      variable=self.point_var,
      value='gamma',
    ).pack(anchor='w', pady=2)

    ttk.Label(control_frame, text='Параметр гамма (γ):').pack(
      anchor='w', pady=(6, 0)
    )
    self.gamma_var = tk.DoubleVar(value=1.0)
    gamma_scale = tk.Scale(
      control_frame,
      from_=0.1,
      to=5.0,
      resolution=0.1,
      orient=tk.HORIZONTAL,
      variable=self.gamma_var,
    )
    gamma_scale.pack(fill=tk.X, pady=(0, 6))

    ttk.Button(
      control_frame, text='Выполнить', command=self.run_pointwise
    ).pack(fill=tk.X, pady=(4, 4))

    ttk.Separator(control_frame, orient=tk.HORIZONTAL).pack(
        fill=tk.X, pady=14
    )

    ttk.Button(
        control_frame, text='Гистограммы', command=self.show_histogram_window
    ).pack(fill=tk.X, pady=4)
    ttk.Button(control_frame, text='Сохранить', command=self.save_image).pack(
        fill=tk.X, pady=4
    )

    self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(10, 6))
    self.fig.tight_layout()

    self.canvas_plot = FigureCanvasTkAgg(self.fig, master=display_frame)
    self.canvas_plot.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    self.show_placeholder()

  def show_placeholder(self):
    self.ax1.clear()
    self.ax1.set_title('Исходное')
    self.ax1.axis('off')

    self.ax2.clear()
    self.ax2.set_title('Результат')
    self.ax2.axis('off')

    self.fig.canvas.draw()

  def load_image(self):
    file_path = filedialog.askopenfilename(
        filetypes=[('Images', '*.jpg *.jpeg *.png *.bmp *.tif')]
    )
    if file_path:
      img = cv2.imread(file_path)
      if img is not None:
        self.image_original = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.image_processed = self.image_original.copy()
        self.update_display()

  def load_demo_image(self):
    h, w = 300, 400
    demo = np.linspace(30, 90, w, dtype=np.uint8)
    demo = np.tile(demo, (h, 1))
    noise = np.random.normal(0, 10, (h, w)).astype(np.int16)
    demo = np.clip(demo.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    self.image_original = cv2.cvtColor(demo, cv2.COLOR_GRAY2RGB)
    self.image_processed = self.image_original.copy()
    self.update_display()

  def update_display(self):
    if self.image_original is None:
      return

    self.ax1.clear()
    self.ax1.imshow(self.image_original)
    self.ax1.set_title('Исходное')
    self.ax1.axis('off')

    self.ax2.clear()
    self.ax2.imshow(self.image_processed)
    self.ax2.set_title('Результат')
    self.ax2.axis('off')

    self.fig.tight_layout()
    self.fig.canvas.draw()

  def run_part1(self):
    if self.image_original is None:
      return

    method = self.method_var.get()
    img = self.image_original.copy()

    if method == 'linear':
      if len(img.shape) == 3:
        channels = cv2.split(img)
        res_channels = []
        for ch in channels:
          min_val, max_val = np.min(ch), np.max(ch)
          if max_val > min_val:
            norm = cv2.normalize(
                ch, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX
            )
          else:
            norm = ch
          res_channels.append(norm)
        self.image_processed = cv2.merge(res_channels)
      else:
        min_val, max_val = np.min(img), np.max(img)
        if max_val > min_val:
          self.image_processed = cv2.normalize(
              img, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX
          )
        else:
          self.image_processed = img

    elif method == 'eq_rgb':
      if len(img.shape) == 3:
        channels = cv2.split(img)
        eq_channels = [cv2.equalizeHist(ch) for ch in channels]
        self.image_processed = cv2.merge(eq_channels)
      else:
        self.image_processed = cv2.equalizeHist(img)

    elif method == 'eq_hsv':
      if len(img.shape) == 3:
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        h, s, v = cv2.split(hsv)
        v_eq = cv2.equalizeHist(v)
        hsv_eq = cv2.merge([h, s, v_eq])
        self.image_processed = cv2.cvtColor(hsv_eq, cv2.COLOR_HSV2RGB)
      else:
        self.image_processed = cv2.equalizeHist(img)

    self.update_display()

  def run_pointwise(self):
      if self.image_original is None:
        return

      op = self.point_var.get()
      img = self.image_original.copy()

      if op == 'invert':
        self.image_processed = 255 - img

      elif op == 'gamma':
        gamma = self.gamma_var.get()
        if gamma <= 0:
          gamma = 1.0
        inv_gamma = 1.0 / gamma
        lut = np.array(
            [((i / 255.0) ** inv_gamma) * 255 for i in range(256)],
            dtype=np.uint8,
        )
        self.image_processed = cv2.LUT(img, lut)

      self.update_display()

  def show_histogram_window(self):
    if self.image_original is None:
      return

    top = Toplevel(self.root) if 'Toplevel' in globals() else tk.Toplevel(self.root)
    top.title('Гистограммы')
    top.geometry('1000x600')

    fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    colors = ('r', 'g', 'b')
    for i, col in enumerate(colors):
      hist_orig = cv2.calcHist([self.image_original], [i], None, [256], [0, 256])
      axes[0].plot(hist_orig, color=col)
    axes[0].set_title('Исходное')
    axes[0].set_xlim([0, 256])

    for i, col in enumerate(colors):
      hist_proc = cv2.calcHist([self.image_processed], [i], None, [256], [0, 256])
      axes[1].plot(hist_proc, color=col)
    axes[1].set_title('Результат')
    axes[1].set_xlim([0, 256])

    fig.tight_layout()
    canvas = FigureCanvasTkAgg(fig, master=top)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

  def save_image(self):
    if self.image_processed is None:
      return
    file_path = filedialog.asksaveasfilename(
        defaultextension='.png',
        filetypes=[('PNG', '*.png'), ('JPEG', '*.jpg')],
    )
    if file_path:
      save_img = cv2.cvtColor(self.image_processed, cv2.COLOR_RGB2BGR)
      cv2.imwrite(file_path, save_img)


if __name__ == '__main__':
  root = tk.Tk()
  app = Lab2App(root)
  try:
    root.mainloop()
  except KeyboardInterrupt:
    pass