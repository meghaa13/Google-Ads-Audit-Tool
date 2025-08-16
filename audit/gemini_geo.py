from .utils_text import clean
from .config import model

def gemini_geo_summary(df):
    if df is None or df.empty:
        return ""
    prompt = f"""You're a Google Ads geo-performance analyst.
Analyze the following geographic performance data. Each row includes city, region, country, cost, and conversion metrics.

Given the campaign data below, return a JSON array of insights. Each object should include:
- "Characteristic/ Location"
- "Insight" (with actual metric values)
- "Recommendation" (tactical, specific)
Return json 
Only include high-impact rows:
- Low CPA + High CVR
- High spend + low conversion
- Cities or regions over/underperforming

Avoid generic advice. Focus on tactical recommendations using exact values.
Avoid markdown formatting.
Data:
{df.head(30).to_string(index=False)}
"""
    try:
        return clean(model.generate_content(prompt).text)
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        return ""
