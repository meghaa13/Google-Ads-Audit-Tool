import os
import pandas as pd
import subprocess
import psutil
from google.ads.googleads.client import GoogleAdsClient
import google.generativeai as genai
from dotenv import load_dotenv

# === Load environment variables from .env ===
load_dotenv()

# === Platform Detection ===
IS_WINDOWS = os.name == "nt"
IS_RENDER = os.environ.get("RENDER") == "TRUE"  # Render sets this automatically

# === Chrome Path Setup ===
if IS_WINDOWS:
    CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
else:
    # Render/Linux: path to extracted Chromium
    CHROME_PATH = "/usr/bin/google-chrome"
# === User Data Dir Setup ===
USER_DATA_DIR = os.path.join(os.getcwd(), "ChromeDebugProfile")
os.makedirs(USER_DATA_DIR, exist_ok=True)

# === Chrome Debugging Port ===
DEBUGGING_PORT = "9222"

# === Auto-launch Chrome function ===
def ensure_chrome_debugger():
    """Force-launch Chrome with remote debugging enabled on port 9222."""
    chrome_running = False
    for proc in psutil.process_iter(attrs=['cmdline']):
        try:
            cmdline = " ".join(proc.info['cmdline'])
            if f"--remote-debugging-port={DEBUGGING_PORT}" in cmdline:
                chrome_running = True
                break
        except Exception:
            continue

    if not chrome_running:
        print("🚀 Launching Chrome in debugging mode...")
        chrome_args = [
            CHROME_PATH,
            f"--remote-debugging-port={DEBUGGING_PORT}",
            f"--user-data-dir={USER_DATA_DIR}"
        ]
        # Add headless and Linux-specific flags on Render
        if not IS_WINDOWS:
            chrome_args += ["--headless", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]

        subprocess.Popen(chrome_args)

# Auto-launch Chrome
ensure_chrome_debugger()

# === Global Config (Customer IDs) ===
CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
LOGIN_CUSTOMER_ID = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")

# === Gemini Config ===
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

# === Google Ads Client ===
google_ads_config = {
    "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
    "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
    "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
    "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
    "login_customer_id": LOGIN_CUSTOMER_ID,
    "use_proto_plus": True,
    "token_uri": "https://oauth2.googleapis.com/token",
}
google_ads_client = GoogleAdsClient.load_from_dict(google_ads_config)
client = google_ads_client

# === Environment Constants ===
LANGUAGE = "English"
DEVICE = "Desktop"

# === Mapping Dictionaries ===
MATCH_TYPE_MAP = {0: "UNSPECIFIED", 1: "UNKNOWN", 2: "EXACT", 3: "PHRASE", 4: "BROAD"}
STATUS_MAP = {0: "UNKNOWN", 1: "UNKNOWN", 2: "ENABLED", 3: "PAUSED", 4: "REMOVED"}
BID_STRATEGY_MAP = {
    0: "COMMISSION", 1: "FIXED_CPM", 2: "MANUAL_CPA", 3: "MANUAL_CPC",
    4: "MANUAL_CPM", 5: "MANUAL_CPV", 6: "MAXIMIZE_CONVERSIONS",
    8: "PAGE_ONE_PROMOTED", 9: "PERCENT_CPC", 10: "TARGET_CPA", 11: "TARGET_CPM",
    12: "TARGET_CPV", 13: "TARGET_IMPRESSION_SHARE", 14: "TARGET_ROAS", 15: "TARGET_SPEND"
}

# === Geo Lookup DataFrame ===
GEO_LOOKUP_DF = pd.read_csv("geotargets-2025-07-15.csv")
GEO_LOOKUP_DF = GEO_LOOKUP_DF[GEO_LOOKUP_DF["Status"] == "Active"]
GEO_LOOKUP_DF.set_index("Criteria ID", inplace=True)

# === Ensure required folders exist ===
os.makedirs("report_images", exist_ok=True)
os.makedirs("generated_reports", exist_ok=True)
os.makedirs("user_tokens", exist_ok=True)

# Backwards compatibility
customer_id = CUSTOMER_ID
