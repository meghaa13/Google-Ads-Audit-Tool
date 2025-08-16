import json
import time
import subprocess
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import CHROME_PATH, USER_DATA_DIR, DEBUGGING_PORT, model, LANGUAGE, DEVICE, GEO_LOOKUP_DF, client, CUSTOMER_ID
from .utils_web import fetch_page_text
import pandas as pd

try:
    import pychrome
    from playwright.sync_api import sync_playwright
except Exception:
    pychrome = None
    sync_playwright = None


def safe_parse_gemini_json(raw_text):
    if not raw_text:
        return []
    raw_text = raw_text.strip()
    try:
        return json.loads(raw_text)
    except Exception:
        pass
    match = re.search(r"\[.*\]", raw_text, re.DOTALL)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except Exception:
            pass
    return []


def detect_primary_location(google_ads_client, CUSTOMER_ID):
    ga_service = google_ads_client.get_service("GoogleAdsService")
    query = """
        SELECT
          campaign_criterion.criterion_id
        FROM campaign_criterion
        WHERE campaign_criterion.type = 'LOCATION'
          AND campaign_criterion.status = 'ENABLED'
    """
    location_ids = []
    try:
        response = ga_service.search_stream(customer_id= CUSTOMER_ID, query=query)
        for batch in response:
            for row in batch.results:
                location_ids.append(int(row.campaign_criterion.criterion_id))
    except Exception as e:
        print(f"⚠️ Error fetching campaign locations: {e}")
        return "United States"

    if not location_ids:
        return "United States"

    matches = GEO_LOOKUP_DF.loc[
        GEO_LOOKUP_DF.index.intersection(location_ids),
        ["Name", "Target Type"]
    ]
    if matches.empty:
        return "United States"
    city_region = matches[matches["Target Type"].isin(["City", "Region"])]
    if not city_region.empty:
        return city_region.iloc[0]["Name"]
    return matches.iloc[0]["Name"]


