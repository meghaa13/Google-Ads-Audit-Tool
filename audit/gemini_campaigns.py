# audit/gemini_campaigns.py
from .config import model
from .utils_text import clean, parse_and_repair

def gemini_summary(df, label="Campaigns"):
    """
    Returns a JSON **string** (list[dict]) with clean fields:
      - Characteristic
      - Insight
      - Recommendation
    Always valid JSON. Never markdown. Never multi-line field breaks.
    """
    # Defensive: if df empty, return empty JSON array
    try:
        data_str = df.head(30).to_string(index=False)
    except Exception:
        data_str = ""

    prompt = f"""
You're a senior Google Ads strategist.

Given the {label} data below, return a JSON array of insights.
Each object MUST include:
- "Characteristic"
- "Insight"           (use actual metric values from the table)
- "Recommendation"    (tactical, specific)

HARD RULES:
- Output JSON ONLY. No markdown, no extra narration.
- Return a JSON ARRAY (like: [{{...}}, {{...}}]).
- Keep each value on one line (no embedded newlines).
- Avoid generic advice; reference the table data.

Data:
{data_str}
"""

    try:
        raw = (model.generate_content(prompt).text or "").strip()
        insights = parse_and_repair(raw)
        if not isinstance(insights, list):
            return []
        return insights
    except Exception as e:
        print(f"❌ Gemini API error in gemini_summary: {e}")
        return []
