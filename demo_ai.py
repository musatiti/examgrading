import os
import time
from openai import OpenAI

def grade_demo(student_images, key_images):
    # Grab the key securely from the Docker environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    # Initialize the OpenRouter client
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=300.0, 
    )

    # NO MORE ROULETTE. Lock in the smart, proven model.
    model_id = "qwen/qwen3.6-plus:free"
    max_retries = 3

    # ==========================================
    # ONE-SHOT VISUAL GRADING PIPELINE
    # ==========================================
    grading_prompt = """You are a strict, expert AI examiner grading a student's exam.
    
    I am providing you with two sets of images:
    1. The official Answer Key.
    2. The Student's Exam.

    CRITICAL GRADING RULES:
    1. DIRECT VISUAL COMPARISON: Look directly at the drawings, diagrams, circuits, and handwritten answers in the Student Exam and compare them visually to the Answer Key. Do they match in shape, logic, and content?
    2. ANTI-CHEATING (IGNORE RED INK): The student exam may already have grades, scores (like "13" or "10.5"), checkmarks, or red "X"s written on it by a human. YOU MUST COMPLETELY IGNORE THESE. Grade purely on the student's raw pencil/pen work.
    3. STRICT SPATIAL AWARENESS: Only grade what is inside the official answer boxes or designated drawing areas.

    For EVERY question found in the exam, use this exact template:
    
    * Question: [Section] - [Number]
    * Key Shows: [Brief visual description of the key's answer/drawing]
    * Student Drew/Wrote: [Brief visual description of what the student did]
    * Verdict: [CORRECT / INCORRECT / PARTIAL / BLANK]
    * Reasoning: [1 short sentence explaining the visual match or mismatch. DO NOT output your internal math or monologue.]
    
    End with:
    FINAL SCORE: [Total Earned] / [Total Possible] 
    """

    # Build the message payload
    content = [{"type": "text", "text": grading_prompt}]
    
    # Attach Key Images First
    content.append({"type": "text", "text": "--- OFFICIAL ANSWER KEY IMAGES ---"})
    for b64_img in key_images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        })
        
    # Attach Student Images Second
    content.append({"type": "text", "text": "--- STUDENT EXAM IMAGES ---"})
    for b64_img in student_images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        })

    # Retry Loop
    for attempt in range(max_retries):
        try:
            print(f"Visually Grading Exam (Attempt {attempt + 1})...")
            final_response = client.chat.completions.create(
                model=model_id, 
                messages=[{"role": "user", "content": content}]
            )
            
            final_grade = final_response.choices[0].message.content if final_response.choices[0].message.content else "No response generated."
            
            actual_model = final_response.model
            return f"--- GRADING ENGINE: {actual_model.upper()} ---\n\n{final_grade}"
            
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(5) 
                continue 
            return f"API ERROR DURING GRADING:\n{str(e)}\n\nPlease try again later."
            