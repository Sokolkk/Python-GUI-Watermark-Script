import os
import sys
import json
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw

SETTINGS_FILE = "settings.json"

def make_rounded_corners(im, radius_percent):
    """Скругляет углы у изображения (логотипа)."""
    im = im.convert("RGBA")
    radius = int(min(im.size) * radius_percent)
    if radius < 1: radius = 1

    mask = Image.new('L', im.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), im.size], radius=radius, fill=255)
    
    im.putalpha(mask)
    return im

def apply_opacity(img, opacity):
    """Меняет прозрачность изображения."""
    img = img.convert("RGBA")
    alpha = img.split()[3]
    alpha = alpha.point(lambda p: int(p * opacity))
    img.putalpha(alpha)
    return img

class WatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Watermark Processor")
        self.root.geometry("520x620") # Чуть расширил окно для новой кнопки
        self.root.resizable(False, False)
        
        self.selected_files = []
        
        # --- Переменные настроек с загрузкой из файла ---
        default_out = os.path.join(os.getcwd(), "output_images")
        
        self.output_folder = tk.StringVar(value=self.load_setting("output_folder", default_out))
        self.logo_file = tk.StringVar(value=self.load_setting("logo_file", ""))
        
        self.pad_x = tk.IntVar(value=self.load_setting("pad_x", 20))
        self.pad_y = tk.IntVar(value=self.load_setting("pad_y", 20))
        self.opacity = tk.IntVar(value=self.load_setting("opacity", 90))
        self.radius = tk.IntVar(value=self.load_setting("radius", 74))
        self.scale = tk.IntVar(value=self.load_setting("scale", 12))
        
        self.setup_ui()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_setting(self, key, default):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    return settings.get(key, default)
            except Exception:
                pass
        return default

    def save_all_settings(self):
        settings = {
            "output_folder": self.output_folder.get(),
            "logo_file": self.logo_file.get(),
            "pad_x": self.pad_x.get(),
            "pad_y": self.pad_y.get(),
            "opacity": self.opacity.get(),
            "radius": self.radius.get(),
            "scale": self.scale.get()
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def on_closing(self):
        self.save_all_settings()
        self.root.destroy()

    def setup_ui(self):
        # --- 1. Исходные файлы ---
        frame_files = tk.LabelFrame(self.root, text=" 1. Исходные фото ", padx=10, pady=5)
        frame_files.pack(fill="x", padx=10, pady=5)

        self.lbl_files = tk.Label(frame_files, text="Выбрано файлов: 0")
        self.lbl_files.pack(side="left")

        tk.Button(frame_files, text="Сбросить", command=self.clear_files).pack(side="right", padx=(5, 0))
        tk.Button(frame_files, text="Выбрать фото", command=self.select_files).pack(side="right")

        # --- 2. Логотип ---
        frame_logo = tk.LabelFrame(self.root, text=" 2. Файл логотипа ", padx=10, pady=5)
        frame_logo.pack(fill="x", padx=10, pady=5)

        tk.Entry(frame_logo, textvariable=self.logo_file, state="readonly").pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Button(frame_logo, text="Выбрать лого", command=self.choose_logo_file).pack(side="right")

        # --- 3. Папка сохранения ---
        frame_output = tk.LabelFrame(self.root, text=" 3. Папка сохранения ", padx=10, pady=5)
        frame_output.pack(fill="x", padx=10, pady=5)

        tk.Entry(frame_output, textvariable=self.output_folder, state="readonly").pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # ДОБАВЛЕНА НОВАЯ КНОПКА ОТКРЫТИЯ ПАПКИ
        tk.Button(frame_output, text="Открыть", command=self.open_output_folder).pack(side="right")
        tk.Button(frame_output, text="Изменить", command=self.choose_output_folder).pack(side="right", padx=(0, 5))

        # --- 4. Ползунки настроек ---
        frame_settings = tk.LabelFrame(self.root, text=" 4. Настройки наложения ", padx=10, pady=10)
        frame_settings.pack(fill="x", padx=10, pady=5)

        frame_settings.columnconfigure(1, weight=1)

        tk.Label(frame_settings, text="Размер логотипа (%):").grid(row=0, column=0, sticky="e", pady=2)
        tk.Scale(frame_settings, variable=self.scale, from_=1, to=100, orient="horizontal").grid(row=0, column=1, sticky="we", padx=5)

        tk.Label(frame_settings, text="Отступ справа (px):").grid(row=1, column=0, sticky="e", pady=2)
        tk.Scale(frame_settings, variable=self.pad_x, from_=0, to=500, orient="horizontal").grid(row=1, column=1, sticky="we", padx=5)

        tk.Label(frame_settings, text="Отступ снизу (px):").grid(row=2, column=0, sticky="e", pady=2)
        tk.Scale(frame_settings, variable=self.pad_y, from_=0, to=500, orient="horizontal").grid(row=2, column=1, sticky="we", padx=5)

        tk.Label(frame_settings, text="Непрозрачность (%):").grid(row=3, column=0, sticky="e", pady=2)
        tk.Scale(frame_settings, variable=self.opacity, from_=0, to=100, orient="horizontal").grid(row=3, column=1, sticky="we", padx=5)

        tk.Label(frame_settings, text="Сила скругления (%):").grid(row=4, column=0, sticky="e", pady=2)
        tk.Scale(frame_settings, variable=self.radius, from_=0, to=100, orient="horizontal").grid(row=4, column=1, sticky="we", padx=5)

        # --- Кнопка старта ---
        self.btn_start = tk.Button(self.root, text="Начать обработку", font=("Arial", 12, "bold"), bg="#4CAF50", fg="white", command=self.process_images)
        self.btn_start.pack(fill="x", padx=10, pady=(15, 5), ipady=10)

        self.lbl_status = tk.Label(self.root, text="Готов к работе", fg="gray")
        self.lbl_status.pack()

    # --- Обработчики кнопок ---
    def select_files(self):
        files = filedialog.askopenfilenames(
            title="Выберите изображения",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp")]
        )
        if files:
            self.selected_files.extend(files)
            self.selected_files = sorted(list(set(self.selected_files)))
            self.update_file_label()

    def clear_files(self):
        self.selected_files = []
        self.update_file_label()

    def update_file_label(self):
        self.lbl_files.config(text=f"Выбрано файлов: {len(self.selected_files)}")

    def choose_logo_file(self):
        file = filedialog.askopenfilename(
            title="Выберите файл логотипа",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")]
        )
        if file:
            self.logo_file.set(file)

    def choose_output_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку для сохранения")
        if folder:
            self.output_folder.set(folder)

    # ДОБАВЛЕНА ФУНКЦИЯ ДЛЯ ОТКРЫТИЯ ПАПКИ
    def open_output_folder(self):
        path = self.output_folder.get()
        if not os.path.exists(path):
            messagebox.showwarning("Внимание", "Эта папка еще не существует. Она будет создана при обработке фото.")
            return
            
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin": # macOS
                subprocess.call(["open", path])
            else: # Linux
                subprocess.call(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку: {e}")

    # --- Основной процесс ---
    def process_images(self):
        if not self.selected_files:
            messagebox.showwarning("Внимание", "Сначала выберите фотографии для обработки!")
            return

        logo_path = self.logo_file.get()
        if not logo_path or not os.path.exists(logo_path):
            messagebox.showerror("Ошибка", "Пожалуйста, укажите правильный путь к файлу логотипа!")
            return

        self.save_all_settings()

        out_dir = self.output_folder.get()
        os.makedirs(out_dir, exist_ok=True)

        try:
            wm_original = Image.open(logo_path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть логотип: {e}")
            return

        self.btn_start.config(state="disabled")
        counter = 1
        total = len(self.selected_files)

        scale_val = self.scale.get() / 100.0
        pad_x_val = self.pad_x.get()
        pad_y_val = self.pad_y.get()
        opacity_val = self.opacity.get() / 100.0
        radius_val = self.radius.get() / 100.0

        for filepath in self.selected_files:
            try:
                self.lbl_status.config(text=f"Обработка {counter} из {total}...")
                self.root.update()

                img = Image.open(filepath).convert("RGBA")
                wm = wm_original.copy()

                target_w = int(img.width * scale_val)
                if target_w < 10: target_w = 10
                aspect = wm.width / wm.height
                target_h = int(target_w / aspect)
                wm = wm.resize((target_w, target_h), Image.Resampling.LANCZOS)

                if radius_val > 0:
                    wm = make_rounded_corners(wm, radius_val)
                
                if opacity_val < 1.0:
                    wm = apply_opacity(wm, opacity_val)

                pos_x = img.width - wm.width - pad_x_val
                pos_y = img.height - wm.height - pad_y_val

                output_filename = f"{counter}.png"
                output_path = os.path.join(out_dir, output_filename)
                
                img.alpha_composite(wm, (pos_x, pos_y))
                img.save(output_path, "PNG")

                counter += 1

            except Exception as e:
                print(f"Ошибка с файлом {filepath}: {e}")

        self.btn_start.config(state="normal")
        self.lbl_status.config(text="Обработка завершена!")
        self.clear_files()
        messagebox.showinfo("Успех", f"Успешно обработано файлов: {counter - 1}\nОни сохранены в:\n{out_dir}")

if __name__ == "__main__":
    root = tk.Tk()
    app = WatermarkApp(root)
    root.mainloop()
