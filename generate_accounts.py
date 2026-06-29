# Create New Mega Accounts
# saves credentials to a file called accounts.csv

import subprocess
import os
import sys
import time
import re
import random
import string
import csv
import threading
import argparse
import logging
import platform
import shlex
import megatools_helper
import csv_utils
import mailtm_client
from faker import Faker
from tqdm import tqdm
from colorama import init, Fore, Style

CREATION_FLAGS = megatools_helper.CREATION_FLAGS

# Initialize colorama
init(autoreset=True)

# Configure Logging
logging.basicConfig(
    filename='debug.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

fake = Faker()

# Lock for thread-safe operations
print_lock = threading.Lock()
status_lock = threading.Lock()
mail_request_lock = threading.Lock()
mail_request_times = []

# Custom function for checking if the argument is below a certain value
def check_limit(value):
    ivalue = int(value)
    if ivalue < 1:
        raise argparse.ArgumentTypeError("Number of threads must be at least 1.")
    if ivalue > 8:
        raise argparse.ArgumentTypeError("You cannot use more than 8 threads due to Mail.tm rate limits.")
    return ivalue

def rate_limit_mail_request():
    """Implement rate limiting for Mail.tm requests to avoid blocks."""
    with mail_request_lock:
        now = time.time()
        global mail_request_times
        mail_request_times = [t for t in mail_request_times if now - t < 60]
        
        # Allow max 8 requests per minute to Mail.tm
        if len(mail_request_times) >= 8:
            wait_time = 60 - (now - mail_request_times[0])
            if wait_time > 0:
                time.sleep(wait_time)
        
        mail_request_times.append(time.time())

# Global callbacks for GUI
log_callback = None
status_callback = None

STOP_FLAG = False

def stop():
    global STOP_FLAG
    STOP_FLAG = True

def set_log_callback(callback):
    global log_callback
    log_callback = callback

def set_status_callback(callback):
    global status_callback
    status_callback = callback

def safe_print(message, color=Fore.WHITE):
    clean_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(message))
    logging.info(clean_msg)
    
    if log_callback:
        log_callback(message)
    
    if sys.stdout is not None:
        with print_lock:
            try:
                tqdm.write(f"{color}{message}{Style.RESET_ALL}")
            except Exception:
                pass

def update_status(index, email, status):
    if status_callback:
        with status_lock:
            status_callback(index, email, status)


def find_url(string):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»""'']))"
    url = re.findall(regex, string)
    return [x[0] for x in url]

