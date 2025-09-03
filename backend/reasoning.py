import google.generativeai as genai

def generate_reasoning(stock_info: str, headlines: list, api_key: str) -> str:
    """Use Gemini API to generate reasoning from news headlines."""
    if not api_key:
        return "Gemini API key not found."

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-pro")

        headlines_text = "\n".join([f"- {h['title']}" for h in headlines]) if headlines else "No major news available."
        prompt = f"""
        Stock Analysis:
        {stock_info}


        Please summarize why this stock may have moved in a way that a retail investor can easily understand. 
        - Use simple language. 
        - Give 3-5 clear bullet points explaining the key reasons. 
        - Highlight any major positive or negative factors affecting the stock price.
        - Avoid technical jargon.
        - Keep it concise and actionable.
        """

        response = model.generate_content(prompt)
        return response.text if response and response.text else "No explanation generated."
    except Exception as e:
        return f"Error generating reasoning: {str(e)}"
