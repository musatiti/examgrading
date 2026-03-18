import os
from openai import OpenAI

def grade_demo(student_text, key_text):
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    prompt = f"Grade this student work based on the answer key.\n\nKey: {key_text}\n\nStudent: {student_text}"
    
    response = client.chat.completions.create(
        model="openrouter/hunter-alpha",
        messages=[{"role": "user", "content": prompt}],
        extra_body={"reasoning": {"enabled": True}}
    )
    
    # 1. Get the raw reasoning data
    raw_reasoning = getattr(response.choices[0].message, 'reasoning_details', "No reasoning provided.")
    
    # 2. Clean it up if it's a list/dictionary
    clean_reasoning = ""
    if isinstance(raw_reasoning, list):
        for item in raw_reasoning:
            if isinstance(item, dict) and 'text' in item:
                clean_reasoning += item['text'] + "\n"
    elif isinstance(raw_reasoning, str):
        clean_reasoning = raw_reasoning
    else:
        clean_reasoning = str(raw_reasoning)
        
    answer = response.choices[0].message.content
    
    return f"THINKING PROCESS:\n{clean_reasoning}\n\nFINAL GRADE:\n{answer}"