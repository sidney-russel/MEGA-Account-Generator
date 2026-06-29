<div align="center">

**English** | [Português (Brasil)](https://github.com/byPancra/MEGA-Account-Generator-GUI/tree/lang-pt-BR) | [Español](https://github.com/byPancra/MEGA-Account-Generator-GUI/tree/lang-es) | [日本語](https://github.com/byPancra/MEGA-Account-Generator-GUI/tree/lang-ja) | [繁體中文](https://github.com/byPancra/MEGA-Account-Generator-GUI/tree/lang-zh-TW) | [简体中文](https://github.com/byPancra/MEGA-Account-Generator-GUI/tree/lang-zh-CN)

</div>
<br>

<div align="center">

  ![Mega Account Generator GUI](./img/readme-icon.png)

  <h1 align="center">Mega Account Generator GUI</h1>
  
  **The ultimate tool for automating MEGA.nz account creation and management.**
  
  *Generate, Manage, Tag, and Export your accounts with a professional-grade interface.*

  [![Python Version](https://img.shields.io/badge/python-3.8%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
  [![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](./LICENSE)
  [![Status](https://img.shields.io/badge/status-active-success?style=for-the-badge)]()

  [Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Proxy Setup](#-proxy-setup-webshare) • [Keep-Alive](#-keep-alive-prevent-inactivity-deletion) • [FAQ](#-faq)

</div>

---

## Overview

**Mega Account Generator GUI** is a robust, desktop-grade application designed for power users who need to generate and manage [MEGA.nz](https://mega.nz) accounts in bulk. Built with **Modern Python** (CustomTkinter) and **Thread-Safe Architecture**, it ensures reliability even when processing hundreds of accounts.

![Demo](./img/intro2.gif)

---

## Features

### Core Generation
*   **High-Speed Multi-Threading**: Generate up to 8 accounts simultaneously.
*   **Smart Rate Limiting**: Intelligent delays and retry logic to bypass Mail.tm restrictions.
*   **Free Proxy Rotation**: Automatically rotates IPs for email creation using Webshare (10 free proxies per account).

### Advanced Management
*   **Tagging System**: Organize accounts with custom tags (e.g., `Personal`, `Backup`, `Client-A`).
*   **Search & Filter**: Find accounts by Email, Status (`Active`, `Disabled`, `Failed`), or Tags.
*   **Keep-Alive**: Automated sign-in to prevent account deletion due to inactivity.
*   **Storage Check**: Auto-update used/free storage quotas for all accounts.
*   **Bulk Operations**: Disable specific accounts to exclude them from bulk operations.

### Data Freedom
*   **Professional Export**: Export to **Excel (.xlsx)** with formatting or **JSON** for programmatic use.
*   **Import**: Import from **JSON**, **Excel**, or **CSV** files.
*   **Clipboard Integration**: One-click copy for emails and passwords.

### Security & Reliability
*   **Thread-Safe CSV**: Prevents data corruption during concurrent writes.
*   **Crash Recovery**: "Stop" button gracefully halts operations, preserving data integrity.

---

## Installation

### Option A: Standalone Executable (Recommended)

No Python or external tools needed.

**Windows:**
1.  Download `MEGA-Generator.exe` from [Releases](https://github.com/byPancra/Mega-Account-Generator-GUI/releases).
2.  Run the executable.

**Linux:**
1.  Download `MEGA-Generator` from [Releases](https://github.com/byPancra/Mega-Account-Generator-GUI/releases).
2.  Make executable: `chmod +x MEGA-Generator`
3.  Run: `./MEGA-Generator`

### Option B: Running from Source

#### Linux (Ubuntu/Debian)

```bash
# 1. Install system dependencies
sudo apt update
sudo apt install python3 python3-pip python3-venv megatools

# 2. Clone the repository
git clone https://github.com/byPancra/Mega-Account-Generator-GUI.git
cd Mega-Account-Generator-GUI

# 3. Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Run the application
python3 gui.py
```

#### Linux (Arch/Manjaro)

```bash
# 1. Install system dependencies
sudo pacman -S python python-pip megatools

# 2-5. Same as Ubuntu steps 2-5 above
```

#### Linux (Fedora/RHEL)

```bash
# 1. Install system dependencies
sudo dnf install python3 python3-pip megatools

# 2-5. Same as Ubuntu steps 2-5 above
```

#### Windows

```powershell
# 1. Install Python 3.8+ from python.org (check "Add to PATH")

# 2. Install Megatools
#    Download from https://megatools.megous.com/ or use: choco install megatools

# 3. Clone and setup
git clone https://github.com/byPancra/Mega-Account-Generator-GUI.git
cd Mega-Account-Generator-GUI
pip install -r requirements.txt

# 4. Run
python gui.py
```

#### macOS

```bash
# 1. Install dependencies
brew install python3 megatools

# 2-5. Same as Linux steps 2-5 above
```

### Option C: Build Standalone Binary

**Linux:**
```bash
chmod +x build.sh
./build.sh
# Binary: dist/MEGA-Generator
```

**Windows:**
```cmd
build.bat
:: Binary: dist\MEGA-Generator.exe
```

---

## Usage

### Generating Accounts

1.  Open the application.
2.  Set the number of **Accounts** and **Threads** (max 8).
3.  (Optional) Set a **Common Password** for all accounts.
4.  (Optional) Enable **Use Proxies** and add Webshare API keys for IP rotation.
5.  Click **Start Generation**.
6.  Credentials are saved to `accounts.csv` automatically.

### Managing Accounts

Navigate to the **Stored Accounts** tab:
*   **Search**: Type an email to filter instantly.
*   **Filter**: Use the dropdown to see only `Active`, `Disabled`, or `Failed` accounts.
*   **Edit**: Click "Edit" to change a saved password or manage Tags.
*   **Copy**: Quick buttons to copy credentials to clipboard.
*   **Pagination**: Navigate through pages (50 accounts per page).

### CLI Usage

```bash
# Generate 3 accounts (default)
python3 generate_accounts.py

# Generate 50 accounts with 5 threads
python3 generate_accounts.py -n 50 -t 5

# Set a specific password for all accounts
python3 generate_accounts.py -n 10 -p "MySecretPass123!"

# Keep-Alive check (sign in to all accounts)
python3 signin_accounts.py
```

**Arguments for generate_accounts.py:**
| Flag | Description | Default |
|------|-------------|---------|
| `-n`, `--number` | Number of accounts to create | 3 |
| `-t`, `--threads` | Number of concurrent threads (1-8) | 3 |
| `-p`, `--password` | Common password for all accounts | Random |

### Import/Export

**Export:**
1.  Click **Export** in the top right.
2.  Select format: **JSON** (raw data) or **Excel** (formatted spreadsheet).
3.  Choose save location.

**Import:**
1.  Click **Import** in the Accounts view.
2.  Select a file: **JSON**, **Excel (.xlsx)**, or **CSV**.
3.  Confirm the import.

**CSV Import Format:**
```csv
email,password
user1@example.com,mypassword123
user2@example.com,anotherpass456
```

Or full format matching `accounts.csv`:
```csv
email,password,storage_used,free_storage,status,tags,mailtm_password,mailtm_id
user@example.com,mypass,0 B,20 GB,Active,,, 
```

---

## Proxy Setup (Webshare)

Proxies are used **only for mail.tm email creation** (MEGA blocks all proxy IPs). This lets you bypass IP bans when creating emails.

### How It Works

1.  **Webshare** gives 10 free HTTP/SOCKS5 proxies per account (1GB/mo bandwidth).
2.  Create multiple Webshare accounts → aggregate all proxies into one pool.
3.  The tool rotates through all proxies when creating mail.tm emails.

### Setup

1.  Go to [webshare.io](https://webshare.io) and sign up (free, no credit card).
2.  In the dashboard, go to **API Keys** → **Create API Key**.
3.  Copy the key.
4.  In the GUI, paste the key in the **Webshare API Keys** field and click **Add**.
5.  Repeat for more accounts:
    *   1 account = 10 proxies
    *   5 accounts = 50 proxies
    *   10 accounts = 100 proxies
6.  Enable the **Use Proxies** checkbox.

### Adding Keys via CLI

API keys are saved to `proxy_config.json`. You can also edit this file directly:
```json
{
  "webshare_api_keys": [
    "your-api-key-1",
    "your-api-key-2",
    "your-api-key-3"
  ]
}
```

### Free Proxy Fallback

If no Webshare keys are added, the tool automatically fetches from free proxy lists (~10% work rate). Not recommended for serious use.

---

## Keep-Alive (Prevent Inactivity Deletion)

MEGA deletes accounts that haven't been accessed for a long time. The **Keep-Alive** feature prevents this by signing into each account periodically.

### How It Works

1.  Signs into each account using `megatools ls`.
2.  Updates storage quota (used/free).
3.  Marks failed accounts as `Login Failed`.
4.  Skips `Disabled` accounts.

### Running Keep-Alive

**Via GUI:**
1.  Go to the **Stored Accounts** tab.
2.  Click **Check Storage / Sign In**.
3.  Wait for all accounts to be processed.

**Via CLI:**
```bash
python3 signin_accounts.py
```

### Recommended Schedule

| Accounts | Frequency |
|----------|-----------|
| 1-50 | Weekly |
| 50-200 | Every 3-4 days |
| 200+ | Every 2 days |

**Tip:** Set up a cron job for automatic keep-alive:
```bash
# Run keep-alive every Sunday at 2 AM
0 2 * * 0 cd /path/to/Mega-Account-Generator-GUI && python3 signin_accounts.py >> keepalive.log 2>&1
```

---

## File Structure

```
MEGA-Account-Generator-GUI/
├── gui.py                 # Main GUI application
├── generate_accounts.py   # Account generation logic
├── signin_accounts.py     # Keep-alive / sign-in
├── mailtm_client.py       # Direct mail.tm API (replaces pymailtm)
├── proxy_manager.py       # Multi-account Webshare proxy rotation
├── megatools_helper.py    # Cross-platform megatools wrapper
├── csv_utils.py           # Thread-safe CSV operations
├── export_utils.py        # JSON/Excel/CSV import/export
├── tag_manager.py         # Account tagging system
├── accounts.csv           # Account database (auto-created)
├── proxy_config.json      # Webshare API keys (auto-created)
├── requirements.txt       # Python dependencies
├── build.sh               # Linux build script
├── build.bat              # Windows build script
├── logo.ico               # Application icon
├── logo.png               # Application logo
└── README.md              # This file
```

---

## FAQ

<details>
<summary><strong>Why am I limited to 8 threads?</strong></summary>
The temporary email provider (Mail.tm) has strict rate limits. Exceeding 8 concurrent threads significantly increases the chance of IP bans or failed generations.
</details>

<details>
<summary><strong>What does "Check Storage / Sign In" do?</strong></summary>
It performs a "Keep-Alive" check. It signs into your accounts using `megatools`, updates storage quotas, and signals to MEGA that the accounts are active, preventing deletion.
</details>

<details>
<summary><strong>Where are my accounts saved?</strong></summary>
All data is stored locally in `accounts.csv` in the application directory. You can also export this data using the Export feature.
</details>

<details>
<summary><strong>I see "Megatools not found" error.</strong></summary>
If running from source, ensure `megatools` is installed and in your system PATH:

```bash
# Ubuntu/Debian
sudo apt install megatools

# Verify installation
which megareg
```

If using the executable, this is handled automatically.
</details>

<details>
<summary><strong>How many accounts can I generate?</strong></summary>
Depends on your proxy setup:
- **No proxies**: ~50-100 per IP before mail.tm bans
- **10 Webshare proxies**: ~500-1000 accounts
- **50 Webshare proxies**: ~2500-5000 accounts
- **100+ Webshare proxies**: 5000+ accounts

MEGA itself blocks all proxy IPs, so MEGA registration always uses your real IP.
</details>

<details>
<summary><strong>Can I import accounts from another tool?</strong></summary>
Yes. Use the Import button to load JSON, Excel, or CSV files. The CSV import supports:
- `email,password` format
- Full 8-column format matching `accounts.csv`
</details>

<details>
<summary><strong>How do I prevent accounts from being deleted?</strong></summary>
Run the Keep-Alive feature weekly (or more often for large collections). See the [Keep-Alive](#-keep-alive-prevent-inactivity-deletion) section for cron job setup.
</details>

<details>
<summary><strong>Does this work on headless Linux servers?</strong></summary>
Yes. For servers without a display, use Xvfb:
```bash
sudo apt install xvfb
xvfb-run python3 gui.py
```
Or use the CLI commands directly (no GUI needed):
```bash
python3 generate_accounts.py -n 50 -t 5
python3 signin_accounts.py
```
</details>

---

## Disclaimer

This tool is created for **educational and testing purposes only**. Using this software to abuse third-party services, bypass restrictions, or violate terms of service (ToS) of MEGA.nz or Mail.tm is strictly prohibited. The developer assumes no responsibility for misuse.

---

## Acknowledgements

*   Based on the original work by [f-o/MEGA-Account-Generator](https://github.com/f-o/MEGA-Account-Generator).
*   GUI Components by [TomSchimansky/CustomTkinter](https://github.com/TomSchimansky/CustomTkinter).
*   Enhanced and Maintained by [byPancra](https://github.com/byPancra).

---

## License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

<div align="center">
  <sub>Developed with love by <a href="https://github.com/byPancra">byPancra</a></sub>
</div>
