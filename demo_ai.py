import os
from openai import OpenAI

def grade_demo(student_images, key_images):
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=300.0, 
    )

    # 1. The Magic: A strict, step-by-step Chain of Thought prompt
    system_prompt = """You are a highly precise and strict AI examiner. You are grading a student's handwritten exam (which may contain drawings, diagrams, and text) based on a provided answer key.

You MUST strictly follow this exact formatting and process:

## Step 1: Answer Key Extraction
(List out every correct answer you see in the key images so you have a baseline.)

## Step 2: Question-by-Question Grading
(For EVERY single question on the exam, you must provide the following bullet points:)
* Question Number: 
* Answer Key says: [What the correct answer is]
* Student wrote/drew: [Describe exactly what the student put]
* Verdict: [CORRECT / INCORRECT / PARTIAL]
* Reasoning: (Explain exactly why they got the points or lost them based ONLY on visual evidence)

## Step 3: Final Calculation
(Carefully count the total number of correct points based on your Step 2 analysis.)
FINAL SCORE: [Total Correct] / [Total Possible Questions]
"""

    content_array = [{"type": "text", "text": system_prompt}]
    
    content_array.append({"type": "text", "text": "--- START OF ANSWER KEY IMAGES ---"})
    for b64_img in key_images:
        content_array.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        })
        
    content_array.append({"type": "text", "text": "--- START OF STUDENT WORK IMAGES ---"})
    for b64_img in student_images:
        content_array.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        })

    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[{"role": "user", "content": content_array}]
    )
    
    final_answer = response.choices[0].message.content if response.choices[0].message.content else "No response generated."
        
    return final_answer