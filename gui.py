import customtkinter as ctk
import threading
import sys
import os
import queue
import re
import csv
import time
import platform

import generate_accounts
import signin_accounts
import export_utils
import tag_manager
import csv_utils
import megatools_helper
import proxy_manager
from colorama import Fore
from PIL import Image
from tkinter import messagebox, filedialog

# Configure global appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Constants & Colors ---
COLOR_PRIMARY = "#2cc985"
COLOR_PRIMARY_HOVER = "#23a16a"

COLOR_SECONDARY = "#1f6aa5"
COLOR_SECONDARY_HOVER = "#144870"

COLOR_DANGER = "#c92c2c"
COLOR_DANGER_HOVER = "#962121"

COLOR_BG_DARK = "#1a1a1a"
COLOR_CARD_BG = "#2b2b2b"
COLOR_TEXT_MAIN = "#ffffff"
COLOR_TEXT_SUB = "#cccccc"

FONT_MAIN = ("Segoe UI", 13) if platform.system() == "Windows" else ("Roboto", 13)
FONT_HEADER = ("Segoe UI Semibold", 20) if platform.system() == "Windows" else ("Roboto Medium", 20)
FONT_SUBHEADER = ("Segoe UI Semibold", 15) if platform.system() == "Windows" else ("Roboto Medium", 15)

MAX_THREADS = 8


class MegaGenGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Mega Account Generator GUI")
        self.geometry("900x600")

        try:
            self.iconbitmap(resource_path("logo.ico"))
        except Exception as e:
            print(f"Icon load error: {e}")

        self.configure(fg_color=COLOR_BG_DARK)
        
        # --- Layout Configuration ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.log_queue = queue.Queue()
        self.is_running = False

        # --- Check megatools availability at startup ---
        available, info = megatools_helper.is_megatools_available()
        if not available:
            self.after(100, lambda: messagebox.showwarning(
                "megatools Not Found",
                f"{info}\n\nAccount generation and sign-in will not work until megatools is installed."
            ))

        # --- Sidebar (Left) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="MEGA\nGenerator", font=("Roboto", 26, "bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_nav_gen = ctk.CTkButton(self.sidebar_frame, text="Generator", command=self.show_generator,
                                         fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                         anchor="w", width=180, font=FONT_SUBHEADER)
        self.btn_nav_gen.grid(row=1, column=0, padx=10, pady=10)

        self.btn_nav_acc = ctk.CTkButton(self.sidebar_frame, text="Stored Accounts", command=self.show_accounts,
                                         fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                         anchor="w", width=180, font=FONT_SUBHEADER)
        self.btn_nav_acc.grid(row=2, column=0, padx=10, pady=10)

        self.sidebar_frame.grid_rowconfigure(3, weight=1)
        try:
            pil_image = Image.open(resource_path("logo.png"))
            self.logo_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(100, 100))
            self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="", image=self.logo_image)
            self.logo_label.grid(row=4, column=0, padx=20, pady=20, sticky="s")
        except Exception as e:
            print(f"Logo load error: {e}")

        # --- Main Content Area (Right) ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # Initialize Views
        self.generator_view = GeneratorView(self.main_frame, self)
        self.accounts_view = AccountsView(self.main_frame, self)
        
        # Default view
        self.show_generator()

        # Redirect backend logs
        generate_accounts.set_log_callback(self.append_log)
        signin_accounts.set_log_callback(self.append_log)
        
        self.status_queue = queue.Queue()
        generate_accounts.set_status_callback(self.append_status)
        
        # Start log and status pollers
        self.after(100, self.poll_log_queue)
        self.after(100, self.poll_status_queue)

    def show_generator(self):
        self.accounts_view.pack_forget()
        self.generator_view.pack(fill="both", expand=True)
        self.btn_nav_gen.configure(fg_color=("gray75", "gray25"))
        self.btn_nav_acc.configure(fg_color="transparent")

    def show_accounts(self):
        self.generator_view.pack_forget()
        self.accounts_view.pack(fill="both", expand=True)
        self.accounts_view.load_accounts()
        self.btn_nav_gen.configure(fg_color="transparent")
        self.btn_nav_acc.configure(fg_color=("gray75", "gray25"))

    def append_log(self, message):
        self.log_queue.put(message)

    def append_status(self, index, email, status):
        self.status_queue.put((index, email, status))

    def poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if self.generator_view.winfo_exists():
                    self.generator_view.log_box.configure(state="normal")
                    clean_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(msg))
                    self.generator_view.log_box.insert("end", clean_msg + "\n")
                    # Cap log box at 500 lines to prevent memory/speed issues
                    line_count = int(self.generator_view.log_box.index("end-1c").split(".")[0])
                    if line_count > 500:
                        self.generator_view.log_box.delete("1.0", f"{line_count - 500}.0")
                    self.generator_view.log_box.see("end")
                    self.generator_view.log_box.configure(state="disabled")
        except queue.Empty:
            pass
        finally:
            self.after(100, self.poll_log_queue)
            
    def poll_status_queue(self):
        """Consume status updates from backend threads."""
        try:
            while True:
                index, email, status = self.status_queue.get_nowait()
                clean_status = re.sub(r'\x1b\[[0-9;]*m', '', str(status))
                clean_email = re.sub(r'\x1b\[[0-9;]*m', '', str(email))
                if self.generator_view.winfo_exists():
                    self.generator_view.metrics_label.configure(
                        text=f"Account {index}: {clean_email} - {clean_status}"
                    )
        except queue.Empty:
            pass
        finally:
            self.after(100, self.poll_status_queue)

    def confirm_stop(self):
        return messagebox.askyesno("Stop Process", "Are you sure you want to stop the current process?")

