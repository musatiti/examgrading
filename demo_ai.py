import os
from openai import OpenAI

def grade_demo(student_text, key_text):
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    # --- INITIAL PROMPT ---
    prompt = f"Grade this student work based on the answer key.\n\nKey: {key_text}\n\nStudent: {student_text}"
    messages = [{"role": "user", "content": prompt}]
    
    # --- FIRST API CALL ---
    response1 = client.chat.completions.create(
        model="stepfun/step-3.5-flash:free",
        messages=messages,
        extra_body={"reasoning": {"enabled": True}}
    )
    
    # Extract the assistant message object
    assistant_message = response1.choices[0].message
    
    # --- PREPARE FOR SECOND CALL (REFLECTION) ---
    # We must construct the assistant message dictionary carefully
    assistant_dict = {
        "role": "assistant",
        "content": assistant_message.content
    }
    
    # Only append reasoning_details if the model actually provided them
    if hasattr(assistant_message, 'reasoning_details') and assistant_message.reasoning_details:
        assistant_dict["reasoning_details"] = assistant_message.reasoning_details
        
    messages.append(assistant_dict)
    
    # Add the follow-up prompt asking it to double-check
    messages.append({
        "role": "user", 
        "content": "Are you sure? Think carefully and double-check your grading for any mistakes."
    })

    # --- SECOND API CALL ---
    response2 = client.chat.completions.create(
        model="stepfun/step-3.5-flash:free",
        messages=messages,
        extra_body={"reasoning": {"enabled": True}}
    )
    
    final_message = response2.choices[0].message
    
    # --- CLEANUP & RETURN ---
    raw_reasoning = getattr(final_message, 'reasoning_details', "No reasoning provided.")
    
    clean_reasoning = ""
    if isinstance(raw_reasoning, list):
        for item in raw_reasoning:
            if isinstance(item, dict) and 'text' in item:
                clean_reasoning += item['text'] + "\n"
    elif isinstance(raw_reasoning, str):
        clean_reasoning = raw_reasoning
    else:
        clean_reasoning = str(raw_reasoning)
        
    final_answer = final_message.content
    
    return f"REFINED THINKING PROCESS:\n{clean_reasoning}\n\nFINAL GRADE:\n{final_answer}"