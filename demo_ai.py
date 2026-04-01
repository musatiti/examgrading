import os
from openai import OpenAI

def grade_demo(student_images, key_images):
    # Grab the key securely from the Docker environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    # Initialize the OpenRouter client with a 5-minute safety timeout
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=300.0, 
    )

    # The strict, hallucination-proof prompt
    system_prompt = """You are a highly precise, universal AI examiner. You are grading a student's handwritten exam based on a provided answer key.

CRITICAL GRADING RULES:
1. EXAM HIERARCHY (SECTIONS VS. QUESTIONS): You must map the exam structure perfectly. Pay strict attention to "Sections" (e.g., Q1, Part A) versus "Sub-questions" (e.g., 1, 2, 3). Do NOT mix questions from different sections together.
2. POINT WEIGHT DISTRIBUTION: If a Section Header says "(15 points)" and contains 10 sub-questions, you MUST divide the points equally (1.5 pts each). Do not assign the total section points to a single question.
3. SPATIAL AWARENESS: Look for strict formatting rules. If the exam has a dedicated "Answers Table", "Final Answer Box", or specific blanks, you MUST prioritize grading what is inside those areas.
4. ANTI-HALLUCINATION: Do NOT guess. If a student's handwriting, math, or diagram is completely illegible, or if a box is left blank, state "BLANK/ILLEGIBLE" and award 0 points. 
5. PARTIAL CREDIT: If a question requires a drawing or multi-step math equation, evaluate the components. Award PARTIAL points if some elements are correct but others are missing.

You MUST strictly follow this exact formatting:

## Step 1: Exam Structure
(List each Section, how many sub-questions it contains, and the exact point value of each sub-question).

## Step 2: Question-by-Question Grading
(Group your grading by Section. For EVERY question provide:)
* Question: [Section] - [Number]
* Expected Answer: [Exactly what the key says]
* Student Answer: [Exactly what the student wrote/drew, and WHERE you found it]
* Verdict: [CORRECT / INCORRECT / PARTIAL]
* Points Awarded: [X] / [Y] pts

## Step 3: Final Score Calculation
(Show your addition)
FINAL SCORE: [Total Points Earned] / [Total Possible Points]
"""

    # 1. Start the message with our text instructions
    content_array = [{"type": "text", "text": system_prompt}]
    
    # 2. Attach all pages of the Answer Key as images
    content_array.append({"type": "text", "text": "--- START OF ANSWER KEY IMAGES ---"})
    for b64_img in key_images:
        content_array.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        })
        
    # 3. Attach all pages of the Student Work as images
    content_array.append({"type": "text", "text": "--- START OF STUDENT WORK IMAGES ---"})
    for b64_img in student_images:
        content_array.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        })

    # 4. Use the API inside a safety block
    try:
        # Hardcoding the powerful, consistent Gemini 2.0 Flash Experimental model (100% Free)
        response = client.chat.completions.create(
            model="meta-llama/llama-3.2-90b-vision-instruct:free", 
            messages=[{"role": "user", "content": content_array}]
        )
        
        final_answer = response.choices[0].message.content if response.choices[0].message.content else "No response generated."
        return f"FINAL GRADE & FEEDBACK:\n{final_answer}"
        
    except Exception as e:
        # If the API crashes or times out, display the error on the screen cleanly
        return f"API ERROR ENCOUNTERED:\n{str(e)}\n\nPlease try again."