def generate_competitor_insights(kw_df, lp_df, site_url, genai_model):
    if kw_df is None or lp_df is None:
        return None

    primary_location = detect_primary_location(client, CUSTOMER_ID)
    print(f"📍 Using campaign location: {primary_location}")

    def launch_chrome():
        try:
            subprocess.Popen([
                CHROME_PATH,
                f"--remote-debugging-port={DEBUGGING_PORT}",
                f"--user-data-dir={USER_DATA_DIR}",
                "--no-first-run",
                "--no-default-browser-check"
            ])
            time.sleep(4)
        except Exception as e:
            print("⚠️ Could not launch local Chrome for pychrome:", e)

    def get_iframe_urls_for_keyword(keyword):
        iframe_urls = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            print(f"🔍 Looking for iframe URLs for keyword: {keyword}")
            page.goto("https://ads.google.com/anon/AdPreview")
            page.fill("input[aria-label='Enter a search term']", keyword)
            page.keyboard.press("Enter")
            time.sleep(3)
            try:
                page.locator("button[aria-label='Select location']").click()
                location_input = page.get_by_label("Enter a location to include")
                location_input.click()
                location_input.fill(primary_location)
                time.sleep(1)
                page.locator("div.list-dynamic-item.active").first.click()
                time.sleep(1.5)
            except:
                pass
            try:
                page.locator("div.button:has(span.label-text:has-text('Language'))").click()
                page.wait_for_selector("material-select-searchbox material-input input")
                page.locator("material-select-searchbox material-input input").first.fill(LANGUAGE)
                time.sleep(1)
                page.locator("material-select-dropdown-item span.label").first.click()
            except:
                pass
            try:
                page.locator("span.button-text", has_text="Mobile").click()
                time.sleep(1)
                page.locator(f"material-select-dropdown-item span.label:has-text('{DEVICE}')").click()
                time.sleep(1.5)
            except:
                pass
            page.wait_for_selector("iframe.iframe-preview", timeout=8000)
            iframe_elements = page.query_selector_all("iframe.iframe-preview")
            for iframe in iframe_elements:
                src = iframe.get_attribute("src")
                if src and src.startswith("http"):
                    iframe_urls.append(src)
            browser.close()
        return iframe_urls

    def scrape_ads(iframe_url):
        if pychrome is None:
            return []
        try:
            browser = pychrome.Browser(url=f"http://127.0.0.1:{DEBUGGING_PORT}")
            tabs = browser.list_tab()
            if not tabs:
                print("⚠️ No tabs found in Chrome debugger")
                return []
            tab = tabs[0]
            tab.start()
            tab.call_method("Page.enable")
            tab.call_method("Runtime.enable")
            tab.call_method("Page.navigate", url=iframe_url)
            time.sleep(5)
            js = """
            (() => {
                const results = [];
                const blocks = document.querySelectorAll('#rso > div');
                for (let i = 0; i < Math.min(3, blocks.length); i++) {
                    const block = blocks[i];
                    let titleEl = block.querySelector('a > h3');
                    let title = titleEl ? titleEl.innerText.trim() : "";
                    let urlEl = block.querySelector('cite');
                    let domainUrl = urlEl ? urlEl.innerText.trim() : "";
                    let domainName = domainUrl
                        .replace(/^https?:\/\//, '')
                        .replace(/^www\./, '')
                        .split(/[\/\?]/)[0];
                    let adCopyEl = block.querySelector('div:nth-child(2) > div > span');
                    let adCopy = adCopyEl ? adCopyEl.innerText.trim() : "";
                    results.push({
                        Name: domainName,
                        URL: domainUrl,
                        "Title": title,
                        "Ad Copy": adCopy
                    });
                }
                return JSON.stringify(results);
            })();
            """
            result = tab.call_method("Runtime.evaluate", expression=js, returnByValue=True)
            return json.loads(result["result"]["value"])
        except Exception as e:
            print("⚠️ pychrome scrape error:", e)
            return []

    def scrape_ads_for_keyword(keyword):
        ads_for_keyword = []
        try:
            iframe_urls = get_iframe_urls_for_keyword(keyword)[:2]
            for iframe_url in iframe_urls:
                ads = scrape_ads(iframe_url)
                ads_for_keyword.extend(ads)
        except Exception as e:
            print(f"⚠️ Error processing keyword '{keyword}': {e}")
        return keyword, ads_for_keyword

    def summarize_competitor(name, ads, lp_text):
        ad_summaries = "\n".join([f"- {ad['Title']} | {ad['Ad Copy']}" for ad in ads])
        prompt = f"""
You're a senior digital strategist.

A competitor named "{name}" has the following Google ad creatives:

{ad_summaries}

Compare their messaging and positioning to our landing page content below:

{lp_text[:3500]}

Return a JSON array of insights. Each object should include:
- "Competitor"
- "Strengths of Competitor"
- "Recommendation"

Avoid markdown. Only return valid JSON array.
"""
        try:
            response = genai_model.generate_content(prompt).text.strip()
            return {
                "Competitor": name,
                "Insight": response
            }
        except Exception as e:
            return {
                "Competitor": name,
                "Insight": f"Gemini error: {e}"
            }

    if "CVR" not in kw_df.columns:
        kw_df["CVR"] = kw_df["Conversions"] / kw_df["Clicks"].replace(0, 1)

    top_keywords = kw_df.sort_values("CVR", ascending=False).drop_duplicates("Keyword").head(5)
    best_lp = lp_df.sort_values("Conversions", ascending=False)["Final URL"].iloc[0] if not lp_df.empty else site_url
    lp_text = fetch_page_text(best_lp)

    launch_chrome()
    competitor_ads = defaultdict(list)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(scrape_ads_for_keyword, kw) for kw in top_keywords["Keyword"]]
        for future in as_completed(futures):
            keyword, ads = future.result()
            own_domain = site_url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0].lower()
            for ad in ads:
                ad_domain = ad["Name"].lower()
                if ad_domain != own_domain and ad_domain != "unknown":
                    ad["Keyword"] = keyword
                    competitor_ads[ad["Name"]].append(ad)

    summary = []
    for name, ads in competitor_ads.items():
        summary.append(summarize_competitor(name, ads, lp_text))

    result_df = []
    for row in summary:
        raw_json = row.get("Insight", "").strip()
        try:
            insights = safe_parse_gemini_json(raw_json)
            if not insights:
                raise ValueError("Could not extract valid JSON")
            strengths = []
            recommendations = []
            for item in insights:
                strengths.append(item.get("Strengths of Competitor", "").strip())
                recommendations.append(item.get("Recommendation", "").strip())
            result_df.append({
                "Competitor": row["Competitor"],
                "Strengths": "\n".join(filter(None, strengths)),
                "Recommendations": "\n".join(filter(None, recommendations))
            })
        except Exception as e:
            result_df.append({
                "Competitor": row.get("Competitor", "Unknown"),
                "Strengths": f"❌ Parse Error: {e}",
                "Recommendations": "N/A"
            })

    return pd.DataFrame(result_df)
