import os
import time
from openai import OpenAI

def grade_demo(student_images, key_images):
    # Grab the key securely from the environment
    api_key = os.getenv("MOONSHOT_API_KEY")

    if not api_key:
        return "API ERROR: MOONSHOT_API_KEY is not set in the environment."

    # Initialize the Kimi client
    client = OpenAI(
        base_url="https://api.moonshot.ai/v1",
        api_key=api_key,
        timeout=300.0,
    )

    # Kimi model
    model_id = "kimi-k2.5"
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
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64_img}"
            }
        })

    extracted_key_text = ""

    # Retry Loop for Phase 1
    for attempt in range(max_retries):
        try:
            print(f"Extracting Answer Key (Attempt {attempt + 1})...")
            key_response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Kimi, a precise exam analysis assistant."
                    },
                    {
                        "role": "user",
                        "content": key_content
                    }
                ]
            )
            extracted_key_text = key_response.choices[0].message.content or ""
            break

        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(5)
                continue
            return f"API ERROR DURING KEY EXTRACTION:\n{str(e)}\n\nPlease try again later."

    # ==========================================
    # PHASE 2: GRADE THE STUDENT EXAM ONLY
    # ==========================================
    grading_prompt = f"""You are a strict, literal AI examiner.

Here is the official Answer Key text:
---
{extracted_key_text}
---

CRITICAL GRADING RULES:
1. STRICT SPATIAL AWARENESS: Look at the attached Student Exam images. YOU MUST ONLY GRADE WHAT IS WRITTEN INSIDE OFFICIAL ANSWER BOXES/TABLES. Completely ignore scratchpad work, margin notes, crossed-out text, or circles drawn on the question text itself.
2. MANDATORY COMPARISON: You are forbidden from giving a verdict without explicitly printing the Key's answer and the Student's answer right next to each other first. If they do not match exactly, you MUST mark it INCORRECT.
3. ANTI-HALLUCINATION: DO NOT guess. If the official answer box is empty or illegible, mark it BLANK (0 points) even if there is work elsewhere on the page.
4. POINT WEIGHTS: Use the point values from the key. If a section is worth 15 points and has 10 questions, each is 1.5 points.

YOU MUST USE THIS EXACT TEMPLATE FOR EVERY SINGLE QUESTION. DO NOT DEVIATE:

* Question: [Section] - [Number]
* Key Says: [Exactly what Phase 1 extracted]
* Student Wrote: [Exactly what is in the box]
* Verdict: [CORRECT / INCORRECT / PARTIAL / BLANK]
* Points: [X] / [Y]
* Reasoning: [Explain why they match or fail based strictly on the visual evidence]

End with:
FINAL SCORE: [Total Earned] / [Total Possible]
"""

    student_content = [{"type": "text", "text": grading_prompt}]
    for b64_img in student_images:
        student_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64_img}"
            }
        })

    # Retry Loop for Phase 2
    for attempt in range(max_retries):
        try:
            print(f"Grading Student Exam (Attempt {attempt + 1})...")
            final_response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Kimi, a strict and accurate exam grading assistant."
                    },
                    {
                        "role": "user",
                        "content": student_content
                    }
                ]
            )

            final_grade = final_response.choices[0].message.content or "No response generated."
            return (
                f"PHASE 1 (EXTRACTED KEY):\n{extracted_key_text}\n\n"
                f"=========================\n\n"
                f"PHASE 2 (FINAL GRADE & FEEDBACK):\n{final_grade}"
            )

        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(5)
                continue
            return f"API ERROR DURING GRADING:\n{str(e)}\n\nPlease try again later."