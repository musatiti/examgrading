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
    system_prompt = """You are a highly precise and strict AI examiner. You are grading a student's handwritten exam based on a provided answer key. 

CRITICAL GRADING RULES:
1. For Q1 (Multiple Choice), you MUST ONLY look at the "Answers table" located at the bottom of Page 2. Do not look at circles or marks on the questions themselves. Compare the student's letter (a, b, c, d) directly to the key's letter.
2. For Q2 (Logic Design), read the handwritten numbers in the tables carefully. If a box is blank or illegible, mark it as "BLANK/ILLEGIBLE". Do not guess or make up numbers.
3. For Q2.5 (Circuit Diagram), the student must draw the internal logic gates of the carryout. If they draw block diagrams (like chaining 'add' boxes together), they lose points.

You MUST strictly follow this exact formatting:

## Step 1: Q1 Answer Key Extraction
(List the correct letters 1-10 from the Answer Key's table)

## Step 2: Q1 Grading
(List each question 1-10. State the Key Letter vs the Student Letter. Give a VERDICT: CORRECT / INCORRECT).

## Step 3: Q2 Grading
(For Q2.1 through Q2.5, state exactly what the Key table says vs what the Student table says. Give a VERDICT: CORRECT / INCORRECT / PARTIAL, and explain why).

## Step 4: Final Score
(Calculate the final exact score).
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