"""
Direct mail.tm API client.
Bypasses pymailtm which has address collision bugs.
Supports proxy rotation via proxy_manager.
"""
import requests
import random
import string
import logging
import time

API_BASE = "https://api.mail.tm"
logger = logging.getLogger(__name__)


class MailTmAccount:
    """Represents a mail.tm account."""
    def __init__(self, address, account_id, password, token=None):
        self.address = address
        self.id_ = account_id
        self.password = password
        self.token = token


def _generate_unique_address():
    """Generate a unique random email address for mail.tm."""
    length = random.randint(10, 16)
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=length))


def _get_proxies():
    """Get current proxy dict from proxy_manager if enabled."""
    try:
        from proxy_manager import proxy_manager
        if proxy_manager.enabled:
            proxy = proxy_manager.get_proxy()
            if proxy:
                return {"http": proxy, "https": proxy}
    except ImportError:
        pass
    return None


def _mark_proxy_failed():
    """Mark current proxy as failed."""
    try:
        from proxy_manager import proxy_manager
        proxies = _get_proxies()
        if proxies and proxy_manager.enabled:
            proxy_manager.mark_failed(proxies.get("http", ""))
    except ImportError:
        pass


def _get_domain(session):
    """Get an active domain from mail.tm."""
    r = session.get(f"{API_BASE}/domains", timeout=15, proxies=_get_proxies())
    r.raise_for_status()
    domains = r.json().get("hydra:member", [])
    active = [d for d in domains if d.get("isActive")]
    if not active:
        raise Exception("No active mail.tm domains available")
    return random.choice(active)["domain"]


def _generate_password(length=None):
    """Generate a random password."""
    if length is None:
        length = random.randint(10, 16)
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


def create_account(max_retries=5):
    """
    Create a new mail.tm account with retries for address collisions.
    Uses proxy rotation if enabled.
    
    Returns:
        MailTmAccount on success, None on failure.
    """
    for attempt in range(max_retries):
        try:
            proxies = _get_proxies()
            domain = _get_domain(requests.Session())
            username = _generate_unique_address()
            address = f"{username}@{domain}"
            password = _generate_password()
            
            payload = {"address": address, "password": password}
            headers = {
                "accept": "application/ld+json",
                "Content-Type": "application/json",
            }
            r = requests.post(f"{API_BASE}/accounts", json=payload, headers=headers, timeout=15, proxies=proxies)
            
            if r.status_code in (200, 201):
                data = r.json()
                account_id = data.get("id", "")
                return MailTmAccount(address, account_id, password)
            
            if r.status_code == 422:
                body = r.text
                if "already used" in body.lower():
                    logger.info(f"Address collision on attempt {attempt+1}, retrying...")
                    continue
                else:
                    logger.warning(f"HTTP 422 (other): {body[:200]}")
                    continue
            
            logger.warning(f"HTTP {r.status_code} creating mail.tm account: {r.text[:200]}")
            if r.status_code in (403, 429, 503):
                _mark_proxy_failed()
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error on attempt {attempt+1}: {e}")
            _mark_proxy_failed()
            time.sleep(min(4 * (2 ** attempt), 30))
        except Exception as e:
            logger.warning(f"Unexpected error on attempt {attempt+1}: {e}")
            time.sleep(min(4 * (2 ** attempt), 30))
    
    return None


def session_get_messages(account):
    """
    Authenticate and get messages from mail.tm.
    Uses proxy rotation if enabled.
    
    Args:
        account: MailTmAccount instance with address and password
    
    Returns:
        list of message dicts
    """
    headers = {
        "accept": "application/ld+json",
        "Content-Type": "application/json",
    }
    
    proxies = _get_proxies()
    session = requests.Session()
    
    # Authenticate
    auth_payload = {"address": account.address, "password": account.password}
    r = session.post(f"{API_BASE}/token", json=auth_payload, headers=headers, timeout=15, proxies=proxies)
    
    if r.status_code not in (200, 201):
        logger.warning(f"Failed to authenticate with mail.tm for {account.address}: {r.status_code}")
        if r.status_code in (403, 429, 503):
            _mark_proxy_failed()
        return []
    
    token = r.json().get("token")
    if not token:
        return []
    
    # Get messages
    msg_headers = {
        "accept": "application/ld+json",
        "Authorization": f"Bearer {token}",
    }
    r = session.get(f"{API_BASE}/messages", headers=msg_headers, timeout=15, proxies=proxies)
    
    if r.status_code != 200:
        return []
    
    messages = r.json().get("hydra:member", [])
    result = []
    for msg in messages:
        msg_id = msg.get("id")
        if msg_id:
            full_r = session.get(f"{API_BASE}/messages/{msg_id}", headers=msg_headers, timeout=15, proxies=proxies)
            if full_r.status_code == 200:
                result.append(full_r.json())
            else:
                result.append(msg)
    
    return result
