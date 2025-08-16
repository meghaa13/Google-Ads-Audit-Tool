import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
import pandas as pd
from .config import GEO_LOOKUP_DF

def fetch_page_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)
    except Exception as e:
        print(f"❌ Failed to fetch page {url}: {e}")
        return ""

def normalize_url(url):
    try:
        parsed = urlparse(url)
        normalized = parsed._replace(fragment="", query="")
        path = normalized.path.rstrip("/")
        normalized = normalized._replace(path=path)
        return urlunparse(normalized)
    except Exception:
        return url

def extract_location_parts(canonical_name):
    parts = [p.strip() for p in canonical_name.split(",")]
    parts += [""] * (3 - len(parts))
    return pd.Series({"City": parts[-3], "Region": parts[-2], "Country": parts[-1]})

def resolve_geo_names_from_csv(geo_ids):
    info = {}
    for geo_id in geo_ids:
        try:
            row = GEO_LOOKUP_DF.loc[int(geo_id)]
            info[int(geo_id)] = {
                "name": row.get("Name", ""),
                "canonical_name": row.get("Canonical Name", ""),
                "type": row.get("Target Type", ""),
                "country_code": row.get("Country Code", "")
            }
        except Exception:
            info[int(geo_id)] = {
                "name": f"GeoID {geo_id}",
                "canonical_name": "",
                "type": "",
                "country_code": ""
            }
    return info
