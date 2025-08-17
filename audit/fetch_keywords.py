import pandas as pd
from google.ads.googleads.client import GoogleAdsClient
from .config import MATCH_TYPE_MAP

def fetch_keyword_data(client: GoogleAdsClient, customer_id: str):
    service = client.get_service("GoogleAdsService")
    query = """
        SELECT ad_group.name, ad_group_criterion.keyword.text,
               ad_group_criterion.keyword.match_type,
               ad_group_criterion.quality_info.quality_score,
               metrics.impressions, metrics.clicks, metrics.ctr,
               metrics.average_cpc, metrics.cost_micros, metrics.conversions
        FROM keyword_view
        WHERE ad_group_criterion.status = 'ENABLED'
        AND campaign.status = 'ENABLED'
        AND ad_group.status = 'ENABLED'
        AND segments.date DURING LAST_30_DAYS
        AND metrics.impressions > 0
        LIMIT 500
    """
    try:
        response = service.search_stream(customer_id=customer_id, query=query)
    except Exception as e:
        print(f"❌ Error fetching keyword data: {e}")
        return pd.DataFrame()

    data = []
    for batch in response:
        for row in batch.results:
            cost = (row.metrics.cost_micros or 0) / 1e6
            clicks = row.metrics.clicks or 0
            impressions = row.metrics.impressions or 0
            conversions = row.metrics.conversions or 0
            cpa = cost / conversions if conversions else 0

            data.append({
                "Ad Group": row.ad_group.name,
                "Keyword": row.ad_group_criterion.keyword.text,
                "Match Type": MATCH_TYPE_MAP.get(row.ad_group_criterion.keyword.match_type, "UNKNOWN"),
                "Quality Score": row.ad_group_criterion.quality_info.quality_score,
                "Impressions": impressions,
                "Clicks": clicks,
                "CTR": clicks / impressions if impressions else 0,
                "Avg CPC": (row.metrics.average_cpc or 0) / 1e6,
                "Cost ($)": cost,
                "Conversions": conversions,
                "CPA ($)": cpa,
                "CVR": conversions / clicks if clicks else 0  # <-- added here
            })

    df = pd.DataFrame(data)

    # Ensure CVR column exists even if data is empty
    if "CVR" not in df.columns:
        df["CVR"] = 0

    return df
