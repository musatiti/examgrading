import os
import time
import json
from openai import OpenAI

def grade_batch_exams(student_submissions, key_images):
    """
    Expects:
    - student_submissions: A dictionary {"Student_1.pdf": [img1, img2]}
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

    # THE ROBOTIC JSON PROMPT
    grading_prompt = """You are a robotic, highly strict grading algorithm. Your only goal is 100% accurate visual transcription and logic comparison.
    
    I am providing you with exactly two images:
    1. The official Answer Key (for this specific page).
    2. The Student's Exam (for this specific page).

    CRITICAL GRADING RULES:
    1. ZERO HALLUCINATION: Read exactly what the student wrote. Do not guess. Do not autocomplete.
    2. WHAT ANSWERS TO GRADE: read the questions CAREFULLY and know what to grade and what to not . for example this exam says in the end ofthe first question "Write your choice in the Answer table", so you basically grade the answers written in the answers table and ignore any outside the table.
    2. STRICT COMPARISON: If the student's answer differs by even one character, letter, or logic gate, it is INCORRECT.
    3. NO RED INK: Ignore human grading marks (checkmarks, red Xs, written scores).
    4. POINTS EXTRACTION: Scale the exam to 30 points. Calculate the exact point value per question based on the text,every question have the points weight written. If a section says "(15 points)" and has 10 questions, assign exactly 1.5 points. Correct = full points, Incorrect = 0 points.
    
    OUTPUT FORMAT:
    You MUST output your final response as a valid JSON object. Use EXACTLY this schema:
    {
        "questions": [
            {
                "question_id": "Q1 - 1",
                "key_literal_transcription": "b. lw $t0, 0($s0)",
                "student_literal_transcription": "c. lw $t0, 0($s0)",
                "verdict": "INCORRECT",
                "points_possible": 1.5,
                "points_earned": 0.0,
                "reasoning": "Student selected c instead of b."
            }
        ]
    }
    If there are no questions to grade on this page, return {"questions": []}.
    """

    master_report = f"--- BATCH GRADING ENGINE: {model_id.upper()} (ZERO-TEMP JSON MODE) ---\n"

    for student_name, student_images in student_submissions.items():
        student_report = f"\n\n========================================\n"
        student_report += f" GRADING REPORT: {student_name}\n"
        student_report += f"========================================\n\n"
        
        if len(student_images) != len(key_images):
            student_report += f"WARNING: {student_name} has {len(student_images)} pages, but the Answer Key has {len(key_images)}. Grading matched pages only.\n\n"

        # Initialize student totals outside the page loop
        student_raw_earned = 0.0
        student_raw_possible = 0.0
        student_total_questions = 0

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
                    
                    # THE SILVER BULLETS: Temperature 0.0 and JSON Object format
                    response = client.chat.completions.create(
                        model=model_id, 
                        response_format={ "type": "json_object" },
                        temperature=0.0,
                        messages=[{"role": "user", "content": content}]
                    )
                    
                    json_text = response.choices[0].message.content
                    
                    # Safely parse the JSON directly into Python
                    try:
                        page_data = json.loads(json_text)
                        questions = page_data.get("questions", [])
                        
                        if not questions:
                            student_report += "No gradable questions found on this page.\n\n"
                            
                        for q in questions:
                            student_report += f"* Question: {q.get('question_id')}\n"
                            student_report += f"* Key Shows: {q.get('key_literal_transcription')}\n"
                            student_report += f"* Student Wrote: {q.get('student_literal_transcription')}\n"
                            student_report += f"* Verdict: {q.get('verdict')}\n"
                            student_report += f"* Points: {q.get('points_earned')} / {q.get('points_possible')}\n"
                            student_report += f"* Reasoning: {q.get('reasoning')}\n\n"
                            
                            # Add to the running math tallies
                            student_raw_earned += float(q.get('points_earned', 0))
                            student_raw_possible += float(q.get('points_possible', 0))
                            student_total_questions += 1
                            
                    except json.JSONDecodeError:
                        student_report += "ERROR: AI failed to output valid JSON for this page.\n\n"
                        
                    break 
                    
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        print(f"Rate limited on {student_name} Page {page_num}, waiting 15 seconds...")
                        time.sleep(15) 
                        continue 
                    
                    student_report += f"API ERROR DURING GRADING FOR {student_name} PAGE {page_num}:\n{str(e)}\n\n"
                    break 
        
        # ==========================================
        # THE PERFECT SCALER (MATH DONE BY PYTHON)
        # ==========================================
        if student_raw_possible > 0:
            final_scaled_score = (student_raw_earned / student_raw_possible) * 30
        else:
            final_scaled_score = 0.0
            
        final_scaled_score = round(final_scaled_score, 2)
        
        student_report += f"----------------------------------------\n"
        student_report += f" FINAL EXAM TALLY: {student_name}\n"
        student_report += f"----------------------------------------\n"
        student_report += f"Total Questions Graded: {student_total_questions}\n"
        student_report += f"Raw AI Detection: {round(student_raw_earned, 2)} / {round(student_raw_possible, 2)}\n"
        student_report += f"FINAL SCALED SCORE: {final_scaled_score} / 30\n"
        student_report += f"========================================\n\n"
        
        master_report += student_report
        
    return master_report