# --- Generator View ---
class GeneratorView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Settings Card
        self.settings_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10)
        self.settings_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 20))
        self.settings_frame.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(self.settings_frame, text="Generation Settings", font=FONT_HEADER, text_color=COLOR_TEXT_MAIN).grid(row=0, column=0, columnspan=4, sticky="w", padx=20, pady=15)

        # Inputs
        self.num_accounts_var = ctk.StringVar(value="3")
        self.num_threads_var = ctk.StringVar(value="3")
        self.password_var = ctk.StringVar(value="")

        self._create_input(self.settings_frame, 1, 0, "Accounts", self.num_accounts_var)
        self._create_input(self.settings_frame, 1, 1, f"Threads (Max {MAX_THREADS})", self.num_threads_var)
        self._create_input(self.settings_frame, 1, 2, "Common Password (Optional)", self.password_var)

        # Proxy toggle + Webshare API key
        self.proxy_var = ctk.BooleanVar(value=False)
        self.proxy_checkbox = ctk.CTkCheckBox(
            self.settings_frame, text="Use Proxies (bypass IP bans)",
            variable=self.proxy_var, font=FONT_MAIN, text_color=COLOR_TEXT_SUB,
            fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER,
            command=self._on_proxy_toggle
        )
        self.proxy_checkbox.grid(row=1, column=3, padx=20, pady=10, sticky="w")
        
        self.proxy_status_label = ctk.CTkLabel(self.settings_frame, text="", font=("Roboto", 10), text_color="gray60")
        self.proxy_status_label.grid(row=1, column=3, padx=20, pady=(35, 0), sticky="w")

        # Webshare multi-key section
        self.webshare_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.webshare_frame.grid(row=2, column=0, columnspan=4, padx=20, pady=(0, 5), sticky="ew")
        
        ws_row1 = ctk.CTkFrame(self.webshare_frame, fg_color="transparent")
        ws_row1.pack(fill="x")
        
        ctk.CTkLabel(ws_row1, text="Webshare API Keys (10 proxies each):", font=("Roboto", 11), text_color=COLOR_TEXT_SUB).pack(side="left")
        self.webshare_key_var = ctk.StringVar(value="")
        self.webshare_entry = ctk.CTkEntry(ws_row1, textvariable=self.webshare_key_var, width=280, height=28, placeholder_text="Paste API key → Click Add")
        self.webshare_entry.pack(side="left", padx=10)
        ctk.CTkButton(ws_row1, text="Add", fg_color=COLOR_SECONDARY, width=50, height=28, command=self._add_webshare_key).pack(side="left")
        ctk.CTkButton(ws_row1, text="Remove Last", fg_color="gray", width=80, height=28, command=self._remove_webshare_key).pack(side="left", padx=5)
        self.webshare_status_label = ctk.CTkLabel(ws_row1, text="", font=("Roboto", 10), text_color="gray60")
        self.webshare_status_label.pack(side="left", padx=10)

        # Action Buttons
        self.btn_gen = ctk.CTkButton(self.settings_frame, text="Start Generation", font=("Roboto", 14, "bold"),
                                     fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER, height=40,
                                     command=self.start_generation)
        self.btn_gen.grid(row=3, column=0, columnspan=2, padx=20, pady=20, sticky="ew")

        self.btn_signin = ctk.CTkButton(self.settings_frame, text="Check Storage / Sign In", font=("Roboto", 14, "bold"),
                                        fg_color=COLOR_SECONDARY, hover_color=COLOR_SECONDARY_HOVER, height=40,
                                        command=self.start_signin)
        self.btn_signin.grid(row=3, column=2, columnspan=2, padx=20, pady=20, sticky="ew")

        self.btn_stop = ctk.CTkButton(self.settings_frame, text="Stop", font=("Roboto", 14, "bold"),
                                      fg_color="gray", hover_color=COLOR_DANGER_HOVER, height=40,
                                      state="disabled", command=self.stop_process)
        self.btn_stop.grid(row=4, column=0, columnspan=4, padx=20, pady=(0, 20), sticky="ew")

        # Live Status Table
        self.log_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10)
        self.log_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.log_frame.grid_rowconfigure(1, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.log_frame, text="Activity Log", font=FONT_SUBHEADER, text_color=COLOR_TEXT_SUB).grid(row=0, column=0, sticky="w", padx=20, pady=10)

        self.log_box = ctk.CTkTextbox(self.log_frame, font=("Consolas", 12), fg_color="#1e1e1e", text_color="#d4d4d4")
        self.log_box.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.log_box.configure(state="disabled")

        self.metrics_label = ctk.CTkLabel(self.log_frame, text="Ready to start.", font=("Roboto", 12), text_color=COLOR_TEXT_SUB)
        self.metrics_label.grid(row=2, column=0, sticky="w", padx=20, pady=(10, 0))

        self.progress_bar = ctk.CTkProgressBar(self.log_frame, progress_color=COLOR_PRIMARY)
        self.progress_bar.grid(row=3, column=0, columnspan=2, padx=20, pady=20, sticky="ew")
        self.progress_bar.set(0)

    def _create_input(self, parent, row, col, label_text, variable):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=col, padx=20, pady=10, sticky="ew")
        ctk.CTkLabel(frame, text=label_text, font=FONT_MAIN, text_color=COLOR_TEXT_SUB).pack(anchor="w", pady=(0, 5))
        ctk.CTkEntry(frame, textvariable=variable, height=35).pack(fill="x")

    def _add_webshare_key(self):
        """Add a Webshare API key."""
        api_key = self.webshare_key_var.get().strip()
        if not api_key:
            self.webshare_status_label.configure(text="Enter API key", text_color=COLOR_DANGER)
            return
        
        self.webshare_status_label.configure(text="Adding...", text_color="gray60")
        
        def _add():
            try:
                count = proxy_manager.add_webshare_key(api_key)
                if count > 0:
                    total = len(proxy_manager.all_webshare)
                    self.controller.after(0, lambda: self.webshare_status_label.configure(
                        text=f"+{count} proxies (total: {total})", text_color=COLOR_PRIMARY))
                    self.controller.after(0, lambda: self.webshare_key_var.set(""))
                    self.controller.after(0, lambda: self.proxy_var.set(True))
                    self.controller.after(0, lambda: self._on_proxy_toggle())
                else:
                    self.controller.after(0, lambda: self.webshare_status_label.configure(
                        text="Invalid key or duplicate", text_color=COLOR_DANGER))
            except Exception as e:
                self.controller.after(0, lambda: self.webshare_status_label.configure(
                    text=f"Error: {str(e)[:30]}", text_color=COLOR_DANGER))
        
        threading.Thread(target=_add, daemon=True).start()

    def _remove_webshare_key(self):
        """Remove the last Webshare API key."""
        try:
            if proxy_manager.accounts:
                last = proxy_manager.accounts[-1]
                proxy_manager.remove_webshare_key(last.api_key)
                total = len(proxy_manager.all_webshare)
                self.webshare_status_label.configure(
                    text=f"Removed. Total: {total} proxies", text_color="gray60")
            else:
                self.webshare_status_label.configure(text="No keys to remove", text_color=COLOR_DANGER)
        except ImportError:
            pass

    def _on_proxy_toggle(self):
        """Enable/disable proxy rotation."""
        try:
            if self.proxy_var.get():
                # Check if Webshare is already connected
                if proxy_manager.all_webshare:
                    proxy_manager.enable()
                    count = len(proxy_manager.all_webshare)
                    status = f"Webshare: {count} proxies from {len(proxy_manager.accounts)} accounts"
                    self.proxy_status_label.configure(text=status, text_color=COLOR_PRIMARY)
                    return
                
                # Fall back to free proxies
                self.proxy_status_label.configure(text="Finding free proxies...", text_color="gray60")
                def _load():
                    count = proxy_manager.refresh_free_proxies(max_test=20)
                    status = f"{count} free proxies found"
                    color = COLOR_PRIMARY if count > 0 else COLOR_DANGER
                    self.controller.after(0, lambda: self.proxy_status_label.configure(text=status, text_color=color))
                    if count > 0:
                        proxy_manager.enable()
                threading.Thread(target=_load, daemon=True).start()
            else:
                proxy_manager.disable()
                self.proxy_status_label.configure(text="")
        except ImportError:
            self.proxy_status_label.configure(text="proxy_manager not found", text_color=COLOR_DANGER)

    def _validate_inputs(self):
        """Validate generation inputs. Returns (num, threads, password) or None on error."""
        try:
            num = int(self.num_accounts_var.get())
            threads = int(self.num_threads_var.get())
            password = self.password_var.get() or None
        except ValueError:
            self.controller.append_log("Error: Invalid number input.")
            return None

        if num < 1:
            self.controller.append_log("Error: Number of accounts must be at least 1.")
            return None

        if threads < 1:
            self.controller.append_log(f"Error: Thread count must be at least 1.")
            return None

        if threads > MAX_THREADS:
            self.controller.append_log(f"Error: Thread count cannot exceed {MAX_THREADS} due to Mail.tm rate limits.")
            return None

        return num, threads, password

    def start_generation(self):
        if self.controller.is_running: return
        
        validated = self._validate_inputs()
        if validated is None:
            return
        
        num, threads, password = validated

        # Reset stop flags
        generate_accounts.STOP_FLAG = False
        signin_accounts.STOP_FLAG = False

        self.controller.is_running = True
        self._toggle_buttons(False)
        self.progress_bar.set(0)
        
        threading.Thread(target=self._run_gen_thread, args=(num, threads, password), daemon=True).start()

    def start_signin(self):
        if self.controller.is_running: return
        
        # Reset stop flags
        generate_accounts.STOP_FLAG = False
        signin_accounts.STOP_FLAG = False

        self.controller.is_running = True
        self._toggle_buttons(False)
        self.progress_bar.set(0)
        threading.Thread(target=self._run_signin_thread, daemon=True).start()

    def stop_process(self):
        if not self.controller.is_running: return
        if self.controller.confirm_stop():
            generate_accounts.stop()
            signin_accounts.stop()
            self.controller.append_log("Stopping process...")
            self.btn_stop.configure(state="disabled", text="Stopping...")

    def _toggle_buttons(self, state):
        s = "normal" if state else "disabled"
        self.btn_gen.configure(state=s)
        self.btn_signin.configure(state=s)
        
        if not state:
            self.btn_stop.configure(state="normal", text="STOP", fg_color=COLOR_DANGER)
        else:
            self.btn_stop.configure(state="disabled", text="Stop", fg_color="gray")

    def _run_gen_thread(self, total, threads, password):
        self.controller.append_log(f"Starting generation of {total} accounts...")
        pbar = ProgressWrapper(self.progress_bar.set, total, self.controller)
        
        success_count = 0
        fail_count = 0
        total_time = 0
        
        try:
            if threads > 1:
                thread_list = []
                result_queue = queue.Queue()
                start_delay = max(3, 10 / threads)
                
                def thread_wrapper(idx, p, pw, q):
                    res = generate_accounts.new_account(idx, p, pw)
                    q.put(res)

                for i in range(total):
                    if generate_accounts.STOP_FLAG: break
                    t = threading.Thread(target=thread_wrapper, args=(i, pbar, password, result_queue))
                    thread_list.append(t)
                    t.start()
                    time.sleep(start_delay)
                
                for t in thread_list: t.join()
                
                while not result_queue.empty():
                    res = result_queue.get()
                    if res.get("success"): success_count += 1
                    else: fail_count += 1
                    total_time += res.get("time", 0)
            else:
                for i in range(total):
                    if generate_accounts.STOP_FLAG: break
                    res = generate_accounts.new_account(i, pbar, password)
                    if res.get("success"): success_count += 1
                    else: fail_count += 1
                    total_time += res.get("time", 0)
            
            avg_time = (total_time / total) if total > 0 else 0
            
            msg = f"Done. Success: {success_count} | Failed: {fail_count} | Total: {total} | Avg: {avg_time:.1f}s"
            if generate_accounts.STOP_FLAG: msg += " (Stopped)"
            
            self.metrics_label.configure(text=msg, text_color=COLOR_PRIMARY if success_count > 0 else COLOR_TEXT_SUB)
            self.controller.append_log(msg)

        except Exception as e:
            self.controller.append_log(f"Error: {e}")
        finally:
            self.controller.is_running = False
            self.progress_bar.set(1.0)
            self._toggle_buttons(True)

    def _run_signin_thread(self):
        try:
            if not csv_utils.csv_exists():
                self.controller.append_log("Error: accounts.csv not found.")
                return
            
            total = csv_utils.count_accounts()
            
            if total < 1:
                self.controller.append_log("No accounts to sign in.")
                return

            pbar = ProgressWrapper(self.progress_bar.set, total, self.controller)
            signin_accounts.main(pbar, check_only_storage=True)
            
            if signin_accounts.STOP_FLAG:
                self.controller.append_log("Sign In Stopped.")

        except Exception as e:
            self.controller.append_log(f"Error during sign in: {e}")
        finally:
            self.controller.is_running = False
            self.progress_bar.set(1.0)
            self._toggle_buttons(True)

