import pandas as pd
from .config import STATUS_MAP, BID_STRATEGY_MAP
from google.ads.googleads.client import GoogleAdsClient

def fetch_campaign_data(client: GoogleAdsClient, customer_id: str, date_range="LAST_30_DAYS"):
    service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT campaign.id, campaign.name, campaign.status, campaign.start_date,
               campaign.bidding_strategy_type, campaign_budget.amount_micros,
               metrics.impressions, metrics.clicks, metrics.ctr, metrics.average_cpc,
               metrics.cost_micros, metrics.conversions
        FROM campaign
        WHERE campaign.advertising_channel_type = 'SEARCH'
        AND campaign.status = 'ENABLED'
        AND metrics.impressions > 0
        AND segments.date DURING {date_range}
        LIMIT 100
    """
    try:
        response = service.search_stream(customer_id=customer_id, query=query, metadata=(("login-customer-id", "9323527146"),))
    except Exception as e:
        print(f"❌ Error fetching campaign data: {e}")
        return pd.DataFrame()

    data = []
    for batch in response:
        for row in batch.results:
            cost = row.metrics.cost_micros / 1e6 if row.metrics.cost_micros else 0
            conversions = row.metrics.conversions or 0
            cpa = cost / conversions if conversions else 0
            data.append({
                "Campaign ID": row.campaign.id,
                "Campaign Name": row.campaign.name,
                "Status": STATUS_MAP.get(row.campaign.status, "UNKNOWN"),
                "Start Date": row.campaign.start_date,
                "Bid Strategy": BID_STRATEGY_MAP.get(row.campaign.bidding_strategy_type, "UNKNOWN"),
                "Budget/day ($)": row.campaign_budget.amount_micros / 1e6 if row.campaign_budget.amount_micros else 0,
                "Impressions": row.metrics.impressions,
                "Clicks": row.metrics.clicks,
                "CTR": row.metrics.ctr,
                "Avg CPC": row.metrics.average_cpc / 1e6 if row.metrics.average_cpc else 0,
                "Cost ($)": cost,
                "Conversions": conversions,
                "CPA ($)": cpa
            })
    return pd.DataFrame(data)
