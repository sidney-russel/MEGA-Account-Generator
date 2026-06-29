import csv
import subprocess
import time
import os
import sys
import re
import logging
import megatools_helper
from tqdm import tqdm
from colorama import init, Fore, Style
import csv_utils

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

log_callback = None

STOP_FLAG = False

def stop():
    global STOP_FLAG
    STOP_FLAG = True

def set_log_callback(callback):
    global log_callback
    log_callback = callback

def format_bytes(size):
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size >= power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

def safe_print(message):
    clean_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(message))
    logging.info(clean_msg)
    
    if log_callback:
        log_callback(message)
    if sys.stdout is not None:
        try:
            tqdm.write(message)
        except Exception:
            pass

def check_storage(email, password):
    """Run megatools df to get storage usage (Used, Free)"""
    try:
        result = megatools_helper.run_megatools_command(
            ["df", "-u", email, "-p", password], 
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATION_FLAGS,
            timeout=30,
        )
        if result.returncode == 0:
            line = result.stdout.strip()
            parts = line.split()
            
            used_bytes = 0
            total_bytes = 0
            
            nums = [p for p in parts if p.isdigit()]
            logging.info(f"Storage Raw Output: {line} | Parsed: {nums}")
            
            if len(nums) >= 2:
                total_bytes = int(nums[0])
                used_bytes = int(nums[1])
            
            free_bytes = total_bytes - used_bytes
            
            return format_bytes(used_bytes), format_bytes(free_bytes)
            
        return None, None
    except Exception as e:
        logging.error(f"Error checking storage for {email}: {e}")
        return None, None

def main(pbar=None, check_only_storage=False):
    rows = csv_utils.read_accounts()
    
    if not rows:
        safe_print(f"{Fore.YELLOW}No accounts found in accounts.csv.")
        return
    
    safe_print(f"{Fore.MAGENTA}Starting processing for {len(rows)} accounts...")

    success_count = 0
    updated_rows = []
    
    if pbar is None:
        pbar_cm = tqdm(total=len(rows), desc="Processing", unit="acc")
    else:
        class DummyCM:
            def __enter__(self): return pbar
            def __exit__(self, *args): pass
        pbar_cm = DummyCM()

    with pbar_cm as pbar_instance:
        for row in rows:
            if STOP_FLAG:
                safe_print(f"{Fore.YELLOW}Process stopped by user.")
                updated_rows.append(row)
                continue

            email = row[0].strip()
            password = row[1].strip()
            
            storage_used = row[2] if len(row) > 2 else "0 B"
            free_storage = row[3] if len(row) > 3 else "20 GB"
            status = row[4].strip() if len(row) > 4 else "Unknown"

            if "disabled" in status.lower():
                if pbar_instance: pbar_instance.update(1)
                updated_rows.append(row) 
                continue
            
            session_status = "Unknown"
            
            tags = row[5]
            mail_tm_pass = row[6]
            mail_tm_id = row[7]

            if check_only_storage:
                used, free = check_storage(email, password)
                if used is not None:
                    safe_print(f"{Fore.GREEN}> [{email}]: Used: {used} | Free: {free}")
                    success_count += 1
                    session_status = "Active"
                    storage_used = used
                    free_storage = free
                else:
                    safe_print(f"{Fore.RED}> [{email}]: Failed to check storage (Login failed?)")
                    session_status = "Login Failed"
            else:
                login = megatools_helper.run_megatools_command(
                    ["ls", "-u", email, "-p", password],
                    universal_newlines=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=CREATION_FLAGS,
                    timeout=30,
                )

                if "/Root" in login.stdout:
                    success_count += 1
                    safe_print(f"{Fore.GREEN}> [{email}]: Login OK")
                    session_status = "Active"
                else:
                    safe_print(f"{Fore.RED}> [{email}]: LOGIN FAILED")
                    session_status = "Login Failed"

            new_row = [email, password, storage_used, free_storage, session_status, tags, mail_tm_pass, mail_tm_id]
            updated_rows.append(new_row)
            
            pbar_instance.update(1)
            time.sleep(1)

    if updated_rows:
        if csv_utils.write_accounts(updated_rows):
            safe_print(f"{Fore.CYAN}Updated accounts.csv with latest status.")
        else:
             safe_print(f"{Fore.RED}Error saving CSV.")

    safe_print(f"\n{Fore.CYAN}Process complete. {success_count}/{len(rows)} successful.")

if __name__ == "__main__":
    main()
