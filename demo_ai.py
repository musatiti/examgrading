import os
import time
import json
from openai import OpenAI

def grade_batch_exams(student_submissions, key_images):
    """
    Expects:
    - student_submissions: A dictionary {"Student_1.pdf": [img1, img2, img3], "Student_2.pdf": [img1, img2]}
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

    # THE ROBOTIC, WHOLE-DOCUMENT PROMPT
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

    master_report = f"--- BATCH GRADING ENGINE: {model_id.upper()} (WHOLE-DOCUMENT JSON MODE) ---\n"

    for student_name, student_images in student_submissions.items():
        student_report = f"\n\n========================================\n"
        student_report += f" GRADING REPORT: {student_name}\n"
        student_report += f"========================================\n\n"
        
        # Build payload: All Key images first, then All Student images
        content = [{"type": "text", "text": grading_prompt}]
        
        content.append({"type": "text", "text": "--- ENTIRE OFFICIAL ANSWER KEY ---"})
        for img in key_images:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}})
            
        content.append({"type": "text", "text": f"--- ENTIRE STUDENT EXAM: {student_name} ---"})
        for img in student_images:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}})

        for attempt in range(max_retries):
            try:
                print(f"Grading {student_name} (All Pages at Once) - Attempt {attempt + 1}...")
                
                # THE SILVER BULLETS: JSON Mode + Temperature 0.0
                response = client.chat.completions.create(
                    model=model_id, 
                    response_format={ "type": "json_object" },
                    temperature=0.0,
                    messages=[{"role": "user", "content": content}]
                )
                
                # Parse JSON directly
                exam_data = json.loads(response.choices[0].message.content)
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
                
                # ==========================================
                # THE 30-POINT SCALER
                # ==========================================
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
                    print(f"Rate limited on {student_name}, waiting 15 seconds...")
                    time.sleep(15) 
                    continue 
                
                student_report += f"API ERROR DURING GRADING FOR {student_name}:\n{str(e)}\n\n"
                break 
                
        master_report += student_report
        
    return master_report