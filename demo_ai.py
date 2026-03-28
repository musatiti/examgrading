import os
from openai import OpenAI

def grade_demo(student_text, key_text):
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    # 300s timeout added to the client as well for safety
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=300.0, 
    )

    prompt = f"You are an expert examiner. Grade this student's handwritten work based on the provided answer key.\n\nANSWER KEY:\n{key_text}\n\nSTUDENT WORK:\n{student_text}\n\nProvide a fair final grade and point out any specific mistakes."
    
    response = client.chat.completions.create(
        model="openrouter/hunter-alpha",
        messages=[{"role": "user", "content": prompt}],
        extra_body={"reasoning": {"enabled": True}}
    )
    
    msg = response.choices[0].message
    raw_reasoning = getattr(msg, 'reasoning_details', "No reasoning provided.")
    
    # Safely clean up the reasoning details
    clean_reasoning = ""
    if isinstance(raw_reasoning, list):
        for item in raw_reasoning:
            if isinstance(item, dict) and 'text' in item:
                clean_reasoning += item['text'] + "\n"
    elif isinstance(raw_reasoning, str):
        clean_reasoning = raw_reasoning
    else:
        clean_reasoning = str(raw_reasoning)
        
    final_answer = msg.content if msg.content else "No final response."
    
    return f"HUNTER ALPHA THINKING PROCESS:\n{clean_reasoning}\n\nFINAL GRADE & FEEDBACK:\n{final_answer}"