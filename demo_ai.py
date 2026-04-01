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
    system_prompt = """You are a highly precise, universal AI examiner. You are grading a student's handwritten exam based on a provided answer key. You must adapt to whatever format the exam is in (multiple choice, essays, math, logic diagrams, etc.).

CRITICAL GRADING RULES:
1. EXAM DISCOVERY & POINT WEIGHTS: Carefully analyze the Answer Key to determine the structure of the exam. You MUST look for point values assigned to specific questions or sections (e.g., "[2.5 points]", "(15 points)"). Calculate the student's score based on these specific weights. (If a section is worth 15 points and has 10 questions, each question is worth 1.5 points).
2. SPATIAL AWARENESS: Look for strict formatting rules. If the exam has a dedicated "Answers Table", "Final Answer Box", or specific blanks, you MUST prioritize grading what is inside those areas.
3. ANTI-HALLUCINATION: Do NOT guess. If a student's handwriting, math, or diagram is completely illegible, or if a box is left blank, state "BLANK/ILLEGIBLE" and award 0 points. Do not invent text or numbers to make it match the key.
4. PARTIAL CREDIT: If a question requires a drawing, diagram, or multi-step math equation, evaluate the components. Award PARTIAL points based on the total weight of the question if some elements are correct but others are missing or wrong.

You MUST strictly follow this exact formatting for your output:

## Step 1: Exam Structure & Key Extraction
(Briefly describe the format of the exam, list the expected correct answers, and explicitly state how many points each question is worth).

## Step 2: Question-by-Question Grading
(For EVERY question found in the key, provide the following:)
* Question: [Number/ID] ([Points Possible] pts)
* Expected Answer: [Exactly what the key says]
* Student Answer: [Exactly what the student wrote/drew, and WHERE you found it]
* Verdict: [CORRECT / INCORRECT / PARTIAL]
* Points Awarded: [X] / [Y] pts
* Reasoning: (Explain the logic for the verdict based strictly on visual evidence)

## Step 3: Final Score Calculation
(Show your addition for the points earned)
FINAL SCORE: [Total Points Earned] / [Total Possible Points]
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