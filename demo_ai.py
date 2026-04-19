import os
import time
from openai import OpenAI

def grade_demo(student_images, key_images):
    # Grab the GitHub token securely from the environment
    github_token = os.getenv("GITHUB_TOKEN")
    
    # A quick safety check just in case Docker forgets the key
    if not github_token:
        return "API ERROR: GITHUB_TOKEN environment variable not found. Please check your .env or export command."

    # Initialize the client for GitHub Models (Azure)
    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=github_token,
        timeout=300.0, 
    )

    # Using the flagship GPT-4o model for maximum logic and reasoning
    model_id = "gpt-4o"
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
    4. LOGIC CHECK: If the Student's answer visually or textually matches the Key, the Verdict MUST be CORRECT. Do not contradict yourself.

    --- TRAINING EXAMPLES (Edge Cases to Watch Out For) ---
    Example A: The "Don't Care" State
    If the Answer Key shows S0=X (a "don't care" state), and the student wrote S0=0 or S0=1, mark it CORRECT.

    Example B: Partial Drawing Matches
    If the Answer Key shows a full adder with a carry-out wire, and the student drew the full adder but forgot the final carry-out wire, mark it INCORRECT. Close is not enough.

    Example C: Illegible Handwriting
    If you cannot definitively read the student's handwriting, mark it PARTIAL and explicitly state "Handwriting illegible" in the Reasoning.
    -------------------------------------------------------

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
            print(f"Visually Grading Exam via GitHub Models ({model_id}) (Attempt {attempt + 1})...")
            final_response = client.chat.completions.create(
                model=model_id, 
                messages=[{"role": "user", "content": content}]
            )
            
            final_grade = final_response.choices[0].message.content if final_response.choices[0].message.content else "No response generated."
            
            actual_model = final_response.model
            return f"--- GRADING ENGINE: {actual_model.upper()} ---\n\n{final_grade}"
            
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                print("Rate limited, waiting 5 seconds...")
                time.sleep(5) 
                continue 
            return f"API ERROR DURING GRADING:\n{str(e)}\n\nPlease try again later."