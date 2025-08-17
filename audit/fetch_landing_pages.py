import pandas as pd
from .utils_web import normalize_url
from google.ads.googleads.client import GoogleAdsClient

def fetch_landing_page_data(client: GoogleAdsClient, customer_id: str):
    service = client.get_service("GoogleAdsService")
    query = """
        SELECT 
          landing_page_view.unexpanded_final_url,
          metrics.impressions,
          metrics.clicks,
          metrics.conversions,
          metrics.cost_micros,
          metrics.ctr,
          metrics.average_cpc
        FROM landing_page_view
        WHERE segments.date DURING LAST_30_DAYS
        AND metrics.impressions > 0
        LIMIT 500
    """
    try:
        response = service.search_stream(customer_id=customer_id, query=query)
    except Exception as e:
        print(f"❌ Error fetching landing page data: {e}")
        return pd.DataFrame()

    data = []
    for batch in response:
        for row in batch.results:
            url = row.landing_page_view.unexpanded_final_url
            cost = row.metrics.cost_micros / 1e6 if row.metrics.cost_micros else 0
            conversions = row.metrics.conversions or 0
            clicks = row.metrics.clicks or 0
            impressions = row.metrics.impressions or 0
            data.append({
                "Final URL": url,
                "Impressions": impressions,
                "Clicks": clicks,
                "Conversions": conversions,
                "Cost ($)": cost
            })

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["Normalized URL"] = df["Final URL"].apply(normalize_url)
    agg_cols = ["Impressions", "Clicks", "Conversions", "Cost ($)"]
    df = df.groupby("Normalized URL", as_index=False)[agg_cols].sum()
    df["CTR"] = df["Clicks"] / df["Impressions"].replace(0, 1)
    df["CPA ($)"] = df["Cost ($)"] / df["Conversions"].replace(0, 1)
    df["Avg CPC"] = df["Cost ($)"] / df["Clicks"].replace(0, 1)
    df = df.rename(columns={"Normalized URL": "Final URL"})
    return df
