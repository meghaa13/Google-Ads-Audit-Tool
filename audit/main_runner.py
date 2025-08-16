from concurrent.futures import ThreadPoolExecutor, as_completed
from .fetch_campaigns import fetch_campaign_data
from .fetch_keywords import fetch_keyword_data
from .fetch_landing_pages import fetch_landing_page_data
from .fetch_hourly import fetch_hourly_performance_data
from .fetch_geo import fetch_geo_performance_data
from .gemini_campaigns import gemini_summary
from .gemini_keywords import gemini_keyword_summary
from .gemini_hourly import gemini_hourly_summary
from .gemini_geo import gemini_geo_summary
from .gemini_wasted import gemini_wasted_spend_summary
from .gemini_lp_audit import run_landing_page_audits
from .gemini_competitor import generate_competitor_insights
from .utils_analysis import wasted_spend_analyzer, gemini_summary_risks_opps
from .report_generator import generate_report
from .config import model
import pandas as pd


def generate_google_ads_report(customer_id, google_ads_client):
    """
    Orchestrates fetching, Gemini summarization and report generation in parallel.
    Signature matches how app.py calls it.
    """

    # 1) Fetch data in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(fetch_campaign_data, google_ads_client, customer_id, "LAST_30_DAYS"): "campaigns",
            executor.submit(fetch_keyword_data, google_ads_client, customer_id): "keywords",
            executor.submit(fetch_landing_page_data, google_ads_client, customer_id): "landing_pages",
            executor.submit(fetch_hourly_performance_data, google_ads_client, customer_id): "hourly",
            executor.submit(fetch_geo_performance_data, google_ads_client, customer_id): "geo"
        }

        results = {}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                res = fut.result()
                results[name] = res
                print(f"ℹ️ Fetched: {name}")
            except Exception as e:
                print(f"❌ Error in fetch {name}: {e}")
                results[name] = pd.DataFrame() if name != "hourly" else (pd.DataFrame(), pd.DataFrame())

    df_campaign = (
        results.get("campaigns", pd.DataFrame())
        .sort_values("Cost ($)", ascending=False)
        .head(30)
                if results.get("campaigns") is not None
        else pd.DataFrame()
    )
    kw_df = (
        results.get("keywords", pd.DataFrame())
        .sort_values("Cost ($)", ascending=False)
        .head(50)
        if results.get("keywords") is not None
        else pd.DataFrame()
    )
    lp_df = results.get("landing_pages", pd.DataFrame())
    hour_pivot, hour_raw_df = results.get("hourly", (pd.DataFrame(), pd.DataFrame()))
    geo_df = (
        results.get("geo", pd.DataFrame())
        .sort_values("Cost ($)", ascending=False)
        .head(50)
        if results.get("geo") is not None
        else pd.DataFrame()
    )

    # 2) Run Gemini / audits in parallel
    with ThreadPoolExecutor(max_workers=7) as executor:
        f_risk_opps = executor.submit(gemini_summary_risks_opps, df_campaign)  # ✅ New Risks/Opportunities
        f_insight_30 = executor.submit(gemini_summary, df_campaign, "Campaigns")
        f_insight_kw = executor.submit(gemini_keyword_summary, kw_df)
        f_insight_hour = executor.submit(gemini_hourly_summary, hour_raw_df)
        f_insight_geo = executor.submit(gemini_geo_summary, geo_df)
        f_wasted = executor.submit(gemini_wasted_spend_summary, kw_df)
        f_lp_audit = executor.submit(run_landing_page_audits, lp_df, 5)

        # Competitor insights (safe execution)
        try:
            f_competitor = executor.submit(
                generate_competitor_insights,
                kw_df,
                lp_df,
                lp_df["Final URL"].iloc[0]
                if (lp_df is not None and not lp_df.empty)
                else "",
                model,
            )
        except Exception:
            f_competitor = None

        # Collect results
        risk_opp_data = f_risk_opps.result() if f_risk_opps else {"Risks": [], "Opportunities": []}
        insight_30 = f_insight_30.result() if f_insight_30 else ""
        insight_kw = f_insight_kw.result() if f_insight_kw else ""
        insight_hour = f_insight_hour.result() if f_insight_hour else ""
        insight_geo = f_insight_geo.result() if f_insight_geo else ""
        wasted_insight = f_wasted.result() if f_wasted else ""
        lp_audit_rows = f_lp_audit.result() if f_lp_audit else []
        competitor_df = f_competitor.result() if (f_competitor is not None) else None

    # 3) Additional lightweight analysis
    wasted_flags = wasted_spend_analyzer(kw_df)

    # 4) Generate report
    filename = generate_report(
        df_campaign, kw_df, hour_pivot, hour_raw_df,
        insight_30, insight_kw, insight_hour,
        geo_df, insight_geo,
        wasted_flags=wasted_flags,
        wasted_insight=wasted_insight,
        lp_audit_rows=lp_audit_rows,
        risk_opp_insights=risk_opp_data,  # ✅ Dict instead of raw text
        lp_flags=None,
        competitor_insights=competitor_df
    )

    return filename