# --- Accounts View ---
ACCOUNTS_PER_PAGE = 50

class AccountsView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.all_accounts = []
        self.filtered_accounts = []
        self.current_page = 0
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header Card
        self.header_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10, height=60)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 10))
        
        ctk.CTkLabel(self.header_frame, text="Stored Accounts", font=FONT_HEADER, text_color=COLOR_TEXT_MAIN).pack(side="left", padx=20, pady=15)
        
        btn_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        btn_frame.pack(side="right", padx=20)
        
        ctk.CTkButton(btn_frame, text="Export", width=80, command=self.show_export_menu, 
                     fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Import", width=80, command=self.show_import_menu,
                     fg_color=COLOR_SECONDARY, hover_color=COLOR_SECONDARY_HOVER).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Refresh", width=80, command=self.load_accounts, 
                     fg_color="transparent", border_width=1, text_color=COLOR_TEXT_MAIN).pack(side="left", padx=5)
        
        # Search & Filter Bar
        self.search_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10, height=60)
        self.search_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 10))
        
        ctk.CTkLabel(self.search_frame, text="Search:", font=("Roboto", 18)).pack(side="left", padx=(20, 5))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.apply_filters())
        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Search by email...", 
                                        textvariable=self.search_var, width=300)
        self.search_entry.pack(side="left", padx=5, pady=15)
        
        ctk.CTkLabel(self.search_frame, text="Filter:", text_color=COLOR_TEXT_SUB).pack(side="left", padx=(20, 5))
        self.filter_var = ctk.StringVar(value="All")
        self.filter_dropdown = ctk.CTkOptionMenu(self.search_frame, variable=self.filter_var,
                                                values=["All", "Active", "Failed", "Disabled", "Unknown"],
                                                command=lambda x: self.apply_filters(), width=120)
        self.filter_dropdown.pack(side="left", padx=5)

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10)
        self.scroll_frame.grid(row=2, column=0, sticky="nsew")

        # Pagination controls
        self.page_frame = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.page_frame.grid(row=3, column=0, sticky="ew", padx=0, pady=(5, 0))
        
        self.btn_prev = ctk.CTkButton(self.page_frame, text="< Prev", width=80,
                                      fg_color=COLOR_SECONDARY, hover_color=COLOR_SECONDARY_HOVER,
                                      command=self.prev_page, state="disabled")
        self.btn_prev.pack(side="left", padx=5)
        
        self.page_label = ctk.CTkLabel(self.page_frame, text="", font=("Roboto", 12), text_color=COLOR_TEXT_SUB)
        self.page_label.pack(side="left", padx=10)
        
        self.btn_next = ctk.CTkButton(self.page_frame, text="Next >", width=80,
                                      fg_color=COLOR_SECONDARY, hover_color=COLOR_SECONDARY_HOVER,
                                      command=self.next_page, state="disabled")
        self.btn_next.pack(side="left", padx=5)

    def load_accounts(self):
        """Load all accounts from CSV"""
        for w in self.scroll_frame.winfo_children(): w.destroy()
        
        rows = csv_utils.read_accounts()
            
        if not rows:
            ctk.CTkLabel(self.scroll_frame, text="No accounts found.", text_color=COLOR_TEXT_SUB).pack(pady=20)
            self.all_accounts = []
            self.filtered_accounts = []
            self._update_page_label()
            return
        
        self.all_accounts = rows
        
        base_filters = ["All", "Active", "Failed", "Disabled", "Unknown"]
        all_tags = tag_manager.TagManager.get_all_tags()
        
        self.filter_dropdown.configure(values=base_filters + all_tags)
        
        self.current_page = 0
        self.apply_filters()
    
    def apply_filters(self):
        """Filter accounts and display current page"""
        if not self.all_accounts:
            self.filtered_accounts = []
            self._render_page()
            return
        
        search_query = self.search_var.get().lower().strip()
        filter_status = self.filter_var.get()
        
        status_keywords = ["All", "Active", "Failed", "Disabled", "Unknown"]
        
        self.filtered_accounts = []
        for row in self.all_accounts:
            if not row:
                continue
            
            email = row[0].lower() if len(row) > 0 else ""
            status = row[4] if len(row) > 4 else "Unknown"
            
            tags_str = row[5] if len(row) > 5 else ""
            account_tags = [t.strip() for t in tags_str.split(',') if t.strip()]
            
            if search_query and search_query not in email:
                continue
            
            if filter_status != "All":
                if filter_status in status_keywords:
                    if filter_status == "Active" and status != "Active":
                        continue
                    elif filter_status == "Failed" and "Failed" not in status:
                        continue
                    elif filter_status == "Disabled" and status != "Disabled":
                        continue
                    elif filter_status == "Unknown" and status not in ["Unknown", ""]:
                        continue
                else:
                    if filter_status not in account_tags:
                        continue
            
            self.filtered_accounts.append(row)
        
        self.current_page = 0
        self._render_page()
    
    def _render_page(self):
        """Render only the current page of accounts."""
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        
        if not self.filtered_accounts:
            if self.all_accounts:
                ctk.CTkLabel(self.scroll_frame, text="No accounts match your search.", 
                            text_color=COLOR_TEXT_SUB).pack(pady=20)
            else:
                ctk.CTkLabel(self.scroll_frame, text="No accounts to display.", 
                            text_color=COLOR_TEXT_SUB).pack(pady=20)
            self._update_page_label()
            return
        
        total_pages = max(1, (len(self.filtered_accounts) + ACCOUNTS_PER_PAGE - 1) // ACCOUNTS_PER_PAGE)
        start = self.current_page * ACCOUNTS_PER_PAGE
        end = min(start + ACCOUNTS_PER_PAGE, len(self.filtered_accounts))
        page_rows = self.filtered_accounts[start:end]
        
        for row in page_rows:
            AccountRow(self.scroll_frame, row, self.load_accounts).pack(fill="x", padx=10, pady=5)
        
        self._update_page_label()
    
    def _update_page_label(self):
        total = len(self.filtered_accounts)
        total_pages = max(1, (total + ACCOUNTS_PER_PAGE - 1) // ACCOUNTS_PER_PAGE)
        self.page_label.configure(text=f"Page {self.current_page + 1}/{total_pages} ({total} accounts)")
        
        self.btn_prev.configure(state="normal" if self.current_page > 0 else "disabled")
        self.btn_next.configure(state="normal" if self.current_page < total_pages - 1 else "disabled")
    
    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._render_page()
    
    def next_page(self):
        total_pages = max(1, (len(self.filtered_accounts) + ACCOUNTS_PER_PAGE - 1) // ACCOUNTS_PER_PAGE)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._render_page()
    
    def show_export_menu(self):
        """Show export format selection dialog"""
        dialog = ExportDialog(self.winfo_toplevel(), self.controller)
    
    def show_import_menu(self):
        """Show import file selection dialog"""
        filetypes = [
            ("All supported", "*.json *.xlsx *.csv"),
            ("JSON files", "*.json"),
            ("Excel files", "*.xlsx"),
            ("CSV files", "*.csv"),
            ("All files", "*.*")
        ]
        
        filepath = filedialog.askopenfilename(
            title="Import Accounts",
            filetypes=filetypes
        )
        
        if not filepath:
            return
        
        try:
            if filepath.endswith('.json'):
                accounts = export_utils.import_from_json(filepath)
            elif filepath.endswith('.xlsx'):
                accounts = export_utils.import_from_excel(filepath)
            elif filepath.endswith('.csv'):
                accounts = export_utils.import_from_csv(filepath)
            else:
                messagebox.showerror("Error", "Unsupported file format. Use JSON, Excel, or CSV.")
                return
            
            if not accounts:
                messagebox.showwarning("No Accounts", "No valid accounts found in the file.")
                return
            
            if messagebox.askyesno("Confirm Import", 
                                  f"Import {len(accounts)} accounts? This will replace accounts.csv"):
                csv_utils.write_accounts(accounts)
                
                messagebox.showinfo("Success", f"Imported {len(accounts)} accounts successfully!")
                self.load_accounts()
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import: {str(e)}")

class AccountRow(ctk.CTkFrame):
    def __init__(self, parent, row_data, reload_cb):
        super().__init__(parent, fg_color="#333333", corner_radius=8)
        self.row_data = row_data
        self.reload_cb = reload_cb
        self.email = row_data[0]
        self.password = row_data[1]
        self.status = row_data[4] if len(row_data) > 4 else "Unknown"
        self.used = row_data[2] if len(row_data) > 2 else "?"
        self.free = row_data[3] if len(row_data) > 3 else "?"

        self.grid_columnconfigure(0, weight=1)
        self.pack_propagate(False)
        self.configure(height=60)

        # Email & Tags
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="w", padx=15, pady=5)
        
        email_color = "white"
        if self.status == "Disabled":
            email_color = "gray50"
        elif self.status == "Active":
            email_color = COLOR_PRIMARY
        elif "Failed" in self.status:
            email_color = COLOR_DANGER
            
        ctk.CTkLabel(info_frame, text=self.email, font=("Roboto", 13, "bold"), text_color=email_color).pack(anchor="w")
        
        tags = tag_manager.TagManager.get_account_tags(self.email)
        tag_text = ""
        if tags:
            tag_text = " ".join([f"[{t}]" for t in tags[:3]])
            if len(tags) > 3: tag_text += f" +{len(tags)-3}"
            
        if tag_text:
            ctk.CTkLabel(info_frame, text=tag_text, font=("Roboto", 10), text_color="gray70").pack(anchor="w")

        used_display = self.used if self.used and self.used != "?" else "N/A"
        free_display = self.free if self.free and self.free != "?" else "N/A"
        
        details = f"Pass: {self.password} | St: {self.status} | Used: {used_display}  Free: {free_display}"
        ctk.CTkLabel(self, text=details, font=("Roboto", 11), text_color="gray60", anchor="w").grid(row=1, column=0, padx=15, pady=(0, 5), sticky="w")
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=1, rowspan=2, padx=10)

        self._make_btn(btn_frame, "Copy Email", self.copy_email, COLOR_SECONDARY, width=70)
        self._make_btn(btn_frame, "Copy Pass", self.copy_pass, COLOR_SECONDARY, width=70)
        self._make_btn(btn_frame, "Edit", self.edit_pass, "gray40", width=50)
        self._make_btn(btn_frame, "Tags", self.edit_tags, "gray40", width=50)
        
        if self.status == "Disabled":
            self._make_btn(btn_frame, "Enable", self.toggle_status, COLOR_PRIMARY, width=60)
        else:
            self._make_btn(btn_frame, "Disable", self.toggle_status, COLOR_DANGER, width=60)

    def _make_btn(self, parent, text, cmd, col, width=80):
        ctk.CTkButton(parent, text=text, command=cmd, fg_color=col, width=width, height=24, font=("Roboto", 11)).pack(side="left", padx=2)

    def copy_email(self):
        self.clipboard_clear()
        self.clipboard_append(self.email)

    def copy_pass(self):
        self.clipboard_clear()
        self.clipboard_append(self.password)

    def edit_pass(self):
        EditPasswordDialog(self.winfo_toplevel(), self.password, self._on_pass_change)

    def edit_tags(self):
        TagEditDialog(self.winfo_toplevel(), self.email, self.reload_cb)

    def _on_pass_change(self, new_pass):
        if new_pass:
            self._update_cell(1, new_pass)
            self.reload_cb()

    def toggle_status(self):
        new_status = "Unknown" if self.status == "Disabled" else "Disabled"
        self._update_cell(4, new_status)
        self.reload_cb()

    def _update_cell(self, col_index, new_value):
        try:
             csv_utils.update_account(self.email, col_index, new_value)
        except Exception as e:
            print(f"Error updating CSV: {e}")

class EditPasswordDialog(ctk.CTkToplevel):
    def __init__(self, parent, current_pass, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("Edit Password")
        self.geometry("300x150")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        x_pos = parent_x + (parent_width // 2) - (300 // 2)
        y_pos = parent_y + (parent_height // 2) - (150 // 2)
        self.geometry(f"300x150+{x_pos}+{y_pos}")

        ctk.CTkLabel(self, text="Enter new password:", font=("Roboto", 13)).pack(pady=(20, 10))
        
        self.entry = ctk.CTkEntry(self, width=200)
        self.entry.insert(0, current_pass)
        self.entry.pack(pady=5)
        self.entry.focus()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", width=80, command=self.destroy).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Save", fg_color=COLOR_PRIMARY, width=80, command=self.save).pack(side="left", padx=5)
        
        self.bind("<Return>", lambda event: self.save())

    def save(self):
        new_pass = self.entry.get()
        if new_pass:
            self.callback(new_pass)
        self.destroy()

# --- Helper ---
class ProgressWrapper:
    def __init__(self, callback, total, controller=None):
        self.callback = callback
        self.total = total
        self.current = 0
        self.controller = controller

    def update(self, n=1):
        self.current += n
        val = self.current / self.total if self.total > 0 else 0
        if self.controller:
            self.controller.after(0, lambda v=val: self.callback(v))
        else:
            self.callback(val)

# --- Export Dialog ---
class ExportDialog(ctk.CTkToplevel):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.title("Export Accounts")
        self.geometry("400x300")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        x_pos = parent_x + (parent_width // 2) - (400 // 2)
        y_pos = parent_y + (parent_height // 2) - (300 // 2)
        self.geometry(f"400x300+{x_pos}+{y_pos}")
        
        ctk.CTkLabel(self, text="Select Export Format", font=FONT_HEADER).pack(pady=(30, 20))
        
        self.format_var = ctk.StringVar(value="json")
        
        ctk.CTkRadioButton(self, text="JSON (Lightweight, Human-readable)", 
                          variable=self.format_var, value="json").pack(pady=10)
        ctk.CTkRadioButton(self, text="Excel (Formatted, Spreadsheet)", 
                          variable=self.format_var, value="excel").pack(pady=10)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=30)
        
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", width=100, 
                     command=self.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Export", fg_color=COLOR_PRIMARY, width=100, 
                     command=self.export_accounts).pack(side="left", padx=10)
    
    def export_accounts(self):
        format_type = self.format_var.get()
        
        if format_type == "json":
            filetypes = [("JSON files", "*.json")]
            default_ext = ".json"
        else:
            filetypes = [("Excel files", "*.xlsx")]
            default_ext = ".xlsx"
        
        filepath = filedialog.asksaveasfilename(
            title="Export Accounts",
            filetypes=filetypes,
            defaultextension=default_ext
        )
        
        if not filepath:
            return
        
        try:
            rows = csv_utils.read_accounts()
            
            if format_type == "json":
                count = export_utils.export_to_json(rows, filepath)
            else:
                count = export_utils.export_to_excel(rows, filepath)
            
            messagebox.showinfo("Success", f"Exported {count} accounts to {format_type.upper()}")
            self.destroy()
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            messagebox.showerror("Export Error", f"Failed to export:\n\n{str(e)}\n\nDetails:\n{error_details}")

# --- Tag Edit Dialog ---
class TagEditDialog(ctk.CTkToplevel):
    def __init__(self, parent, email, reload_cb):
        super().__init__(parent)
        self.email = email
        self.reload_cb = reload_cb
        self.title(f"Edit Tags - {email}")
        self.geometry("400x350")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        x_pos = parent_x + (parent_width // 2) - (400 // 2)
        y_pos = parent_y + (parent_height // 2) - (350 // 2)
        self.geometry(f"400x350+{x_pos}+{y_pos}")
        
        self.current_tags = tag_manager.TagManager.get_account_tags(email)
        
        ctk.CTkLabel(self, text="Account Tags", font=FONT_HEADER).pack(pady=(20, 10))
        
        self.tags_frame = ctk.CTkScrollableFrame(self, height=150)
        self.tags_frame.pack(fill="x", padx=20, pady=10)
        self.refresh_tags_display()
        
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=20, pady=10)
        
        self.tag_entry = ctk.CTkEntry(input_frame, placeholder_text="Enter new tag...")
        self.tag_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.tag_entry.bind("<Return>", lambda e: self.add_tag())
        
        ctk.CTkButton(input_frame, text="Add", width=60, command=self.add_tag,
                     fg_color=COLOR_PRIMARY).pack(side="left")
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(btn_frame, text="Done", width=100, command=self.on_done,
                     fg_color=COLOR_PRIMARY).pack(side="left", padx=5)
    
    def refresh_tags_display(self):
        for w in self.tags_frame.winfo_children():
            w.destroy()
        
        if not self.current_tags:
            ctk.CTkLabel(self.tags_frame, text="No tags yet", 
                        text_color=COLOR_TEXT_SUB).pack(pady=10)
            return
        
        for tag in self.current_tags:
            tag_row = ctk.CTkFrame(self.tags_frame, fg_color="#333333")
            tag_row.pack(fill="x", pady=2)
            
            ctk.CTkLabel(tag_row, text=f"[{tag}]", font=("Roboto", 12),
                        text_color="white").pack(side="left", padx=10, pady=5)
            
            ctk.CTkButton(tag_row, text="X", width=30, height=25,
                         command=lambda t=tag: self.remove_tag(t),
                         fg_color=COLOR_DANGER, hover_color="#C62828").pack(side="right", padx=5)
    
    def add_tag(self):
        tag = self.tag_entry.get().strip()
        if tag and tag not in self.current_tags:
            self.current_tags.append(tag)
            tag_manager.TagManager.set_account_tags(self.email, self.current_tags)
            self.tag_entry.delete(0, 'end')
            self.refresh_tags_display()
    
    def remove_tag(self, tag):
        if tag in self.current_tags:
            self.current_tags.remove(tag)
            tag_manager.TagManager.set_account_tags(self.email, self.current_tags)
            self.refresh_tags_display()
    
    def on_done(self):
        self.reload_cb()
        self.destroy()

if __name__ == "__main__":
    app = MegaGenGUI()
    app.mainloop()
