from .utils_text import clean, parse_and_repair
from .config import model
import json
import re

def gemini_summary_risks_opps(df):
    """
    Ask Gemini to analyze performance data and return Risks & Opportunities as JSON.
    Always returns a dict with keys 'Risks' and 'Opportunities'.
    """
    if df is None or df.empty:
        return {"Risks": [], "Opportunities": []}

    prompt = f"""
You're a senior Google Ads strategist. Analyze this performance data and return a JSON object with two arrays:

- "Risks": list of top 3 high-risk observations
- "Opportunities": list of top 3 strong wins or improvements

Return ONLY a valid JSON object with this exact structure:

{{
  "Risks": [
    {{"Characteristic": "...", "Insight": "...", "Recommendation": "..."}},
    {{"Characteristic": "...", "Insight": "...", "Recommendation": "..."}}
  ],
  "Opportunities": [
    {{"Characteristic": "...", "Insight": "...", "Recommendation": "..."}},
    {{"Characteristic": "...", "Insight": "...", "Recommendation": "..."}}
  ]
}}

- Provide up to 3 items in each list.
- No explanations, no markdown, no text outside JSON.

Data:
{df.head(30).to_string(index=False)}
"""

    try:
        raw = model.generate_content(prompt).text or ""
        cleaned = clean(raw)

        # --- First try strict parse
        parsed = parse_and_repair(cleaned)

        # --- Fallback: regex extract JSON if necessary
        if not isinstance(parsed, dict):
            import re, json
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group())
                except Exception:
                    parsed = {}

        if isinstance(parsed, dict):
            return {
                "Risks": parsed.get("Risks", []),
                "Opportunities": parsed.get("Opportunities", [])
            }

        print(f"⚠️ Unexpected Gemini output (not dict): {raw}")
        return {"Risks": [], "Opportunities": []}

    except Exception as e:
        print(f"❌ Gemini summary risks/opps error: {e}")
        return {"Risks": [], "Opportunities": []}

def extract_summary_highlights(df):
    """
    Uses Gemini to return top 3 Risks and top 3 Opportunities from performance data.
    """
    result = gemini_summary_risks_opps(df)
    risks = result.get("Risks", [])[:3]
    opportunities = result.get("Opportunities", [])[:3]
    return risks, opportunities


def wasted_spend_analyzer(df):
    flags = []
    if df is None:
        return flags
    for _, row in df.iterrows():
        cost = row.get("Cost ($)", 0)
        conversions = row.get("Conversions", 0)
        cpc = row.get("Avg CPC", 0)
        qs = row.get("Quality Score", 10)

        if conversions == 0:
            flags.append((row.get("Keyword", "N/A"), "High Spend, Zero Conversions", f"Wasted: ${cost:.2f}"))

        if qs < 5 and cpc > 5:
            flags.append((row.get("Keyword", "N/A"), "Low QS + High CPC", "Consider pausing or fixing"))
    return flags


def landing_page_flags(df):
    flags = []
    if df is None:
        return flags
    for _, row in df.iterrows():
        if row.get("Quality Score", 10) < 5:
            flags.append((row.get("Keyword", "N/A"), f"QS: {row['Quality Score']}", "Revamp Landing Page"))
    return flags



