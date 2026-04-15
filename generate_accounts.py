# Create New Mega Accounts (CODESPACE & TOR EDITION)
import subprocess
import os
import sys
import time
import re
import random
import string
import threading
import argparse
import logging
import pymailtm
import megatools_helper
import csv_utils
from pymailtm.pymailtm import CouldNotGetAccountException, CouldNotGetMessagesException
from faker import Faker
from tqdm import tqdm
from colorama import init, Fore, Style

# ==========================================
# BHAI KA JUGAAD: CODESPACE TOR PROXY SETUP
# Ye lines saara traffic Tor ke raaste bhejengi
os.environ['http_proxy'] = 'socks5h://127.0.0.1:9050'
os.environ['https_proxy'] = 'socks5h://127.0.0.1:9050'
os.environ['ALL_PROXY'] = 'socks5h://127.0.0.1:9050'
# ==========================================

init(autoreset=True)

logging.basicConfig(
    filename='debug.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

fake = Faker()
print_lock = threading.Lock()
status_lock = threading.Lock()
vpn_lock = threading.Lock() # Prevents multiple threads from resetting Tor together

def check_limit(value):
    ivalue = int(value)
    if ivalue < 1: raise argparse.ArgumentTypeError("Min 1 thread.")
    if ivalue > 8: raise argparse.ArgumentTypeError("Max 8 threads allowed.")
    return ivalue

log_callback = None
status_callback = None
STOP_FLAG = False

def stop():
    global STOP_FLAG
    STOP_FLAG = True

def set_log_callback(callback): global log_callback = callback
def set_status_callback(callback): global status_callback = callback

def safe_print(message, color=Fore.WHITE):
    clean_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(message))
    logging.info(clean_msg)
    if log_callback: log_callback(message)
    if sys.stdout is not None:
        with print_lock:
            try: tqdm.write(f"{color}{message}{Style.RESET_ALL}")
            except Exception: pass

def update_status(index, email, status):
    if status_callback:
        with status_lock: status_callback(index, email, status)

parser = argparse.ArgumentParser(description="Create New Mega Accounts")
parser.add_argument("-n", "--number", type=int, default=3, help="Number of accounts")
parser.add_argument("-t", "--threads", type=check_limit, default=None, help="Threads")
parser.add_argument("-p", "--password", type=str, default=None, help="Password")
args = parser.parse_args()

def find_url(string):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex, string)
    return [x[0] for x in url]

def get_random_string(length):
    letters = string.ascii_lowercase + string.ascii_uppercase + string.digits
    return "".join(random.choice(letters) for _ in range(length))

class MegaAccount:
    def __init__(self, index, name, password):
        self.index = index
        self.name = name
        self.password = password
        self.email = None
        self.email_id = None
        self.email_password = None
        self.verify_command = None

    def generate_mail(self):
        update_status(self.index, "Generating Email...", "Pending")
        # Retry loop badha kar 50 kar diya hai
        for i in range(50):
            if STOP_FLAG: return False
            try:
                mail = pymailtm.MailTm()
                acc = mail.get_account()
                self.email = acc.address
                self.email_id = acc.id_
                self.email_password = acc.password
                update_status(self.index, self.email, "Email Generated")
                return True
            except CouldNotGetAccountException:
                # AUTO TOR ROTATION
                if vpn_lock.acquire(blocking=False):
                    try:
                        safe_print(f"> [{self.index}] IP Blocked! Auto-Rotating Tor IP... (Attempt {i+1}/50)", Fore.YELLOW)
                        update_status(self.index, "Changing IP...", "Blocked")
                        os.system('sudo service tor restart > /dev/null 2>&1')
                        safe_print(f"> [{self.index}] Nayi IP mil rahi hai. 12 seconds wait karo...", Fore.CYAN)
                        time.sleep(12) 
                    finally:
                        vpn_lock.release()
                else:
                    safe_print(f"> [{self.index}] Waiting for Tor IP rotation...", Fore.YELLOW)
                    update_status(self.index, "Waiting IP...", "Blocked")
                    time.sleep(15)
        
        safe_print("Could not get account even after 50 retries.", Fore.RED)
        update_status(self.index, "Failed", "Perma-Blocked")
        return False

    def get_mail(self):
        try:
            mail = pymailtm.Account(self.email_id, self.email, self.email_password)
            messages = mail.get_messages()
            if not messages: return None
            return messages[0]
        except (CouldNotGetAccountException, CouldNotGetMessagesException):
            return None

    def register(self):
        if not self.generate_mail(): return False
        safe_print(f"> [{self.email}]: Registering account...", Fore.CYAN)
        update_status(self.index, self.email, "Registering...")

        registration = megatools_helper.run_megatools_command(
            ["reg", "--scripted", "--register", "--email", self.email, "--name", self.name, "--password", self.password],
            universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        if registration.returncode != 0:
            err = registration.stderr.strip()
            safe_print(f"> [{self.email}]: Registration failed: {err}", Fore.RED)
            return False

        self.verify_command = registration.stdout.strip()
        return True

    def verify(self):
        if not self.verify_command: return False
        confirm_message = None
        # Tor ki vajah se thoda delay ho sakta hai isliye wait time badha diya (20)
        for i in range(20):
            if STOP_FLAG: return False
            confirm_message = self.get_mail()
            if confirm_message:
                links = find_url(confirm_message.text)
                if links and any("mega" in link.lower() for link in links): break
                if "verification" in confirm_message.subject.lower(): break
            safe_print(f"> [{self.email}]: Waiting for verification email... ({i+1}/20)", Fore.YELLOW)
            time.sleep(5)

        if not confirm_message:
            safe_print(f"> [{self.email}]: Timeout. No email received.", Fore.RED)
            return False

        links = find_url(confirm_message.text)
        if not links: return False
        self.verify_command = self.verify_command.replace("@LINK@", links[0])
        
        import shlex
        cmd_parts = shlex.split(self.verify_command)
        if cmd_parts and cmd_parts[0] == "megatools": cmd_parts = cmd_parts[1:]
        
        verification = megatools_helper.run_megatools_command(
            cmd_parts, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        if "registered successfully!" in verification.stdout.lower():
            safe_print(f"> [{self.email}] Successfully registered!", Fore.GREEN)
            csv_utils.append_account([self.email, self.password, "0 B", "20 GB", "Active", "Pharma-Archive", self.email_password, self.email_id])
            return True
        return False

def new_account(index=0, pbar=None, password=None):
    if STOP_FLAG: return {"success": False, "time": 0}
    start_time = time.time()
    if password is None:
        password = args.password if args.password else get_random_string(random.randint(10, 16))
    
    acc = MegaAccount(index, fake.name(), password)
    success = False
    if acc.register():
        if not STOP_FLAG:
            if acc.verify(): success = True
    
    if pbar: pbar.update(1)
    return {"success": success, "time": time.time() - start_time}

if __name__ == "__main__":
    csv_utils.initialize_csv()
    safe_print(f"Starting generation of {args.number} accounts via Tor Proxy...", Fore.MAGENTA)
    
    with tqdm(total=args.number, desc="Total Progress", unit="acc") as pbar:
        if args.threads:
            threads = []
            for i in range(args.number):
                t = threading.Thread(target=new_account, args=(i, pbar, args.password))
                threads.append(t)
                t.start()
                time.sleep(1.5) # Gap to prevent instant IP flag
            for t in threads: t.join()
        else:
            for i in range(args.number): new_account(i, pbar, args.password)

    safe_print("\nDone! Check accounts.csv", Fore.GREEN + Style.BRIGHT)
