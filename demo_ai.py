import os
import time
import json
import re
from openai import OpenAI


def grade_batch_exams(student_submissions, key_images):
    """
    Expects:
    - student_submissions: A dictionary {"Student_1.pdf": [img1, img2, img3]}
    - key_images: A list of base64 images for the Answer Key
    """
    
    # 1. FETCH THE TOKEN
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    if not GITHUB_TOKEN:
        return "API ERROR: GITHUB_TOKEN environment variable not found."

    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=GITHUB_TOKEN,
        timeout=300.0, 
    )

    model_id = "gpt-4o"
    max_retries = 3

    # التعليمات الموجهة للذكاء الاصطناعي
    grading_prompt = """You are a grading engine. Your only goal is 100% deterministic visual transcription and logic comparison. 
    
    I am providing you with exactly two images:
    1. The official Answer Key (for this specific page).
    2. The Student's Exam (for this specific page).

    CRITICAL GRADING RULES:
    1. ZERO HALLUCINATION (LITERAL TEXT): Read exactly what the student wrote. Do not guess or infer. If the key says 'a' and the student's 'a' looks like a 'c', transcribe it as 'c' and mark it INCORRECT.
    2. VISUAL DIAGRAM MATCHING (CIRCUITS/DRAWINGS): For questions requiring a drawn logic circuit, DO NOT just describe the image. You must visually trace the topology. The student's drawing MUST have the exact same logic gates (AND, OR, XOR), wire connections, and input/output labels as the key. If a wire goes to the wrong gate, it is INCORRECT.
    3. THE ANSWER TABLE IS THE SOURCE OF TRUTH: If the student filled out a summary "Answers Table" for multiple-choice questions, use the letters written in that table as their official answers. If the table is empty or missing, fall back to checking the circled answers next to the questions.
    4. NO NEWLINES IN EXTRACTION: Never use newline characters (\n) inside question IDs or transcriptions. Format IDs cleanly (e.g., "Q1-1", "Q2-4").
    5. STRICT POINT DEFAULT: Look for explicit point labels (e.g., "(15 points)" for 10 questions = 1.5 points each). IF AND ONLY IF you cannot find an explicit point label, default to EXACTLY 1.0 point per question. NEVER invent random decimals like 2.14.
    6. NO RED INK: Ignore human checkmarks, red Xs, or written scores left by human graders.
    
    OUTPUT FORMAT:
    You MUST output your final response as a valid JSON object. You MUST generate the "step_by_step_analysis" BEFORE the "verdict" to ensure you reason through the logic first. Use EXACTLY this schema:
    {
        "questions": [
            {
                "question_id": "Q1-1",
                "key_literal_transcription": "b. lw $t0, 0($s0)",
                "student_literal_transcription": "c",
                "step_by_step_analysis": "The key requires option 'b'. The student wrote 'c' in the answer table. The options do not match.",
                "verdict": "INCORRECT",
                "points_possible": 1.5,
                "points_earned": 0.0
            }
        ]
    }
    If there are no questions to grade on this page, return {"questions": []}.
    """

    master_report = f"--- BATCH GRADING ENGINE: {model_id.upper()} (PAGE-BY-PAGE JSON MODE) ---\n"

    for student_name, student_images in student_submissions.items():
        student_report = f"\n\n========================================\n"
        student_report += f" GRADING REPORT: {student_name}\n"
        student_report += f"========================================\n\n"
        
        if len(student_images) != len(key_images):
            student_report += f"WARNING: {student_name} has {len(student_images)} pages, but the Answer Key has {len(key_images)}. Grading matched pages only to avoid misalignment.\n\n"

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
                    
                    response = client.chat.completions.create(
                        model=model_id, 
                        response_format={ "type": "json_object" },
                        temperature=0.0, 
                        messages=[{"role": "user", "content": content}]
                    )
                    
                    json_text = response.choices[0].message.content
                    
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
                            student_report += f"* Reasoning: {q.get('step_by_step_analysis')}\n\n"
                            
                            student_raw_earned += float(q.get('points_earned', 0))
                            student_raw_possible += float(q.get('points_possible', 0))
                            student_total_questions += 1
                            
                    except json.JSONDecodeError:
                        student_report += "ERROR: AI failed to output valid JSON for this page.\n\n"
                        
                    print("Page graded successfully. Sleeping 15 seconds to cool down Azure limits...")
                    time.sleep(15)
                    break 
                    
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        print(f"Rate limited on {student_name} Page {page_num}, waiting 30 seconds...")
                        time.sleep(30) 
                        continue 
                    
                    student_report += f"API ERROR DURING GRADING FOR {student_name} PAGE {page_num}:\n{str(e)}\n\n"
                    break 
        
        # العلامة من 30
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


def extract_student_info(student_image_b64):
    """Reads student ID and name from the first page of the exam."""
    
    # 2. FETCH THE TOKEN HERE AS WELL
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    if not GITHUB_TOKEN:
        print("API ERROR: GITHUB_TOKEN environment variable not found.")
        return None, None

    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=GITHUB_TOKEN,
        timeout=60.0,
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            temperature=0.0,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Look at this exam paper and extract the student's university ID number and full name.
                        Return ONLY this JSON:
                        {
                            "student_id": "the university ID number you see",
                            "student_name": "the full name you see"
                        }
                        If you cannot find the ID or name, return null for that field."""
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{student_image_b64}"}
                    }
                ]
            }]
        )

        data = json.loads(response.choices[0].message.content)
        return data.get("student_id"), data.get("student_name")

    except Exception as e:
        print(f"extract_student_info error: {e}")
        return None, None