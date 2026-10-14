import tkinter as tk
from tkinter import colorchooser


class ColorModelApp:

  def __init__(self, root):
    self.root = root
    self.root.title(
        'Цветовые модели (CMYK - RGB - HSV)'
    )
    self.root.geometry('920x680')
    self.root.minsize(850, 620)

    #Базовый цвет RGB
    self.r = 79
    self.g = 70
    self.b = 229

    self.is_updating = False

    self.create_widgets()
    self.update_all_from_rgb(update_sliders=True)

  def create_widgets(self):
    main_frame = tk.Frame(self.root, padx=15, pady=15)
    main_frame.pack(fill=tk.BOTH, expand=True)

    #Способ заданиячерез графическую палитру
    preview_frame = tk.LabelFrame(
        main_frame, text='Выбор и просмотр цвета', padx=10, pady=10
    )
    preview_frame.pack(fill=tk.X, padx=5, pady=5)

    self.color_canvas = tk.Canvas(preview_frame, height=70, bg='#4f46e5')
    self.color_canvas.pack(fill=tk.X, pady=5)

    btn_palette = tk.Button(
      
        preview_frame,
        text='Color Picker',
        command=self.open_color_picker,
        bg='#e0e7ff',
        font=('Segoe UI', 10, 'bold'),
        cursor='hand2',

    )
    btn_palette.pack(pady=5)

    # Контейнер для трех цветовых моделей
    models_frame = tk.Frame(main_frame)
    models_frame.pack(fill=tk.BOTH, expand=True, pady=10)

    models_frame.columnconfigure(0, weight=1)
    models_frame.columnconfigure(1, weight=1)
    models_frame.columnconfigure(2, weight=1)
    models_frame.rowconfigure(0, weight=1)

    # --- Модель RGB ---
    rgb_frame = tk.LabelFrame(
        models_frame,
        text='Модель RGB',
        padx=10,
        pady=10,
        font=('Segoe UI', 11, 'bold'),
    )
    rgb_frame.grid(row=0, column=0, sticky='nsew', padx=5)

    self.rgb_vars = {}
    self.rgb_sliders = {}
    self.rgb_entries = {}

    for ch in ['R', 'G', 'B']:
      lbl = tk.Label(rgb_frame, text=f'{ch} (0–255):', font=('Segoe UI', 9))
      lbl.pack(anchor='w', pady=(5, 0))

      row_f = tk.Frame(rgb_frame)
      row_f.pack(fill=tk.X, pady=2)

      var = tk.IntVar(value=0)
      self.rgb_vars[ch] = var

      slider = tk.Scale(
          row_f,
          from_=0,
          to=255,
          orient=tk.HORIZONTAL,
          variable=var,
          command=lambda val, c=ch: self.on_rgb_slider(c, val),
      )
      slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
      self.rgb_sliders[ch] = slider

      entry = tk.Entry(row_f, width=5, font=('Segoe UI', 10))
      entry.pack(side=tk.RIGHT)
      entry.bind(
          '<Return>', lambda e, c=ch: self.on_rgb_entry_submit(c)
      )
      entry.bind(
          '<FocusOut>', lambda e, c=ch: self.on_rgb_entry_submit(c)
      )
      self.rgb_entries[ch] = entry

    cmyk_frame = tk.LabelFrame(
        models_frame,
        text='Модель CMYK',
        padx=10,
        pady=10,
        font=('Segoe UI', 11, 'bold'),
    )
    cmyk_frame.grid(row=0, column=1, sticky='nsew', padx=5)

    self.cmyk_vars = {}
    self.cmyk_sliders = {}
    self.cmyk_entries = {}

    for ch in ['C', 'M', 'Y', 'K']:
      lbl = tk.Label(
          cmyk_frame, text=f'{ch} (0–100%):', font=('Segoe UI', 9)
      )
      lbl.pack(anchor='w', pady=(5, 0))

      row_f = tk.Frame(cmyk_frame)
      row_f.pack(fill=tk.X, pady=2)

      var = tk.IntVar(value=0)
      self.cmyk_vars[ch] = var

      slider = tk.Scale(
          row_f,
          from_=0,
          to=100,
          orient=tk.HORIZONTAL,
          variable=var,
          command=lambda val, c=ch: self.on_cmyk_slider(c, val),
      )
      slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
      self.cmyk_sliders[ch] = slider

      entry = tk.Entry(row_f, width=5, font=('Segoe UI', 10))
      entry.pack(side=tk.RIGHT)
      entry.bind('<Return>', lambda e, c=ch: self.on_cmyk_entry_submit(c))
      entry.bind('<FocusOut>', lambda e, c=ch: self.on_cmyk_entry_submit(c))
      self.cmyk_entries[ch] = entry

    #HSV
    hsv_frame = tk.LabelFrame(
        models_frame,
        text='Модель HSV',
        padx=10,
        pady=10,
        font=('Segoe UI', 11, 'bold'),
    )
    hsv_frame.grid(row=0, column=2, sticky='nsew', padx=5)

    self.hsv_vars = {}
    self.hsv_sliders = {}
    self.hsv_entries = {}

    ranges = {'H': 360, 'S': 100, 'V': 100}
    for ch in ['H', 'S', 'V']:
      max_val = ranges[ch]
      unit = '°' if ch == 'H' else '%'
      lbl = tk.Label(
          hsv_frame, text=f'{ch} (0–{max_val}{unit}):', font=('Segoe UI', 9)
      )
      lbl.pack(anchor='w', pady=(5, 0))

      row_f = tk.Frame(hsv_frame)
      row_f.pack(fill=tk.X, pady=2)

      var = tk.IntVar(value=0)
      self.hsv_vars[ch] = var

      slider = tk.Scale(
          row_f,
          from_=0,
          to=max_val,
          orient=tk.HORIZONTAL,
          variable=var,
          command=lambda val, c=ch: self.on_hsv_slider(c, val),
      )
      slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
      self.hsv_sliders[ch] = slider

      entry = tk.Entry(row_f, width=5, font=('Segoe UI', 10))
      entry.pack(side=tk.RIGHT)
      entry.bind('<Return>', lambda e, c=ch: self.on_hsv_entry_submit(c))
      entry.bind('<FocusOut>', lambda e, c=ch: self.on_hsv_entry_submit(c))
      self.hsv_entries[ch] = entry

  # Конвертация
  def rgb_to_cmyk_calc(self, r, g, b):
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    k = 1.0 - max(rf, gf, bf)
    if k >= 1.0:
      return 0, 0, 0, 100
    c = (1.0 - rf - k) / (1.0 - k)
    m = (1.0 - gf - k) / (1.0 - k)
    y = (1.0 - bf - k) / (1.0 - k)
    return (
        round(c * 100),
        round(m * 100),
        round(y * 100),
        round(k * 100),
    )

  def cmyk_to_rgb_calc(self, c, m, y, k):
    cf, mf, yf, kf = c / 100.0, m / 100.0, y / 100.0, k / 100.0
    r = 255 * (1.0 - cf) * (1.0 - kf)
    g = 255 * (1.0 - mf) * (1.0 - kf)
    b = 255 * (1.0 - yf) * (1.0 - kf)
    return round(r), round(g), round(b)

  def rgb_to_hsv_calc(self, r, g, b):
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    mx = max(rf, gf, bf)
    mn = min(rf, gf, bf)
    delta = mx - mn
    v = mx
    s = 0 if mx == 0 else delta / mx

    h = 0
    if delta != 0:
      if mx == rf:
        h = 60 * (((gf - bf) / delta) % 6)
      elif mx == gf:
        h = 60 * (((bf - rf) / delta) + 2)
      elif mx == bf:
        h = 60 * (((rf - gf) / delta) + 4)
    if h < 0:
      h += 360
    return round(h), round(s * 100), round(v * 100)

  def hsv_to_rgb_calc(self, h, s, v):
    sf, vf = s / 100.0, v / 100.0
    c = vf * sf
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = vf - c
    rf, gf, bf = 0, 0, 0
    if 0 <= h < 60:
      rf, gf, bf = c, x, 0
    elif 60 <= h < 120:
      rf, gf, bf = x, c, 0
    elif 120 <= h < 180:
      rf, gf, bf = 0, c, x
    elif 180 <= h < 240:
      rf, gf, bf = 0, x, c
    elif 240 <= h < 300:
      rf, gf, bf = x, 0, c
    elif 300 <= h < 360:
      rf, gf, bf = c, 0, x
    return (
        round((rf + m) * 255),
        round((gf + m) * 255),
        round((bf + m) * 255),
    )

  def update_all_from_rgb(self, update_sliders=True):
    if self.is_updating:
      return
    self.is_updating = True

    self.r = max(0, min(255, self.r))
    self.g = max(0, min(255, self.g))
    self.b = max(0, min(255, self.b))

    for ch, val in zip(['R', 'G', 'B'], [self.r, self.g, self.b]):
      if update_sliders:
        self.rgb_vars[ch].set(val)
      self.rgb_entries[ch].delete(0, tk.END)
      self.rgb_entries[ch].insert(0, str(val))

    # Пересчет в CMYK и HSV
    c, m, y, k = self.rgb_to_cmyk_calc(self.r, self.g, self.b)
    h, s, v = self.rgb_to_hsv_calc(self.r, self.g, self.b)

    # Обновление CMYK
    for ch, val in zip(['C', 'M', 'Y', 'K'], [c, m, y, k]):
      if update_sliders:
        self.cmyk_vars[ch].set(val)
      self.cmyk_entries[ch].delete(0, tk.END)
      self.cmyk_entries[ch].insert(0, str(val))

    # Обновление HSV
    for ch, val in zip(['H', 'S', 'V'], [h, s, v]):
      if update_sliders:
        self.hsv_vars[ch].set(val)
      self.hsv_entries[ch].delete(0, tk.END)
      self.hsv_entries[ch].insert(0, str(val))

    hex_color = f'#{self.r:02x}{self.g:02x}{self.b:02x}'
    self.color_canvas.config(bg=hex_color)

    self.is_updating = False

  def on_rgb_slider(self, ch, val):
    if self.is_updating:
      return
    self.r = self.rgb_vars['R'].get()
    self.g = self.rgb_vars['G'].get()
    self.b = self.rgb_vars['B'].get()
    self.update_all_from_rgb(update_sliders=False)

  def on_cmyk_slider(self, ch, val):
    if self.is_updating:
      return
    c = self.cmyk_vars['C'].get()
    m = self.cmyk_vars['M'].get()
    y = self.cmyk_vars['Y'].get()
    k = self.cmyk_vars['K'].get()
    self.r, self.g, self.b = self.cmyk_to_rgb_calc(c, m, y, k)
    self.update_all_from_rgb(update_sliders=False)

  def on_hsv_slider(self, ch, val):
    if self.is_updating:
      return
    h = self.hsv_vars['H'].get()
    s = self.hsv_vars['S'].get()
    v = self.hsv_vars['V'].get()
    self.r, self.g, self.b = self.hsv_to_rgb_calc(h, s, v)
    self.update_all_from_rgb(update_sliders=False)

  # Обработчики текстовых полей
  def on_rgb_entry_submit(self, ch):
    try:
      val = int(self.rgb_entries[ch].get())
      setattr(self, ch.lower(), val)
      self.update_all_from_rgb(update_sliders=True)
    except ValueError:
      pass

  def on_cmyk_entry_submit(self, ch):
    try:
      c = int(self.cmyk_entries['C'].get())
      m = int(self.cmyk_entries['M'].get())
      y = int(self.cmyk_entries['Y'].get())
      k = int(self.cmyk_entries['K'].get())
      self.r, self.g, self.b = self.cmyk_to_rgb_calc(c, m, y, k)
      self.update_all_from_rgb(update_sliders=True)
    except ValueError:
      pass

  def on_hsv_entry_submit(self, ch):
    try:
      h = int(self.hsv_entries['H'].get())
      s = int(self.hsv_entries['S'].get())
      v = int(self.hsv_entries['V'].get())
      self.r, self.g, self.b = self.hsv_to_rgb_calc(h, s, v)
      self.update_all_from_rgb(update_sliders=True)
    except ValueError:
      pass

  #Выбор цвета через системную палитру
  def open_color_picker(self):
    color_code = colorchooser.askcolor(
        title='Выберите цвет',
        initialcolor=f'#{self.r:02x}{self.g:02x}{self.b:02x}',
    )
    if color_code[0]:
      rgb = color_code[0]
      self.r, self.g, self.b = int(rgb[0]), int(rgb[1]), int(rgb[2])
      self.update_all_from_rgb(update_sliders=True)


if __name__ == '__main__':
  root = tk.Tk()
  app = ColorModelApp(root)
  root.mainloop()