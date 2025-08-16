from .utils_text import clean
from .config import model
import json

def gemini_hourly_summary(df):
    if df is None or df.empty:
        return "[]"

    prompt = f"""
You're a Google Ads dayparting analyst.
Based on the following hourly performance data, identify key pattern and optimization opportunities. 

Analyze this hourly performance table and return a **valid JSON array** only.

Rules:
- Each object must have "Characteristic", "Insight", "Recommendation".
- No markdown, no extra commentary.
- Keep each value as a single string.
- Only include meaningful, actionable rows.

Data:
{df.to_string(index=False)}
"""

    try:
        raw = model.generate_content(prompt).text.strip()
        data = json.loads(raw)
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Gemini API error in hourly summary: {e}")
        return "[]"
