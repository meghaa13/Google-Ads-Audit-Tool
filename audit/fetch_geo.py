import pandas as pd
from .utils_web import resolve_geo_names_from_csv, extract_location_parts
from google.ads.googleads.client import GoogleAdsClient

def fetch_geo_performance_data(client: GoogleAdsClient, customer_id: str):
    service = client.get_service("GoogleAdsService")
    query = """
        SELECT 
            geographic_view.country_criterion_id,
            geographic_view.location_type,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.cost_micros
        FROM geographic_view
        WHERE segments.date DURING LAST_30_DAYS
        AND metrics.impressions > 0
        AND geographic_view.location_type = 'LOCATION_OF_PRESENCE'
        LIMIT 10000
    """
    try:
        response = service.search_stream(customer_id=customer_id, query=query, metadata=(("login-customer-id", "9323527146"),))
    except Exception as e:
        print(f"❌ Error fetching geo data: {e}")
        return pd.DataFrame()

    data = []
    geo_ids = set()

    print("\n=== RAW API PAYLOAD (from Google Ads) ===")
    for batch in response:
        for row in batch.results:
            # Print the raw Google Ads API object for this location
            print(row)

            geo_id = row.geographic_view.country_criterion_id
            geo_ids.add(geo_id)
            cost = row.metrics.cost_micros / 1e6 if row.metrics.cost_micros else 0
            if cost == 0:
                continue
            conversions = row.metrics.conversions or 0
            clicks = row.metrics.clicks or 0
            cvr = conversions / clicks if clicks else     0
            cpa = cost / conversions if conversions else 0
            data.append({
                "Geo ID": geo_id,
                "Impressions": row.metrics.impressions,
                "Clicks": clicks,
                "Conversions": conversions,
                "Cost ($)": cost,
                "CVR": cvr,
                "CPA ($)": cpa
            })

    if not data:
        return pd.DataFrame()

    # Process into DataFrame
    df = pd.DataFrame(data)
    geo_info = resolve_geo_names_from_csv(df["Geo ID"].unique())
    df["Canonical Name"] = df["Geo ID"].apply(lambda x: geo_info.get(x, {}).get("canonical_name", f"GeoID {x}"))
    df["Type"] = df["Geo ID"].apply(lambda x: geo_info.get(x, {}).get("type", "Unknown"))
    location_parts = df["Canonical Name"].apply(extract_location_parts)
    df = pd.concat([df, location_parts], axis=1)
    df = df[[
        "City", "Region", "Country", "Type", "Impressions", "Clicks", "Conversions", "Cost ($)", "CVR", "CPA ($)"
    ]]

    print("\n=== PROCESSED GEO PERFORMANCE DATA ===")
    print(df.to_string(index=False))

    return df
