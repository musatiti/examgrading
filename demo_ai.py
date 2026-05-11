import os
import time
import json
import google.generativeai as genai

def grade_batch_exams(student_submissions, key_images):
    """
    Expects:
    - student_submissions: A dictionary {"Student_1.pdf": [img1, img2, img3]}
    - key_images: A list of base64 images for the Answer Key
    """
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return "API ERROR: GEMINI_API_KEY environment variable not found."

    # Wire directly to Google's official servers
    genai.configure(api_key=api_key)
    
    # Locking in the official Gemini 2.0 Flash model
    model_id = "models/gemini-2.0-flash"
    max_retries = 3

    # Lock Gemini into strict JSON mode with zero creativity
    model = genai.GenerativeModel(
        model_name=model_id,
        generation_config={
            "temperature": 0.0,
            "response_mime_type": "application/json"
        }
    )

    grading_prompt = """You are a robotic, highly strict grading algorithm. Your goal is 100% accurate visual transcription and logic comparison.
    
    I am providing you with two complete documents:
    1. The ENTIRE official Answer Key.
    2. The ENTIRE Student's Exam.

    CRITICAL GRADING RULES:
    1. FIND THE ANSWERS: The student's exam may have cover pages, blank pages, or be out of order. Scan the entire document to match the student's answers to the correct questions on the Answer Key.
    2. ZERO CONFIRMATION BIAS: Read exactly what the student wrote. Do not guess. If the key says 'a' and the student wrote 'c', transcribe it as 'c' and mark it INCORRECT.
    3. IGNORE THE ANSWER TABLE: Do NOT grade the summary "Answers table" grid. ONLY grade the individual questions where they are written.
    4. ANTI-CHEATING: Completely ignore any red ink, human grades, or checkmarks.
    5. POINTS EXTRACTION: Calculate the exact point value per question based on the text. If a section says "(15 points)" and has 10 questions, assign exactly 1.5 points. Correct = full points, Incorrect = 0 points.
    
    OUTPUT FORMAT:
    You MUST output your final response as a valid JSON object representing the entire exam. Use EXACTLY this schema:
    {
        "student_total_earned": 15.0,
        "student_total_possible": 30.0,
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
    """

    master_report = f"--- BATCH GRADING ENGINE: GEMINI 2.0 FLASH (WHOLE-DOCUMENT JSON MODE) ---\n"

    for student_name, student_images in student_submissions.items():
        student_report = f"\n\n========================================\n"
        student_report += f" GRADING REPORT: {student_name}\n"
        student_report += f"========================================\n\n"
        
        # Build the native Google Payload (Uncompressed, High-Res Images)
        content = [grading_prompt, "--- ENTIRE OFFICIAL ANSWER KEY ---"]
        for img in key_images:
            content.append({"mime_type": "image/jpeg", "data": img})
            
        content.append(f"--- ENTIRE STUDENT EXAM: {student_name} ---")
        for img in student_images:
            content.append({"mime_type": "image/jpeg", "data": img})

        for attempt in range(max_retries):
            try:
                print(f"Grading {student_name} (All Pages at Once) - Attempt {attempt + 1}...")
                
                # Direct API Call to Google
                response = model.generate_content(content)
                
                # Parse the JSON
                exam_data = json.loads(response.text)
                questions = exam_data.get("questions", [])
                
                if not questions:
                    student_report += "ERROR: No gradable questions found in this document.\n\n"
                    
                for q in questions:
                    student_report += f"* Question: {q.get('question_id')}\n"
                    student_report += f"* Key Shows: {q.get('key_literal_transcription')}\n"
                    student_report += f"* Student Wrote: {q.get('student_literal_transcription')}\n"
                    student_report += f"* Verdict: {q.get('verdict')}\n"
                    student_report += f"* Points: {q.get('points_earned')} / {q.get('points_possible')}\n"
                    student_report += f"* Reasoning: {q.get('reasoning')}\n\n"
                
                # THE 30-POINT SCALER
                raw_earned = float(exam_data.get("student_total_earned", 0))
                raw_possible = float(exam_data.get("student_total_possible", 0))
                
                if raw_possible > 0:
                    final_scaled_score = (raw_earned / raw_possible) * 30
                else:
                    final_scaled_score = 0.0
                    
                final_scaled_score = round(final_scaled_score, 2)
                
                student_report += f"----------------------------------------\n"
                student_report += f" FINAL EXAM TALLY: {student_name}\n"
                student_report += f"----------------------------------------\n"
                student_report += f"Total Questions Graded: {len(questions)}\n"
                student_report += f"Raw AI Detection: {round(raw_earned, 2)} / {round(raw_possible, 2)}\n"
                student_report += f"FINAL SCALED SCORE: {final_scaled_score} / 30\n"
                student_report += f"========================================\n\n"
                
                break 
                
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    print(f"Rate limited on {student_name}, waiting 10 seconds...")
                    time.sleep(10) 
                    continue 
                
                student_report += f"API ERROR DURING GRADING FOR {student_name}:\n{str(e)}\n\n"
                break 
                
        master_report += student_report
        
    return master_report