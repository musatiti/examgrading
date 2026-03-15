from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="OPENROUTER_API_KEY",
)

def grade_demo(student_text, key_text):
    # Construct the prompt using the file contents
    prompt = f"""
    You are an expert examiner. 
    Compare the Student's Work against the Answer Key provided.
    
    ANSWER KEY:
    {key_text}
    
    STUDENT WORK:
    {student_text}
    
    Provide a final grade and detailed feedback.
    """

    response = client.chat.completions.create(
        model="openrouter/hunter-alpha",
        messages=[{"role": "user", "content": prompt}],
        extra_body={"reasoning": {"enabled": True}}
    )
    
    # Return the content (and you can also return reasoning if you want)
    return response.choices[0].message.content