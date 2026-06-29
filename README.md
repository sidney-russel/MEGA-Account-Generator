<div align="center">
  <img src="./logo.png" width="120" alt="Logo">
  <h1>MEGA Account Generator</h1>
  <p>Bulk generate MEGA.nz accounts with proxy rotation, keep-alive, and full account management.</p>
  
  [![Build](https://github.com/sidney-russel/MEGA-Account-Generator/actions/workflows/build.yml/badge.svg)](https://github.com/sidney-russel/MEGA-Account-Generator/actions)
  [![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue)](https://python.org)
  [![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
  
  [Download .exe](https://github.com/sidney-russel/MEGA-Account-Generator/releases/latest) • [Quick Start](#quick-start) • [Proxy Setup](#proxy-setup) • [Keep-Alive](#keep-alive) • [CLI](#cli-usage)
</div>

---

## What This Does

1. Creates temporary emails via mail.tm
2. Registers MEGA.nz accounts using those emails
3. Saves credentials to CSV
4. Keeps accounts alive with periodic sign-ins
5. Rotates IPs via Webshare proxies to avoid bans

## Quick Start

### Windows (no Python needed)
Download [MEGA-Generator.exe](https://github.com/sidney-russel/MEGA-Account-Generator/releases/latest) and run it.

### Linux
```bash
sudo apt install megatools
git clone https://github.com/sidney-russel/MEGA-Account-Generator.git
cd MEGA-Account-Generator
pip install -r requirements.txt
python3 gui.py
```

### Build It Yourself
```bash
# Linux
./build.sh

# Windows
build.bat
```

## How Many Accounts Can I Make?

Depends on your proxy setup:

| Setup | Accounts |
|-------|----------|
| No proxies (direct) | ~50-100 per IP |
| 10 Webshare proxies (1 account) | ~500-1,000 |
| 50 Webshare proxies (5 accounts) | ~2,500-5,000 |
| 100+ Webshare proxies | 5,000+ |

MEGA blocks datacenter IPs for registration — proxies only help with mail.tm email creation.

## Proxy Setup

Each free Webshare account gives **10 HTTP/SOCKS5 proxies**. Create multiple accounts to build a big proxy pool.

1. Sign up at [webshare.io](https://webshare.io) (free, no credit card)
2. Dashboard → API Keys → Create Key
3. In the tool, paste key → click **Add**
4. Repeat for more accounts: 5 accounts = 50 proxies, 10 accounts = 100 proxies

Keys are saved to `proxy_config.json` — auto-loads on restart.

## Keep-Alive

MEGA deletes inactive accounts. Run keep-alive weekly to prevent this.

**GUI:** Click "Check Storage / Sign In" in the Stored Accounts tab.

**CLI:**
```bash
python3 signin_accounts.py
```

**Cron (auto weekly):**
```bash
0 2 * * 0 cd /path/to/MEGA-Account-Generator && python3 signin_accounts.py >> keepalive.log 2>&1
```

## CLI Usage

```bash
# Generate 50 accounts, 5 threads, same password
python3 generate_accounts.py -n 50 -t 5 -p "MyPassword123"

# Keep-alive check
python3 signin_accounts.py
```

| Flag | Description | Default |
|------|-------------|---------|
| `-n` | Number of accounts | 3 |
| `-t` | Threads (max 8) | 3 |
| `-p` | Password for all accounts | random |

## Import / Export

**Export:** JSON or Excel (formatted with color-coded status).

**Import:** JSON, Excel, or CSV. CSV format:
```csv
email,password
user1@example.com,mypass123
user2@example.com,mypass456
```

## File Structure

```
├── gui.py                 # GUI application
├── generate_accounts.py   # Account generation
├── signin_accounts.py     # Keep-alive
├── mailtm_client.py       # mail.tm API client
├── proxy_manager.py       # Webshare proxy rotation
├── megatools_helper.py    # Megatools wrapper
├── csv_utils.py           # Thread-safe CSV
├── export_utils.py        # JSON/Excel/CSV import/export
├── tag_manager.py         # Account tagging
├── build.sh               # Linux build
├── build.bat              # Windows build
└── accounts.csv           # Your accounts (auto-created)
```

## FAQ

**Why max 8 threads?**
mail.tm rate limits. More threads = more bans.

**Accounts.csv not found?**
Auto-created on first run.

**megatools not found?**
```bash
sudo apt install megatools    # Debian/Ubuntu
sudo pacman -S megatools      # Arch
brew install megatools         # macOS
```

**Headless Linux server?**
```bash
xvfb-run python3 gui.py
```

## Disclaimer

For educational and testing purposes only. Don't abuse MEGA or mail.tm services.

## License

MIT
