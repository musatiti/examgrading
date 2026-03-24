import os
from openai import OpenAI

def grade_demo(student_text, key_text):
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    prompt = f"Grade this student work based on the answer key.\n\nKey: {key_text}\n\nStudent: {student_text}"
    
    # ==========================================
    # CALL 1: Initial Grading & Reasoning
    # ==========================================
    response1 = client.chat.completions.create(
        model="stepfun/step-3.5-flash:free",
        messages=[{"role": "user", "content": prompt}],
        extra_body={"reasoning": {"enabled": True}}
    )
    
    # Extract the assistant's first message
    msg1 = response1.choices[0].message
    
    # CRITICAL FIX 1: Safely handle if the AI only thought and returned no text content
    safe_content = msg1.content if msg1.content is not None else ""
    
    # Build the assistant message dictionary
    assistant_memory = {
        "role": "assistant",
        "content": safe_content
    }
    
    # CRITICAL FIX 2: Only attach reasoning_details if they exist
    if hasattr(msg1, 'reasoning_details') and msg1.reasoning_details:
        assistant_memory["reasoning_details"] = msg1.reasoning_details

    # Build the history for the second call
    messages_history = [
        {"role": "user", "content": prompt},
        assistant_memory,
        {"role": "user", "content": "Are you sure? Think carefully and double-check your grading."}
    ]

    # ==========================================
    # CALL 2: Reflection & Final Grade
    # ==========================================
    response2 = client.chat.completions.create(
        model="stepfun/step-3.5-flash:free",
        messages=messages_history,
        extra_body={"reasoning": {"enabled": True}}
    )
    
    msg2 = response2.choices[0].message

    # ==========================================
    # CLEANUP: Format the output for the web page
    # ==========================================
    raw_reasoning = getattr(msg2, 'reasoning_details', "No additional reasoning provided.")
    clean_reasoning = ""
    
    # OpenRouter returns reasoning_details as a list of dictionaries, we need to extract the text
    if isinstance(raw_reasoning, list):
        for item in raw_reasoning:
            if isinstance(item, dict) and 'text' in item:
                clean_reasoning += item['text'] + "\n"
    elif isinstance(raw_reasoning, str):
        clean_reasoning = raw_reasoning
    else:
        clean_reasoning = str(raw_reasoning)
        
    final_answer = msg2.content if msg2.content else "No final response."
    
    return f"REFINED THINKING PROCESS:\n{clean_reasoning}\n\nFINAL GRADE:\n{final_answer}"