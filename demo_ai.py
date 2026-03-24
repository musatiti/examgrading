import os
from openai import OpenAI

def grade_demo(student_text, key_text):
    # Grab the key securely from the Docker environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    # Initialize the OpenRouter client
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    # Set up the strict grading instructions
    prompt = f"You are an expert examiner. Grade this student's handwritten work based on the provided answer key.\n\nANSWER KEY:\n{key_text}\n\nSTUDENT WORK:\n{student_text}\n\nProvide a fair final grade and point out any specific mistakes."
    
    # Make the API call using the stable Llama 3.3 70B free endpoint
    response = client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct:free",
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Extract the AI's response
    final_answer = response.choices[0].message.content
        
    return f"FINAL GRADE & FEEDBACK:\n{final_answer}"