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

    # THE ANTI-LAZINESS PROMPT
    grading_prompt = """You are a strict, highly analytical AI examiner grading a single page of a student's exam.
    
    I am providing you with exactly two images:
    1. The official Answer Key (for this specific page).
    2. The Student's Exam (for this specific page).

    CRITICAL GRADING RULES:
    1. ZERO CONFIRMATION BIAS (LITERAL TRANSCRIPTION): Vision models often get "lazy" and assume a student's messy handwriting matches the answer key. YOU MUST FIGHT THIS. Before grading, look ONLY at the student's paper and literally transcribe exactly what they wrote, letter for letter, number for number. Do not autocomplete their answers.
    2. DIRECT VISUAL COMPARISON: Compare your literal transcription of the student's work to the Answer Key. If the student wrote 'a' and the key says 'b', mark it INCORRECT.
    3. IGNORE THE ANSWER TABLE: Do NOT grade the summary "Answers table" grid at the bottom of the page. ONLY grade the individual questions where they are written.
    4. ANTI-CHEATING (IGNORE RED INK): Completely ignore any red ink, human grades, or checkmarks.
    5. NO SUMMARIES: Output ONLY the grading templates. Do not output a total score, final evaluation, or any conversational text at the end of the page.
    6. POINTS EXTRACTION: The entire exam is scaled to exactly 30 points. Determine the point value for each question based on explicit labels. If a section says "(15 points)" and has 10 questions, assign exactly 1.5 points per question. If the Verdict is CORRECT, Points Earned = Points Possible. If INCORRECT, Points Earned = 0.

    --- TRAINING EXAMPLES (Edge Cases to Watch Out For) ---
    Example A: The "Don't Care" State
    If the Answer Key shows S0=X (a "don't care" state), and the student wrote S0=0 or S0=1, mark it CORRECT.

    Example B: Partial Drawing Matches
    If the Answer Key shows a full adder with a carry-out wire, and the student drew the full adder but forgot the final carry-out wire, mark it INCORRECT. Close is not enough.

    Example C: Illegible Handwriting
    If you cannot definitively read the student's handwriting, do not guess. Mark it INCORRECT and explicitly state "Handwriting illegible" in the Reasoning.
    -------------------------------------------------------

    For EVERY question found on THIS PAGE, use this exact template:
    
    * Question: [Section] - [Number]
    * Key Shows: [Exact answer/drawing from the key]
    * Student Literal Transcription: [EXACTLY what the student wrote/drew, with zero assumptions]
    * Verdict: [CORRECT / INCORRECT / PARTIAL / BLANK]
    * Points: [Earned] / [Possible]
    * Reasoning: [1 short sentence explaining the comparison.]
    
    If there are no questions on this page to grade, simply output: "No gradable questions found on this page."
    """

    master_report = f"--- BATCH GRADING ENGINE: {model_id.upper()} (STRICT TRANSCRIPTION MODE) ---\n"

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
                        print(f"Rate limited on {student_name} Page {page_num}, waiting 15 seconds...")
                        time.sleep(15) 
                        continue 
                    
                    student_report += f"API ERROR DURING GRADING FOR {student_name} PAGE {page_num}:\n{str(e)}\n\n"
                    break 
        
        # ==========================================
        # THE PYTHON ACCOUNTANT (WITH 30-POINT SCALER)
        # ==========================================
        point_matches = re.findall(r"Points:\s*([\d\.]+)\s*/\s*([\d\.]+)", student_report, re.IGNORECASE)
        
        raw_earned = 0.0
        raw_possible = 0.0
        
        for earned, possible in point_matches:
            raw_earned += float(earned)
            raw_possible += float(possible)
            
        if raw_possible > 0:
            final_scaled_score = (raw_earned / raw_possible) * 30
        else:
            final_scaled_score = 0.0
            
        final_scaled_score = round(final_scaled_score, 2)
        
        student_report += f"----------------------------------------\n"
        student_report += f" FINAL EXAM TALLY: {student_name}\n"
        student_report += f"----------------------------------------\n"
        student_report += f"Total Questions Graded: {len(point_matches)}\n"
        student_report += f"Raw AI Detection: {round(raw_earned, 2)} / {round(raw_possible, 2)}\n"
        student_report += f"FINAL SCALED SCORE: {final_scaled_score} / 30\n"
        student_report += f"========================================\n\n"
        
        master_report += student_report
        
    return master_report