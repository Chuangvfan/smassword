import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
import time
import threading
from gmssl import sm3, func
import json
import os

# 配置文件名
CONFIG_FILE = "smassword_config.json"


class HotkeyRecorder:
    """
    专门用于首次运行时录制热键的窗口类
    """

    def __init__(self, on_complete_callback):
        self.root = tk.Tk()
        self.root.title("首次运行设置")
        self.on_complete = on_complete_callback

        width, height = 300, 200
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)

        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="欢迎使用 SM3 自动输入器", font=("微软雅黑", 12, "bold")).pack(pady=5)
        ttk.Label(frame, text="检测到这是您第一次运行，\n请设置您的全局唤醒热键。", justify="center").pack(pady=5)

        self.status_label = ttk.Label(frame, text="点击下方按钮开始录制", foreground="gray")
        self.status_label.pack(pady=10)

        self.btn = ttk.Button(frame, text="开始录制热键", command=self.start_recording)
        self.btn.pack(pady=5)

    def start_recording(self):
        self.btn.config(state="disabled")
        self.status_label.config(text="请按下组合键 (如 Ctrl+Alt+Z)...", foreground="blue")
        threading.Thread(target=self._record_thread).start()

    def _record_thread(self):
        try:
            hotkey = keyboard.read_hotkey(suppress=False)
            self.root.after(0, lambda: self._finish_recording(hotkey))
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text="录制失败，请重试", foreground="red"))
            self.root.after(0, lambda: self.btn.config(state="normal"))

    def _finish_recording(self, hotkey):
        config_data = {"hotkey": hotkey}
        try:
            # 写入配置后立即关闭文件
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f)

            self.status_label.config(text=f"成功! 热键已设为: {hotkey}", foreground="green")
            self.root.update()
            time.sleep(1)

            self.root.destroy()
            self.on_complete(hotkey)

        except Exception as e:
            messagebox.showerror("错误", f"保存配置文件失败: {e}")
            self.btn.config(state="normal")

    def run(self):
        self.root.mainloop()


class SM3AutoTyper:
    def __init__(self, current_hotkey):
        self.root = tk.Tk()
        self.root.title("smassword")
        self.current_hotkey = current_hotkey

        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.root.withdraw()

        width, height = 400, 180
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.resizable(False, False)

        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        hotkey_info = ttk.Label(main_frame, text=f"当前唤醒热键: {self.current_hotkey}", font=("Arial", 8),
                                foreground="#666")
        hotkey_info.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        # === 1. 口令 ===
        ttk.Label(main_frame, text="记忆口令:").grid(row=1, column=0, sticky="w")
        self.text_entry = ttk.Entry(main_frame, width=28, show="*")
        self.text_entry.grid(row=1, column=1, pady=5, padx=5)
        self.text_entry.bind('<Return>', lambda e: self.salt_entry.focus_set())

        self.show_text_var = tk.BooleanVar(value=False)
        self.btn_eye_text = ttk.Checkbutton(main_frame, text="👁", variable=self.show_text_var,
                                            style='Toolbutton', command=self.toggle_text_visibility)
        self.btn_eye_text.grid(row=1, column=2, padx=2)

        # === 2. 盐值 ===
        ttk.Label(main_frame, text="盐值(Salt):").grid(row=2, column=0, sticky="w")
        self.salt_entry = ttk.Entry(main_frame, width=28, show="*")
        self.salt_entry.grid(row=2, column=1, pady=5, padx=5)
        self.salt_entry.bind('<Return>', lambda e: self.perform_type())

        self.show_salt_var = tk.BooleanVar(value=False)
        self.btn_eye_salt = ttk.Checkbutton(main_frame, text="👁", variable=self.show_salt_var,
                                            style='Toolbutton', command=self.toggle_salt_visibility)
        self.btn_eye_salt.grid(row=2, column=2, padx=2)

        # === 3. 按钮 ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=15)

        ttk.Button(btn_frame, text="确认并输入 (Enter)", command=self.perform_type).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="隐藏", command=self.hide_window).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="重置热键", command=self.reset_config).pack(side='left', padx=5)

        self.status_label = ttk.Label(main_frame, text="等待输入...", foreground="gray", font=("Arial", 8))
        self.status_label.grid(row=4, column=0, columnspan=3)

    def toggle_text_visibility(self):
        if self.show_text_var.get():
            self.text_entry.config(show='')
        else:
            self.text_entry.config(show='*')

    def toggle_salt_visibility(self):
        if self.show_salt_var.get():
            self.salt_entry.config(show='')
        else:
            self.salt_entry.config(show='*')

    def show_window(self):
        self.root.after(0, self._show_window_thread_safe)

    def _show_window_thread_safe(self):
        self.root.deiconify()
        self.text_entry.delete(0, 'end')
        self.salt_entry.delete(0, 'end')
        self.show_text_var.set(False)
        self.show_salt_var.set(False)
        self.text_entry.config(show='*')
        self.salt_entry.config(show='*')
        self.text_entry.focus_set()
        self.status_label.config(text="输入后按 Enter 上屏", foreground="gray")

    def hide_window(self):
        self.root.withdraw()

    def reset_config(self):
        """重置配置文件并重启"""
        if messagebox.askyesno("重置", "确定要重置热键吗？程序将关闭，下次启动时需重新录制。"):
            try:
                if os.path.exists(CONFIG_FILE):
                    os.remove(CONFIG_FILE)
                self.root.destroy()
                os._exit(0)
            except Exception as e:
                messagebox.showerror("错误", f"无法删除配置文件: {str(e)}")

    def perform_type(self):
        text = self.text_entry.get()
        salt = self.salt_entry.get()

        if not text:
            self.status_label.config(text="请输入记忆口令！", foreground="red")
            return

        try:
            msg_bytes = text.encode('utf-8')
            salt_bytes = salt.encode('utf-8')
            hash_hex = sm3.sm3_hash(func.bytes_to_list(msg_bytes + salt_bytes))
        except Exception as e:
            self.status_label.config(text=f"错误: {str(e)}", foreground="red")
            return

        self.hide_window()
        threading.Thread(target=self._type_hash, args=(hash_hex,)).start()

    def _type_hash(self, text_to_type):
        time.sleep(0.2)
        keyboard.write(text_to_type)
        print(f"已输入哈希: {text_to_type[:6]}...")

    def run(self):
        self.root.mainloop()


def start_main_app(hotkey):
    """启动主程序逻辑"""
    print(f"✅ 正在启动主程序，监听热键: {hotkey}")
    app = SM3AutoTyper(hotkey)

    try:
        keyboard.add_hotkey(hotkey, app.show_window)
    except Exception as e:
        messagebox.showerror("热键错误",
                             f"无法注册热键 '{hotkey}'\n可能被占用或格式错误。\n请删除 {CONFIG_FILE} 后重试。")
        return

    app.run()


if __name__ == "__main__":
    saved_hotkey = None

    # 1. 尝试读取配置文件
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                saved_hotkey = data.get("hotkey")
        except Exception as e:
            print(f"读取配置出错: {e}")
            saved_hotkey = None

    # 2. 根据读取结果决定 启动主程序 还是 录制热键
    if saved_hotkey:
        start_main_app(saved_hotkey)
    else:
        recorder = HotkeyRecorder(start_main_app)
        recorder.run()