import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
import time
import threading
from gmssl import sm3, func
import json
import os
import base64
import string

# Configuration file name
CONFIG_FILE = "smassword_config.json"


class HotkeyRecorder:
    """
    Window class specifically for recording hotkey during first run
    """

    def __init__(self, on_complete_callback):
        self.root = tk.Tk()
        self.root.title("First Run Setup")
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

        ttk.Label(frame, text="Welcome to SM3 Auto Typer", font=("Arial", 12, "bold")).pack(pady=5)
        ttk.Label(frame, text="This appears to be your first run.\nPlease set your global activation hotkey.", justify="center").pack(pady=5)

        self.status_label = ttk.Label(frame, text="Click button below to start recording", foreground="gray")
        self.status_label.pack(pady=10)

        self.btn = ttk.Button(frame, text="Start Recording Hotkey", command=self.start_recording)
        self.btn.pack(pady=5)

    def start_recording(self):
        self.btn.config(state="disabled")
        self.status_label.config(text="Please press a key combination (e.g., Ctrl+Alt+Z)...", foreground="blue")
        threading.Thread(target=self._record_thread).start()

    def _record_thread(self):
        try:
            hotkey = keyboard.read_hotkey(suppress=False)
            self.root.after(0, lambda: self._finish_recording(hotkey))
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text="Recording failed, please try again", foreground="red"))
            self.root.after(0, lambda: self.btn.config(state="normal"))

    def _finish_recording(self, hotkey):
        config_data = {"hotkey": hotkey}
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f)

            self.status_label.config(text=f"Success! Hotkey set to: {hotkey}", foreground="green")
            self.root.update()
            time.sleep(1)
            self.root.destroy()
            self.on_complete(hotkey)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
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

        width, height = 400, 220
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.resizable(False, False)

        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        hotkey_info = ttk.Label(main_frame, text=f"Current hotkey: {self.current_hotkey}", font=("Arial", 8),
                                foreground="#666")
        hotkey_info.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        # === 1. Passphrase ===
        ttk.Label(main_frame, text="Passphrase:").grid(row=1, column=0, sticky="w")
        self.text_entry = ttk.Entry(main_frame, width=28, show="*")
        self.text_entry.grid(row=1, column=1, pady=5, padx=5)
        self.text_entry.bind('<Return>', lambda e: self.salt_entry.focus_set())

        self.show_text_var = tk.BooleanVar(value=False)
        self.btn_eye_text = ttk.Checkbutton(main_frame, text="👁", variable=self.show_text_var,
                                            style='Toolbutton', command=self.toggle_text_visibility)
        self.btn_eye_text.grid(row=1, column=2, padx=2)

        # === 2. Salt ===
        ttk.Label(main_frame, text="Salt:").grid(row=2, column=0, sticky="w")
        self.salt_entry = ttk.Entry(main_frame, width=28, show="*")
        self.salt_entry.grid(row=2, column=1, pady=5, padx=5)
        self.salt_entry.bind('<Return>', lambda e: self.len_entry.focus_set())

        self.show_salt_var = tk.BooleanVar(value=False)
        self.btn_eye_salt = ttk.Checkbutton(main_frame, text="👁", variable=self.show_salt_var,
                                            style='Toolbutton', command=self.toggle_salt_visibility)
        self.btn_eye_salt.grid(row=2, column=2, padx=2)

        # === 3. Length ===
        ttk.Label(main_frame, text="Password length:").grid(row=3, column=0, sticky="w")
        self.len_var = tk.StringVar(value="16")
        self.len_entry = ttk.Spinbox(main_frame, from_=8, to=32, textvariable=self.len_var, width=5)
        self.len_entry.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        self.len_entry.bind('<Return>', lambda e: self.perform_type())

        ttk.Label(main_frame, text="(uppercase + lowercase + symbols)").grid(row=3, column=1, padx=(60, 0))

        # === 4. Buttons ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=15)

        ttk.Button(btn_frame, text="Confirm and Type (Enter)", command=self.perform_type).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Hide", command=self.hide_window).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Reset Hotkey", command=self.reset_config).pack(side='left', padx=5)

        self.status_label = ttk.Label(main_frame, text="Waiting for input...", foreground="gray", font=("Arial", 8))
        self.status_label.grid(row=5, column=0, columnspan=3)

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
        self.status_label.config(text="Press Enter after input", foreground="gray")

    def hide_window(self):
        self.root.withdraw()

    def reset_config(self):
        if messagebox.askyesno("Reset", "Are you sure you want to reset the hotkey? The program will close and you'll need to re-record on next launch."):
            try:
                if os.path.exists(CONFIG_FILE):
                    os.remove(CONFIG_FILE)
                self.root.destroy()
                os._exit(0)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot delete config file: {str(e)}")

    def perform_type(self):
        text = self.text_entry.get()
        salt = self.salt_entry.get()
        try:
            length = int(self.len_var.get())
        except:
            length = 16

        if not text:
            self.status_label.config(text="Please enter passphrase!", foreground="red")
            return

        try:
            msg_bytes = text.encode('utf-8')
            salt_bytes = salt.encode('utf-8')
            hex_str = sm3.sm3_hash(func.bytes_to_list(msg_bytes + salt_bytes))
            final_password = self._generate_complex_pwd(hex_str, length)
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", foreground="red")
            print(e)
            return

        self.hide_window()
        threading.Thread(target=self._type_hash, args=(final_password,)).start()

    def _generate_complex_pwd(self, hex_hash, length):
        raw_bytes = bytes.fromhex(hex_hash)
        b64_bytes = base64.b64encode(raw_bytes)
        b64_str = b64_bytes.decode('utf-8')

        candidate = list(b64_str[:length])

        upper_pool = string.ascii_uppercase
        lower_pool = string.ascii_lowercase
        digit_pool = string.digits
        symbol_pool = "!@#$%&*"

        hex_ptr = len(hex_hash) - 1

        def ensure_category(pool, replace_index):
            nonlocal hex_ptr
            if not any(c in pool for c in candidate):
                seed_hex = hex_hash[hex_ptr - 1: hex_ptr + 1]
                seed_int = int(seed_hex, 16)
                hex_ptr -= 2
                char_to_inject = pool[seed_int % len(pool)]
                idx = replace_index % len(candidate)
                candidate[idx] = char_to_inject

        ensure_category(upper_pool, 0)
        ensure_category(lower_pool, 1)
        ensure_category(digit_pool, 2)
        ensure_category(symbol_pool, 3)

        return "".join(candidate)

    def _type_hash(self, text_to_type):
        time.sleep(0.3)
        keyboard.write(text_to_type)
        print(f"Password typed: {text_to_type[:3]}***")

    def run(self):
        self.root.mainloop()


def start_main_app(hotkey):
    print(f"✅ Starting main application, listening for hotkey: {hotkey}")
    app = SM3AutoTyper(hotkey)

    try:
        keyboard.add_hotkey(hotkey, app.show_window)
    except Exception as e:
        messagebox.showerror("Hotkey Error",
                             f"Cannot register hotkey '{hotkey}'\nMay be occupied or format error.\nPlease delete {CONFIG_FILE} and try again.")
        return

    app.run()


if __name__ == "__main__":
    saved_hotkey = None
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                saved_hotkey = data.get("hotkey")
        except Exception as e:
            print(f"Error reading config: {e}")
            saved_hotkey = None

    if saved_hotkey:
        start_main_app(saved_hotkey)
    else:
        recorder = HotkeyRecorder(start_main_app)
        recorder.run()