import os
import time
import re
from openai import OpenAI

def grade_batch_exams(student_submissions, key_images):
    """
    Expects:
    - student_submissions: A dictionary {"Student_1.pdf": [img1, img2], "Student_2.pdf": [img1, img2]}
    - key_images: A list of base64 images for the Answer Key
    """
    github_token = os.getenv("GITHUB_TOKEN")
    
    if not github_token:
        return "API ERROR: GITHUB_TOKEN environment variable not found."

    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=github_token,
        timeout=300.0, 
    )

    model_id = "gpt-4o"
    max_retries = 3

    grading_prompt = """You are a strict, expert AI examiner grading a single page of a student's exam.
    
    I am providing you with exactly two images:
    1. The official Answer Key (for this specific page).
    2. The Student's Exam (for this specific page).

    CRITICAL GRADING RULES:
    1. DIRECT VISUAL COMPARISON: Look directly at the Student Exam. You MUST read exactly what the student wrote. Do not assume it matches the key. If the student wrote 'a' and the key says 'b', you must mark it INCORRECT.
    2. IGNORE THE ANSWER TABLE: Do NOT grade the summary "Answers table" grid at the bottom of the page. ONLY grade the individual questions where they are written.
    3. ANTI-CHEATING (IGNORE RED INK): Completely ignore any red ink, human grades, or checkmarks.
    4. LOGIC CHECK: If the Student's written answer matches the Key, output CORRECT. If it differs in any way, output INCORRECT.
    5. NO SUMMARIES: Output ONLY the grading templates. Do not output a total score, final evaluation, or any conversational text at the end of the page.
    6. POINTS EXTRACTION: Determine the point value for each question. Look closely for explicit labels. If a section says "(15 points)" and has 10 questions, assign 1.5 points per question. If the Verdict is CORRECT, Points Earned = Points Possible. If INCORRECT, Points Earned = 0.

    --- TRAINING EXAMPLES (Edge Cases to Watch Out For) ---
    Example A: The "Don't Care" State
    If the Answer Key shows S0=X (a "don't care" state), and the student wrote S0=0 or S0=1, mark it CORRECT.

    Example B: Partial Drawing Matches
    If the Answer Key shows a full adder with a carry-out wire, and the student drew the full adder but forgot the final carry-out wire, mark it INCORRECT. Close is not enough.

    Example C: Illegible Handwriting
    If you cannot definitively read the student's handwriting, mark it PARTIAL and explicitly state "Handwriting illegible" in the Reasoning.
    -------------------------------------------------------

    For EVERY question found on THIS PAGE, use this exact template:
    
    * Question: [Section] - [Number]
    * Key Shows: [Brief visual description of the key's answer/drawing]
    * Student Drew/Wrote: [Brief visual description of what the student did]
    * Verdict: [CORRECT / INCORRECT / PARTIAL / BLANK]
    * Points: [Earned] / [Possible]
    * Reasoning: [1 short sentence explaining the visual match or mismatch.]
    
    If there are no questions on this page to grade, simply output: "No gradable questions found on this page."
    """

    master_report = f"--- BATCH GRADING ENGINE: {model_id.upper()} (PAGE-BY-PAGE MODE) ---\n"

    for student_name, student_images in student_submissions.items():
        student_report = f"\n\n========================================\n"
        student_report += f" GRADING REPORT: {student_name}\n"
        student_report += f"========================================\n\n"
        
        if len(student_images) != len(key_images):
            student_report += f"WARNING: {student_name} has {len(student_images)} pages, but the Answer Key has {len(key_images)} pages. Grading matched pages only.\n\n"

        for page_idx, (key_page, student_page) in enumerate(zip(key_images, student_images)):
            page_num = page_idx + 1
            student_report += f"--- PAGE {page_num} ---\n"
            
            content = [{"type": "text", "text": grading_prompt}]
            
            content.append({"type": "text", "text": f"--- OFFICIAL ANSWER KEY (PAGE {page_num}) ---"})
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{key_page}"}
            })
                
            content.append({"type": "text", "text": f"--- {student_name} (PAGE {page_num}) ---"})
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{student_page}"}
            })

            for attempt in range(max_retries):
                try:
                    print(f"Grading {student_name} - Page {page_num} (Attempt {attempt + 1})...")
                    response = client.chat.completions.create(
                        model=model_id, 
                        messages=[{"role": "user", "content": content}]
                    )
                    
                    grade_text = response.choices[0].message.content
                    student_report += grade_text + "\n\n"
                    break 
                    
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        print(f"Rate limited on {student_name} Page {page_num}, waiting 5 seconds...")
                        time.sleep(5) 
                        continue 
                    
                    student_report += f"API ERROR DURING GRADING FOR {student_name} PAGE {page_num}:\n{str(e)}\n\n"
                    break 
        
        # ==========================================
        # THE PYTHON ACCOUNTANT (WEIGHTED MATH TALLY)
        # ==========================================
        point_matches = re.findall(r"Points:\s*([\d\.]+)\s*/\s*([\d\.]+)", student_report, re.IGNORECASE)
        
        total_earned = 0.0
        total_possible = 0.0
        
        for earned, possible in point_matches:
            total_earned += float(earned)
            total_possible += float(possible)
            
        # Fix the Python floating point decimals
        total_earned = round(total_earned, 2)
        total_possible = round(total_possible, 2)
        
        student_report += f"----------------------------------------\n"
        student_report += f" FINAL EXAM TALLY: {student_name}\n"
        student_report += f"----------------------------------------\n"
        student_report += f"Total Questions Graded: {len(point_matches)}\n"
        student_report += f"ESTIMATED SCORE: {total_earned} / {total_possible}\n"
        student_report += f"========================================\n\n"
        
        master_report += student_report
        
    return master_report