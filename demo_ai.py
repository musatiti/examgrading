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

    try:
        print("Extracting Answer Key...")
        key_response = client.chat.completions.create(
            model=model_id, 
            messages=[{"role": "user", "content": key_content}]
        )
        extracted_key_text = key_response.choices[0].message.content
    except Exception as e:
        return f"API ERROR DURING KEY EXTRACTION:\n{str(e)}"

    # ==========================================
    # PHASE 2: GRADE THE STUDENT EXAM ONLY
    # ==========================================
    grading_prompt = f"""You are a strict AI examiner. 
    
    Here is the official Answer Key text:
    ---
    {extracted_key_text}
    ---

    CRITICAL GRADING RULES:
    1. Look at the attached Student Exam images. ONLY read answers from the official answer boxes/tables. Ignore scratchpad notes.
    2. Compare the student's written answer to the official Answer Key text provided above.
    3. DO NOT hallucinate. If the student wrote something different than the key, mark it INCORRECT. If the box is empty or illegible, mark it BLANK (0 points).
    
    Output the final grade question-by-question, followed by the FINAL SCORE."""

    student_content = [{"type": "text", "text": grading_prompt}]
    for b64_img in student_images:
        student_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        })

    # Retry logic for the grading phase
    max_retries = 3
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