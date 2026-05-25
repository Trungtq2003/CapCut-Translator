import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import threading
import subprocess
import sys

# Cài requests nếu chưa có
try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

from translator import process, LANGUAGES

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        except:
            pass
    return {"api_key": "", "last_file": ""}


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CapCut Translator")
        self.configure(bg="#1a1a2e", padx=24, pady=20)
        self.resizable(False, False)

        cfg = load_config()

        # ── Title ─────────────────────────────────────────────
        tk.Label(self, text="CapCut Translator",
                 bg="#1a1a2e", fg="#e0e0ff",
                 font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, columnspan=3, pady=(0, 4))

        tk.Label(self, text="Dịch draft_content.json sang đa ngôn ngữ",
                 bg="#1a1a2e", fg="#8888aa",
                 font=("Segoe UI", 9)).grid(
            row=1, column=0, columnspan=3, pady=(0, 16))
        
        tk.Label(self, text="LƯU Ý QUAN TRỌNG TRƯỚC KHI DỊCH HÃY THOÁT HOÀN TOÀN APP CAPCUT",
                 bg="#1a1a2e", fg="#8888aa",
                 font=("Segoe UI", 9)).grid(
            row=1, column=0, columnspan=3, pady=(0, 16))

        # ── API Key ───────────────────────────────────────────
        self._label("LibreTranslate API Key\n(để trống nếu dùng server public):", 2)
        self.api_key_var = tk.StringVar(value=cfg.get("api_key", ""))
        self._entry(self.api_key_var, 3, show="*")

        # ── File picker ───────────────────────────────────────
        self._label("File draft_content.json:", 4)
        file_frame = tk.Frame(self, bg="#1a1a2e")
        file_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 12))

        self.file_var = tk.StringVar(value=cfg.get("last_file", ""))
        tk.Entry(file_frame, textvariable=self.file_var,
                 width=42, state="readonly",
                 bg="#2a2a4a", fg="#ccccff",
                 insertbackground="white",
                 relief="flat", font=("Segoe UI", 9)).pack(side="left", ipady=4)

        tk.Button(file_frame, text="  Browse  ",
                  bg="#5865F2", fg="white",
                  activebackground="#4752c4",
                  relief="flat", font=("Segoe UI", 9),
                  command=self.pick_file).pack(side="left", padx=(6, 0), ipady=4)

        # ── Language checkboxes ───────────────────────────────
        self._label("Ngôn ngữ đích:", 6)
        lang_frame = tk.Frame(self, bg="#1a1a2e")
        lang_frame.grid(row=7, column=0, columnspan=3, sticky="w", pady=(0, 14))

        FLAGS = {
            "CS": "🇨🇿", "PL": "🇵🇱", "RU": "🇷🇺", "DE": "🇩🇪",
            "NL": "🇳🇱", "HU": "🇭🇺", "FR": "🇫🇷", "ES": "🇪🇸",
        }

        self.lang_vars = {}
        for i, (code, name) in enumerate(LANGUAGES.items()):
            var = tk.BooleanVar(value=True)
            self.lang_vars[code] = var
            label = name
            cb = tk.Checkbutton(lang_frame, text=label, variable=var,
                                bg="#1a1a2e", fg="#ccccff",
                                selectcolor="#2a2a4a",
                                activebackground="#1a1a2e",
                                activeforeground="#ffffff",
                                font=("Segoe UI", 9))
            cb.grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 18), pady=2)

        # ── Progress ──────────────────────────────────────────
        self.progress = ttk.Progressbar(self, length=480,
                                        mode="determinate", style="Custom.Horizontal.TProgressbar")
        self.progress.grid(row=8, column=0, columnspan=3, pady=(0, 8), sticky="ew")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Custom.Horizontal.TProgressbar",
                        troughcolor="#2a2a4a", background="#5865F2",
                        thickness=10)

        # ── Log ───────────────────────────────────────────────
        self.log_box = tk.Text(self, height=10, width=60,
                               state="disabled",
                               bg="#0d0d1a", fg="#a0ffa0",
                               font=("Consolas", 9),
                               relief="flat", padx=8, pady=6)
        self.log_box.grid(row=9, column=0, columnspan=3, pady=(0, 14))

        # ── Buttons ───────────────────────────────────────────
        btn_frame = tk.Frame(self, bg="#1a1a2e")
        btn_frame.grid(row=10, column=0, columnspan=3)

        self.btn_translate = tk.Button(
            btn_frame, text="  Dịch ngay  ",
            bg="#5865F2", fg="white",
            activebackground="#4752c4",
            font=("Segoe UI", 11, "bold"),
            relief="flat", padx=16, pady=8,
            command=self.start_translate)
        self.btn_translate.pack(side="left", padx=(0, 10))

        tk.Button(btn_frame, text="  Xóa log  ",
                  bg="#2a2a4a", fg="#aaaacc",
                  activebackground="#3a3a5a",
                  relief="flat", padx=12, pady=8,
                  font=("Segoe UI", 9),
                  command=self.clear_log).pack(side="left")

    # ── Helpers ───────────────────────────────────────────────
    def _label(self, text, row):
        tk.Label(self, text=text, bg="#1a1a2e", fg="#8888aa",
                 font=("Segoe UI", 9), justify="left").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 2))

    def _entry(self, var, row, show=None):
        kwargs = dict(textvariable=var, width=58,
                      bg="#2a2a4a", fg="#ccccff",
                      insertbackground="white",
                      relief="flat", font=("Segoe UI", 9))
        if show:
            kwargs["show"] = show
        tk.Entry(self, **kwargs).grid(
            row=row, column=0, columnspan=3, sticky="ew",
            pady=(0, 10), ipady=5)

    def pick_file(self):
        path = filedialog.askopenfilename(
            title="Chọn draft_content.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if path:
            self.file_var.set(path)

    def log(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")
        self.update_idletasks()

    def clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

    # ── Translate ─────────────────────────────────────────────
    def start_translate(self):
        api_key = self.api_key_var.get().strip()
        file_path = self.file_var.get().strip()
        langs = [code for code, var in self.lang_vars.items() if var.get()]

        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Lỗi", "Chưa chọn file JSON hợp lệ!")
            return
        if not langs:
            messagebox.showerror("Lỗi", "Chưa chọn ngôn ngữ nào!")
            return

        save_config({"api_key": api_key, "last_file": file_path})

        self.btn_translate.config(state="disabled", text="  Đang dịch...  ")
        self.progress["maximum"] = len(langs)
        self.progress["value"] = 0
        self.clear_log()
        self.log(f"→ File: {os.path.basename(file_path)}")
        self.log(f"→ Ngôn ngữ: {', '.join(langs)}\n")

        def run():
            try:
                completed = [0]
                orig_log = self.log

                def log_with_progress(msg):
                    orig_log(msg)
                    if msg.startswith("  ✓"):
                        completed[0] += 1
                        self.progress["value"] = completed[0]

                out_path = process(
                    json_path=file_path,
                    target_langs=langs,
                    api_key=api_key,
                    log_fn=log_with_progress
                )
                self.progress["value"] = len(langs)
                messagebox.showinfo("Xong!",
                    f"Dịch thành công!\n\nFile đã lưu tại:\n{out_path}")
            except Exception as e:
                messagebox.showerror("Lỗi", str(e))
                self.log(f"\n❌ Lỗi: {e}")
            finally:
                self.btn_translate.config(state="normal", text="  Dịch ngay  ")

        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
