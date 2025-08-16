from .utils_text import clean
from .config import model

def gemini_wasted_spend_summary(df):
    if df is None or df.empty:
        return ""
    df_filtered = df[(df["Conversions"].fillna(0).astype(float) < 1.0)]
    if df_filtered.empty:
        print("ℹ️ No wasted spend rows meet criteria (Conversions == 0).")
        return "Characteristic | Insight | Recommendation\nNo wasted spend rows met the threshold | No significant spend without conversions | Consider relaxing filters or using broader date range."

    df_filtered = df_filtered.sort_values("Cost ($)", ascending=False).head(30)
    prompt = f"""
You're a senior performance marketer and Google Ads strategist.

Review the following keywords that spent significant budget but got zero conversions. 
Use columns like Quality Score, Avg CPC, CTR, and Cost to generate strategic, context-rich recommendations.

Given the keyword below, return a JSON array of insights. Each object should include:
- "Characteristic"
- "Insight" (with actual metric values)
- "Recommendation" (tactical, specific)
Return JSON. 
Avoid generic advice. Focus on actionable insights.
In insights mention the keyword for which it is generated instead of using generic statements like "this keyword". 
Only include rows with serious issues.

Avoid markdown formatting.

Data:
{df_filtered[["Keyword", "Cost ($)", "CTR", "Avg CPC", "Quality Score", "Conversions"]].to_string(index=False)}
    """
    try:
        raw_output = model.generate_content(prompt).text
        cleaned = clean(raw_output)
        # If Gemini returns malformed output we still return raw_output to avoid failing
        if '|' not in cleaned:
            print("⚠️ Gemini returned unusual wasted spend insight.")
        return raw_output
    except Exception as e:
        print(f"❌ Gemini API error (wasted): {e}")
        return ""
