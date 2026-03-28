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
        
        # Начальный размер: показываем только левую часть
        self.root.geometry("520x720")
        self.root.resizable(False, False)
        
        self.selected_files = []
        self.editor_visible = False # Флаг видимости редактора
        
        # --- Переменные настроек с загрузкой из файла ---
        default_out = os.path.join(os.getcwd(), "output_images")
        
        self.output_folder = tk.StringVar(value=self.load_setting("output_folder", default_out))
        self.logo_file = tk.StringVar(value=self.load_setting("logo_file", ""))
        
        self.pad_x = tk.IntVar(value=self.load_setting("pad_x", 20))
        self.pad_y = tk.IntVar(value=self.load_setting("pad_y", 20))
        self.opacity = tk.IntVar(value=self.load_setting("opacity", 90))
        self.radius = tk.IntVar(value=self.load_setting("radius", 74))
        self.scale = tk.IntVar(value=self.load_setting("scale", 12))

        # Переменные для новых функций
        self.new_folder_name = tk.StringVar(value="new_folder")
        self.new_file_name = tk.StringVar(value="info.txt")
        
        self.setup_ui()
        self.setup_cyrillic_hotkeys()

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

   # --- Поддержка горячих клавиш для русской раскладки ---
    def setup_cyrillic_hotkeys(self):
        def handle_cyrillic_hotkeys(event):
            widget = event.widget
            
            if isinstance(widget, (tk.Entry, tk.Text)):
                keysym = event.keysym.lower()
                
                if keysym in ['cyrillic_ef', 'ф', 'a']: 
                    if isinstance(widget, tk.Text):
                        widget.tag_add("sel", "1.0", "end")
                    else:
                        widget.select_range(0, tk.END)
                        widget.icursor(tk.END)
                    return "break"
                elif keysym in ['cyrillic_es', 'с', 'c']: 
                    widget.event_generate("<<Copy>>")
                    return "break"
                elif keysym in ['cyrillic_em', 'м', 'v']: 
                    widget.event_generate("<<Paste>>")
                    return "break"
                elif keysym in ['cyrillic_che', 'ч', 'x']: 
                    widget.event_generate("<<Cut>>")
                    return "break"

        self.root.bind('<Control-KeyPress>', handle_cyrillic_hotkeys)

    def toggle_editor(self):
        """Разворачивает/сворачивает правую часть с редактором."""
        if self.editor_visible:
            self.root.geometry("520x720")
            self.btn_toggle_editor.config(text="ПОКАЗАТЬ РЕДАКТОР", bg="#e0e0e0")
            self.editor_visible = False
        else:
            self.root.geometry("1040x720")
            self.btn_toggle_editor.config(text="СКРЫТЬ РЕДАКТОР", bg="#ffcccc")
            self.editor_visible = True

    def setup_ui(self):
        # --- РАЗДЕЛЕНИЕ НА ЛЕВУЮ И ПРАВУЮ ЧАСТИ ---
        
        # Левая часть (520 пикселей, фиксированная)
        self.left_frame = tk.Frame(self.root, width=520, height=720)
        self.left_frame.pack_propagate(False) # Запрещаем рамке сжиматься
        self.left_frame.pack(side="left", fill="y")

        # Правая часть (520 пикселей, появляется при расширении окна)
        self.right_frame = tk.Frame(self.root, width=520, height=720)
        self.right_frame.pack_propagate(False)
        self.right_frame.pack(side="left", fill="both", expand=True)

        # ==========================================
        # ЗАПОЛНЯЕМ ЛЕВУЮ ЧАСТЬ (ОСНОВНАЯ ПРОГРАММА)
        # ==========================================

        # --- 1. Исходные файлы ---
        frame_files = tk.LabelFrame(self.left_frame, text=" 1. Исходные фото ", padx=10, pady=5)
        frame_files.pack(fill="x", padx=10, pady=5)

        self.lbl_files = tk.Label(frame_files, text="Выбрано файлов: 0")
        self.lbl_files.pack(side="left")

        tk.Button(frame_files, text="Сбросить", command=self.clear_files).pack(side="right", padx=(5, 0))
        tk.Button(frame_files, text="Выбрать фото", command=self.select_files).pack(side="right")

        # --- 2. Логотип ---
        frame_logo = tk.LabelFrame(self.left_frame, text=" 2. Файл логотипа ", padx=10, pady=5)
        frame_logo.pack(fill="x", padx=10, pady=5)

        tk.Entry(frame_logo, textvariable=self.logo_file, state="readonly").pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Button(frame_logo, text="Выбрать лого", command=self.choose_logo_file).pack(side="right")

        # --- 3. Папка сохранения ---
        frame_output = tk.LabelFrame(self.left_frame, text=" 3. Папка сохранения ", padx=10, pady=5)
        frame_output.pack(fill="x", padx=10, pady=5)

        tk.Entry(frame_output, textvariable=self.output_folder, state="readonly").pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        tk.Button(frame_output, text="Открыть", command=self.open_output_folder).pack(side="right")
        tk.Button(frame_output, text="Изменить", command=self.choose_output_folder).pack(side="right", padx=(0, 5))

        # --- 4. Ползунки настроек ---
        frame_settings = tk.LabelFrame(self.left_frame, text=" 4. Настройки наложения ", padx=10, pady=10)
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

        # --- 5. Дополнительные инструменты ---
        frame_tools = tk.LabelFrame(self.left_frame, text=" 5. Дополнительные инструменты ", padx=10, pady=5)
        frame_tools.pack(fill="x", padx=10, pady=5)
        
        frame_tools.columnconfigure(1, weight=1)

        # Создание папки
        tk.Label(frame_tools, text="Имя папки:").grid(row=0, column=0, sticky="w", pady=2)
        tk.Entry(frame_tools, textvariable=self.new_folder_name).grid(row=0, column=1, sticky="we", padx=5, pady=2)
        tk.Button(frame_tools, text="Создать папку", command=self.create_custom_folder, width=15).grid(row=0, column=2, columnspan=2, pady=2, sticky="we")

        # Создание файла + Кнопка выдвижного редактора
        tk.Label(frame_tools, text="Имя файла:").grid(row=1, column=0, sticky="w", pady=2)
        tk.Entry(frame_tools, textvariable=self.new_file_name).grid(row=1, column=1, sticky="we", padx=5, pady=2)
        
        tk.Button(frame_tools, text="Сохранить файл", command=self.create_custom_file).grid(row=1, column=2, pady=2, padx=(0, 5))
        
        # Сама кнопка выдвижения
        self.btn_toggle_editor = tk.Button(frame_tools, text="ПОКАЗАТЬ РЕДАКТОР", command=self.toggle_editor, bg="#e0e0e0", font=("Arial", 8, "bold"))
        self.btn_toggle_editor.grid(row=1, column=3, pady=2, sticky="we")

        # --- Кнопка старта ---
        self.btn_start = tk.Button(self.left_frame, text="Начать обработку", font=("Arial", 12, "bold"), bg="#4CAF50", fg="white", command=self.process_images)
        self.btn_start.pack(fill="x", padx=10, pady=(15, 5), ipady=10)

        self.lbl_status = tk.Label(self.left_frame, text="Готов к работе", fg="#555555", font=("Arial", 10))
        self.lbl_status.pack()


        # ==========================================
        # ЗАПОЛНЯЕМ ПРАВУЮ ЧАСТЬ (ТЕКСТОВЫЙ РЕДАКТОР)
        # ==========================================
        lbl_editor_title = tk.Label(self.right_frame, text="Текстовый редактор", font=("Arial", 12, "bold"), fg="#333333")
        lbl_editor_title.pack(pady=(15, 5))
        
        lbl_editor_hint = tk.Label(self.right_frame, text="Текст отсюда будет сохранен в ваш .txt файл", font=("Arial", 9), fg="#666666")
        lbl_editor_hint.pack(pady=(0, 10))

        frame_text = tk.Frame(self.right_frame)
        frame_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        text_scroll = tk.Scrollbar(frame_text)
        text_scroll.pack(side="right", fill="y")

        self.text_editor = tk.Text(frame_text, wrap="word", font=("Arial", 10), yscrollcommand=text_scroll.set)
        self.text_editor.pack(side="left", fill="both", expand=True)
        text_scroll.config(command=self.text_editor.yview)

    # --- Функции для папок и файлов ---
    def create_custom_folder(self):
        base_dir = self.output_folder.get()
        folder_name = self.new_folder_name.get().strip()
        
        if not folder_name:
            self.lbl_status.config(text="Укажите имя папки перед созданием", fg="#d32f2f")
            return
            
        new_dir_path = os.path.join(base_dir, folder_name)
        
        try:
            os.makedirs(new_dir_path, exist_ok=True)
            self.lbl_status.config(text=f"Папка '{folder_name}' успешно создана", fg="#388e3c")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать папку:\n{e}")

    def create_custom_file(self):
        base_dir = self.output_folder.get()
        file_name = self.new_file_name.get().strip()
        
        # Получаем текст из редактора
        file_content = self.text_editor.get("1.0", tk.END).rstrip('\n') 
        
        if not file_name:
            self.lbl_status.config(text="Укажите имя файла перед созданием", fg="#d32f2f")
            return
            
        if not file_name.lower().endswith(".txt"):
            file_name += ".txt"
            self.new_file_name.set(file_name) 
            
        os.makedirs(base_dir, exist_ok=True) 
        new_file_path = os.path.join(base_dir, file_name)
        
        try:
            with open(new_file_path, "w", encoding="utf-8") as f:
                f.write(file_content) 
            self.lbl_status.config(text=f"Файл '{file_name}' успешно сохранен", fg="#388e3c")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать файл:\n{e}")

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
            self.lbl_status.config(text=f"Добавлены файлы. Всего: {len(self.selected_files)}", fg="#555555")

    def clear_files(self):
        self.selected_files = []
        self.update_file_label()
        self.lbl_status.config(text="Список файлов очищен", fg="#555555")

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

    def open_output_folder(self):
        path = self.output_folder.get()
        if not os.path.exists(path):
            self.lbl_status.config(text="Папка будет создана автоматически при сохранении", fg="#d32f2f")
            return
            
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin": 
                subprocess.call(["open", path])
            else: 
                subprocess.call(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку: {e}")

    # --- Основной процесс ---
    def process_images(self):
        if not self.selected_files:
            self.lbl_status.config(text="Сначала выберите фотографии для обработки", fg="#d32f2f")
            return

        logo_path = self.logo_file.get()
        if not logo_path or not os.path.exists(logo_path):
            self.lbl_status.config(text="Укажите правильный путь к логотипу", fg="#d32f2f")
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
                self.lbl_status.config(text=f"Обработка: {counter} из {total}...", fg="#555555")
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
        self.clear_files()
        
        self.lbl_status.config(text=f"Завершено! Успешно сохранено файлов: {counter - 1}", fg="#388e3c")

if __name__ == "__main__":
    root = tk.Tk()
    app = WatermarkApp(root)
    root.mainloop()
