import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.v20.enums.types.day_of_week import DayOfWeekEnum

def fetch_hourly_performance_data(client: GoogleAdsClient, customer_id: str):
    service = client.get_service("GoogleAdsService")
    query = """
        SELECT segments.day_of_week, segments.hour,
               metrics.clicks, metrics.conversions, metrics.cost_micros
        FROM campaign
        WHERE campaign.advertising_channel_type = 'SEARCH'
        AND campaign.status = 'ENABLED'
        AND segments.date DURING LAST_30_DAYS
        AND metrics.clicks > 0
        LIMIT 10000
    """
    try:
        response = service.search_stream(customer_id=customer_id, query=query)
    except Exception as e:
        print(f"❌ Error fetching hourly data: {e}")
        return pd.DataFrame(), pd.DataFrame()

    data = []
    for batch in response:
        for row in batch.results:
            cost = row.metrics.cost_micros / 1e6 if row.metrics.cost_micros else 0
            conversions = row.metrics.conversions or 0
            clicks = row.metrics.clicks or 0
            cvr = conversions / clicks if clicks else 0
            data.append({
                "Day": DayOfWeekEnum.DayOfWeek(row.segments.day_of_week).name.title().replace("_", " "),
                "Hour": row.segments.hour,
                "Clicks": clicks,
                "Conversions": conversions,
                "Cost ($)": cost,
                "CVR": cvr
            })

    df = pd.DataFrame(data)
    if df.empty:
        return df, df

    pivot = df.pivot_table(index="Day", columns="Hour", values=["Clicks", "Conversions", "Cost ($)", "CVR"], aggfunc="sum", fill_value=0)
    pivot = pivot.replace(0, "")

    for metric in ["Clicks", "Conversions", "CVR"]:
        heat_data = df.pivot_table(index="Day", columns="Hour", values=metric, aggfunc="sum", fill_value=0)
        plt.figure(figsize=(10, 6))
        sns.heatmap(heat_data, annot=True, fmt=".2f", cmap="coolwarm")
        plt.title(f"Heatmap: {metric} by Day and Hour")
        plt.tight_layout()
        plt.savefig(f"report_images/{metric}_heatmap.png")
        plt.close()

    return pivot, df
