import os
from openai import OpenAI

def grade_demo(student_images, key_images):
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=300.0, 
    )

 
    content_array = [
        {
            "type": "text", 
            "text": "You are an expert examiner. Grade the student's work based on the provided answer key. Analyze both text and drawings carefully. \n\nThe first set of images below is the ANSWER KEY. The second set is the STUDENT WORK."
        }
    ]
    
   
    content_array.append({"type": "text", "text": "--- START OF ANSWER KEY ---"})
    for b64_img in key_images:
        content_array.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        })
        
  
    content_array.append({"type": "text", "text": "--- START OF STUDENT WORK ---"})
    for b64_img in student_images:
        content_array.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        })


    response = client.chat.completions.create(
        model="google/gemini-2.0-flash-lite-preview-02-05:free",
        messages=[{"role": "user", "content": content_array}]
    )
    
    final_answer = response.choices[0].message.content if response.choices[0].message.content else "No response generated."
        
    return f"FINAL GRADE & FEEDBACK:\n{final_answer}"