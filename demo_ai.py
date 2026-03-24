import os
from openai import OpenAI

def grade_demo(student_text, key_text):
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    prompt = f"You are an expert examiner. Grade this student's handwritten work based on the provided answer key.\n\nANSWER KEY:\n{key_text}\n\nSTUDENT WORK:\n{student_text}\n\nProvide a fair final grade and point out any specific mistakes."
    
    # Just ONE API call! DeepSeek R1 handles the reasoning natively.
    response = client.chat.completions.create(
        model="deepseek/deepseek-r1:free",
        messages=[{"role": "user", "content": prompt}],
        extra_body={"reasoning": {"enabled": True}}
    )
    
    content = response.choices[0].message.content or ""
    raw_reasoning = getattr(response.choices[0].message, 'reasoning', None)
    
    clean_reasoning = ""
    final_answer = ""
    
    # Safely extract the thinking process depending on how OpenRouter formats it
    if raw_reasoning:
        clean_reasoning = str(raw_reasoning)
        final_answer = content
    elif "<think>" in content and "</think>" in content:
        parts = content.split("</think>")
        clean_reasoning = parts[0].replace("<think>", "").strip()
        final_answer = parts[1].strip() if len(parts) > 1 else "See reasoning above."
    else:
        clean_reasoning = "Model graded directly without a separate thinking block."
        final_answer = content
        
    return f"DEEPSEEK'S THINKING PROCESS:\n{clean_reasoning}\n\nFINAL GRADE & FEEDBACK:\n{final_answer}"