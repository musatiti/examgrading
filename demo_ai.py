import os
import time
from openai import OpenAI

def grade_demo(student_images, key_images):
    api_key = os.getenv("OPENROUTER_API_KEY")
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=300.0, 
    )

    model_id = "google/gemma-3-27b-it:free"
    max_retries = 3

    # ==========================================
    # PHASE 1: EXTRACT THE ANSWER KEY ONLY
    # ==========================================
    key_prompt = """You are an expert examiner. Look at the attached Answer Key images.
    Extract every correct answer into a clean, numbered text list. 
    Note the point values for each section if they are written on the pages.
    Do NOT grade anything. Just output the pure Answer Key text."""

    key_content = [{"type": "text", "text": key_prompt}]
    for b64_img in key_images:
        key_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        })

    extracted_key_text = ""
    
    # Retry Loop for Phase 1
    for attempt in range(max_retries):
        try:
            print(f"Extracting Answer Key (Attempt {attempt + 1})...")
            key_response = client.chat.completions.create(
                model=model_id, 
                messages=[{"role": "user", "content": key_content}]
            )
            extracted_key_text = key_response.choices[0].message.content
            break  # It worked! Break out of the retry loop and move to Phase 2
            
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(5) # Wait 5 seconds and try again
                continue
            return f"API ERROR DURING KEY EXTRACTION:\n{str(e)}\n\nPlease try again later."

    # ==========================================
    # PHASE 2: GRADE THE STUDENT EXAM ONLY
    # ==========================================
    grading_prompt = f"""You are a strict AI examiner. 
    
    Here is the official Answer Key text:
    ---
    {extracted_key_text}
    ---

    CRITICAL GRADING RULES:
    1. STRICT SPATIAL AWARENESS: Look at the attached Student Exam images. YOU MUST ONLY GRADE WHAT IS WRITTEN INSIDE OFFICIAL ANSWER BOXES/TABLES. Completely ignore scratchpad work, margin notes, crossed-out text, or circles drawn on the question text itself.
    2. Compare the student's written answer to the official Answer Key text provided above.
    3. ANTI-HALLUCINATION: DO NOT guess. If the student wrote something different than the key, mark it INCORRECT. If the official answer box is empty or illegible, mark it BLANK (0 points) even if there is work elsewhere on the page.
    4. POINT WEIGHTS: Use the point values from the key. If a section is worth 15 points and has 10 questions, each is 1.5 points.
    
    Output the final grade question-by-question, grouped by section, followed by the FINAL SCORE calculation."""

    student_content = [{"type": "text", "text": grading_prompt}]
    for b64_img in student_images:
        student_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        })

    # Retry Loop for Phase 2
    for attempt in range(max_retries):
        try:
            print(f"Grading Student Exam (Attempt {attempt + 1})...")
            final_response = client.chat.completions.create(
                model=model_id, 
                messages=[{"role": "user", "content": student_content}]
            )
            
            final_grade = final_response.choices[0].message.content if final_response.choices[0].message.content else "No response generated."
            return f"PHASE 1 (EXTRACTED KEY):\n{extracted_key_text}\n\n=========================\n\nPHASE 2 (FINAL GRADE & FEEDBACK):\n{final_grade}"
            
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(5) 
                continue 
            return f"API ERROR DURING GRADING:\n{str(e)}\n\nPlease try again later."