def get_random_string(length):
    """Generate a random string with a given length."""
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
        """Generate mail.tm account via direct API (bypasses buggy pymailtm)."""
        update_status(self.index, "Generating Email...", "Pending")
        for i in range(5):
            try:
                rate_limit_mail_request()
                acc = mailtm_client.create_account(max_retries=3)
                if acc is None:
                    raise Exception("mail.tm account creation returned None")
                self.email = acc.address
                self.email_id = acc.id_
                self.email_password = acc.password
                update_status(self.index, self.email, "Email Generated")
                return True
            except Exception as e:
                backoff = min(8 * (2 ** i), 128)
                safe_print(f"> Could not get new Mail.tm account: {e}. Retrying ({i+1} of 5) in {backoff}s...", Fore.YELLOW)
                time.sleep(backoff)
        
        safe_print("Could not get account. You are most likely blocked from Mail.tm.", Fore.RED)
        update_status(self.index, "Failed", "Mail.tm Blocked")
        return False

    def get_mail(self):
        """Get the latest email from the mail.tm account"""
        try:
            messages = mailtm_client.session_get_messages(
                mailtm_client.MailTmAccount(self.email, self.email_id, self.email_password)
            )
            if not messages:
                return None
            msg = messages[0]
            # Wrap dict in a simple object for attribute access
            class MsgWrapper:
                def __init__(self, data):
                    self._data = data
                @property
                def text(self):
                    return self._data.get("text", "") or self._data.get("intro", "") or ""
                @property
                def subject(self):
                    return self._data.get("subject", "") or ""
            return MsgWrapper(msg)
        except Exception as e:
            logging.error(f"Error fetching mail for {self.email}: {e}")
            return None

    def register(self):
        if not self.generate_mail():
            return False

        safe_print(f"> [{self.email}]: Registering account...", Fore.CYAN)
        update_status(self.index, self.email, "Registering...")

        registration = megatools_helper.run_megatools_command(
            [
                "reg",
                "--scripted",
                "--register",
                "--email",
                self.email,
                "--name",
                self.name,
                "--password",
                self.password,
            ],
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATION_FLAGS,
            timeout=120,
        )

        if registration.returncode != 0:
            err = registration.stderr.strip()
            safe_print(f"> [{self.email}]: Registration failed: {err}", Fore.RED)
            update_status(self.index, self.email, f"Reg Failed: {err[:20]}")
            return False

        self.verify_command = registration.stdout.strip()
        update_status(self.index, self.email, "Verifying...")
        return True

    def verify(self):
        if not self.verify_command:
            return False

        confirm_message = None
        for i in range(12):
            if STOP_FLAG:
                safe_print(f"> [{self.email}]: Process stopped by user.", Fore.YELLOW)
                update_status(self.index, self.email, "Stopped")
                return False
                
            confirm_message = self.get_mail()
            if confirm_message:
                links = find_url(confirm_message.text)
                if links and any("mega" in link.lower() for link in links):
                    break
                
                if "verification" in confirm_message.subject.lower():
                    break

            safe_print(f"> [{self.email}]: Waiting for verification email... ({i+1} of 12)", Fore.YELLOW)
            update_status(self.index, self.email, f"Waiting Email ({i+1}/12)")
            time.sleep(10)

        if STOP_FLAG: return False

        if not confirm_message:
            safe_print(f"> [{self.email}]: Failed to verify account. No verification email received.", Fore.RED)
            update_status(self.index, self.email, "Timeout: No Email")
            return False

        links = find_url(confirm_message.text)
        if not links:
            safe_print(f"> [{self.email}]: No verification link found in email.", Fore.RED)
            update_status(self.index, self.email, "Error: No Link")
            return False

        self.verify_command = self.verify_command.replace("@LINK@", links[0])

        cmd_parts = shlex.split(self.verify_command)
        # Strip any leading binary name/path (megatools, /usr/bin/megareg, etc.)
        if cmd_parts and (cmd_parts[0] in ("megatools", "megareg") or "megatools" in cmd_parts[0] or "megareg" in cmd_parts[0]):
            cmd_parts = cmd_parts[1:]
        
        # The verify command is: --verify <token> <link>
        # megareg needs: reg --verify <token> <link>
        # Run directly via subprocess since we already have the right binary path
        unified = megatools_helper._find_unified_megatools()
        if unified:
            full_args = [unified] + cmd_parts
        else:
            split_bin = megatools_helper._find_split_binary("reg")
            if split_bin:
                full_args = [split_bin] + cmd_parts
            else:
                full_args = ["megareg"] + cmd_parts
        
        try:
            verification = subprocess.run(
                full_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=CREATION_FLAGS,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            verification = subprocess.CompletedProcess(
                args=full_args, returncode=1, stdout="", stderr="Timed out"
            )
        except FileNotFoundError:
            verification = subprocess.CompletedProcess(
                args=full_args, returncode=1, stdout="", stderr="megatools not found"
            )

        if "registered successfully!" in verification.stdout.lower():
            safe_print(f"> [{self.email}] Successfully registered and verified.", Fore.GREEN)
            update_status(self.index, self.email, "Success")
            
            csv_utils.append_account([self.email, self.password, "0 B", "20 GB", "Active", "", self.email_password, self.email_id])
            
            return True
        else:
            safe_print(f"> [{self.email}]: Verification failed. CLI output: {verification.stdout}", Fore.RED)
            update_status(self.index, self.email, "Mega Verify Failed")
            return False

def new_account(index=0, pbar=None, password=None, cli_password=None):
    if STOP_FLAG: return {"success": False, "time": 0, "reason": "stopped"}

    start_time = time.time()
    if password is not None:
        pass_to_use = password
    elif cli_password is not None:
        pass_to_use = cli_password
    else:
        pass_to_use = get_random_string(random.randint(10, 16))
    
    acc = MegaAccount(index, fake.name(), pass_to_use)
    success = False
    reason = ""
    
    try:
        if acc.register():
            if not STOP_FLAG:
                if acc.verify():
                    success = True
                else:
                    reason = "verify_failed"
            else:
                reason = "stopped"
        else:
            reason = "register_failed"
    except Exception as e:
        reason = f"exception: {e}"
        safe_print(f"> [{acc.email or index}]: Unexpected error: {e}", Fore.RED)
    
    if pbar: pbar.update(1)
    
    elapsed = time.time() - start_time
    return {"success": success, "time": elapsed, "reason": reason}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create New Mega Accounts")
    parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=3,
        help="Number of accounts to create",
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=check_limit,
        default=None,
        help="Number of threads to use for concurrent account creation",
    )
    parser.add_argument(
        "-p",
        "--password",
        type=str,
        default=None,
        help="Password to use for all accounts",
    )
    args = parser.parse_args()

    # Ensure CSV is ready
    csv_utils.initialize_csv()

    safe_print(f"Starting generation of {args.number} accounts...", Fore.MAGENTA)
    
    with tqdm(total=args.number, desc="Total Progress", unit="acc") as pbar:
        if args.threads:
            threads = []
            start_delay = max(3, 10 / args.threads)
            for i in range(args.number):
                t = threading.Thread(target=new_account, args=(i, pbar, None, args.password))
                threads.append(t)
                t.start()
                time.sleep(start_delay)
            for t in threads:
                t.join()
        else:
            for i in range(args.number):
                new_account(i, pbar, None, args.password)

    safe_print("\nDone! Check accounts.csv for your new credentials.", Fore.GREEN + Style.BRIGHT)
