from .utils_text import clean
from .config import model

def gemini_keyword_summary(df):
    if df is None or df.empty:
        return ""
    prompt = f"""
You're a Google Ads keyword analyst.
Given the campaign data below, return a JSON array of insights. Each object should include:
- "Characteristic"
- "Insight" (with actual metric values)
- "Recommendation" (tactical, specific)
Avoid generic advice. Focus on actionable insights.
Return json 
Avoid markdown formatting.
Data:
{df.head(30).to_string(index=False)}
"""
    try:
        return clean(model.generate_content(prompt).text)
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        return ""
