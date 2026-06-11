import os
import time
import json
import re
from openai import OpenAI


def grade_batch_exams(student_submissions, key_images):
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
    if not NVIDIA_API_KEY:
        return "API ERROR: NVIDIA_API_KEY environment variable not found."

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=NVIDIA_API_KEY,
        timeout=300.0,
    )

    model_id = "nvidia/nemotron-nano-12b-v2-vl"
    max_retries = 3

    grading_prompt = """You are a grading engine. Your only goal is 100% deterministic visual transcription and logic comparison.

    I am providing you with exactly two images:
    1. The official Answer Key (for this specific page).
    2. The Student's Exam (for this specific page).

    Return ONLY valid JSON using this schema:
    {
        "questions": [
            {
                "question_id": "Q1-1",
                "key_literal_transcription": "",
                "student_literal_transcription": "",
                "step_by_step_analysis": "",
                "verdict": "CORRECT",
                "points_possible": 1.0,
                "points_earned": 1.0
            }
        ]
    }
    """

    master_report = f"--- BATCH GRADING ENGINE: {model_id.upper()} ---\n"

    for student_name, student_images in student_submissions.items():
        student_report = f"\n\n========================================\n"
        student_report += f" GRADING REPORT: {student_name}\n"
        student_report += f"========================================\n\n"

        student_raw_earned = 0.0
        student_raw_possible = 0.0
        student_total_questions = 0

        for page_idx, (key_page, student_page) in enumerate(zip(key_images, student_images)):
            page_num = page_idx + 1

            content = [
                {"type": "text", "text": grading_prompt},
                {"type": "text", "text": f"ANSWER KEY PAGE {page_num}"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{key_page}"
                    }
                },
                {"type": "text", "text": f"STUDENT PAGE {page_num}"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{student_page}"
                    }
                }
            ]

            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(
                        model=model_id,
                        temperature=0.0,
                        messages=[
                            {
                                "role": "user",
                                "content": content
                            }
                        ]
                    )

                    json_text = response.choices[0].message.content

                    match = re.search(r'\{.*\}', json_text, re.DOTALL)
                    if not match:
                        raise ValueError("No JSON object found in response")

                    page_data = json.loads(match.group())
                    questions = page_data.get("questions", [])

                    for q in questions:
                        student_raw_earned += float(q.get("points_earned", 0))
                        student_raw_possible += float(q.get("points_possible", 0))
                        student_total_questions += 1

                    time.sleep(2)
                    break

                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(10)
                        continue

                    student_report += f"ERROR PAGE {page_num}: {e}\n"

        final_scaled_score = (
            (student_raw_earned / student_raw_possible) * 30
            if student_raw_possible > 0
            else 0
        )

        student_report += f"\nFINAL SCORE: {round(final_scaled_score, 2)} / 30\n"
        master_report += student_report

    return master_report


def extract_student_info(student_image_b64):
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

    if not NVIDIA_API_KEY:
        return None, None

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=NVIDIA_API_KEY,
        timeout=60.0,
    )

    try:
        response = client.chat.completions.create(
            model="nvidia/nemotron-nano-12b-v2-vl",
            temperature=0.0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """
Extract the student ID and full name.

Return ONLY:
{
  "student_id": "",
  "student_name": ""
}
"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{student_image_b64}"
                            }
                        }
                    ]
                }
            ]
        )

        text = response.choices[0].message.content

        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            return None, None

        data = json.loads(match.group())

        return data.get("student_id"), data.get("student_name")

    except Exception:
        return None, None