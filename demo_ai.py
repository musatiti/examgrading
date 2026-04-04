import time
from openai import OpenAI

def grade_demo(student_images, key_images):
    # Connect directly to your local Ollama instance running on your PC
    # 'host.docker.internal' is the bridge that lets Docker talk to Windows/Mac
    client = OpenAI(
        base_url="http://host.docker.internal:11434/v1",
        api_key="ollama-local", # Required by the library, but Ollama ignores it
        timeout=300.0, 
    )

    # Using the lightweight Moondream vision model we just downloaded
    model_id = "moondream"
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
            break  
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(5) 
                continue
            return f"LOCAL API ERROR DURING KEY EXTRACTION:\n{str(e)}\n\nPlease ensure Ollama is running."

    # ==========================================
    # PHASE 2: GRADE THE STUDENT EXAM ONLY
    # ==========================================
    grading_prompt = f"""You are a strict, literal AI examiner. 
    
    Here is the official Answer Key text:
    ---
    {extracted_key_text}
    ---

    CRITICAL GRADING RULES:
    1. STRICT SPATIAL AWARENESS: Look at the attached Student Exam images. YOU MUST ONLY GRADE WHAT IS WRITTEN INSIDE OFFICIAL ANSWER BOXES/TABLES. 
    2. MANDATORY COMPARISON: You are forbidden from giving a verdict without explicitly printing the Key's answer and the Student's answer right next to each other first. If they do not match exactly, mark it INCORRECT.
    3. ANTI-HALLUCINATION: If the official answer box is empty or illegible, mark it BLANK (0 points).
    
    YOU MUST USE THIS EXACT TEMPLATE FOR EVERY SINGLE QUESTION. DO NOT DEVIATE:
    
    * Question: [Section] - [Number]
    * Key Says: [Exactly what Phase 1 extracted]
    * Student Wrote: [Exactly what is in the box]
    * Verdict: [CORRECT / INCORRECT / BLANK]
    
    End with:
    FINAL SCORE: [Total Earned] / [Total Possible]
    """

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
            if attempt < max_retries - 1:
                time.sleep(5) 
                continue 
            return f"LOCAL API ERROR DURING GRADING:\n{str(e)}\n\nPlease ensure Ollama is running."