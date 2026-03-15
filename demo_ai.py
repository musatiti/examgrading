import os
from openai import OpenAI

def grade_demo(student_text, key_text):
    # Grab the key from the Docker environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    # Initialize the client HERE
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
    
    reasoning = getattr(response.choices[0].message, 'reasoning_details', "No reasoning provided.")
    answer = response.choices[0].message.content
    
    return f"THINKING PROCESS:\n{reasoning}\n\nFINAL GRADE:\n{answer}"