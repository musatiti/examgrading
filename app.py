import os
from flask import Flask, request, render_template_string
import google.generativeai as genai
import pytesseract
from pdf2image import convert_from_bytes

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.get_model("text-bison-001")

app = Flask(__name__)

def pdf_to_text(file):
    pages = convert_from_bytes(file.read())
    text = ""
    for page in pages:
        text += pytesseract.image_to_string(page)
    return text or "EMPTY PDF"

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Exam Grader</title>
</head>
<body>
    <h1>AI Exam Grader</h1>
    <form method="POST" enctype="multipart/form-data">
        <label>Student Exam:</label><br>
        <input type="file" name="student" required><br><br>
        <label>Answer Key:</label><br>
        <input type="file" name="key" required><br><br>
        <button type="submit">Grade with AI</button>
    </form>
    {% if result %}
        <h2>Grade & Feedback</h2>
        <pre>{{ result }}</pre>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        try:
            student_text = pdf_to_text(request.files["student"])
            key_text = pdf_to_text(request.files["key"])

            prompt = f"""
You are an exam grader.
Grade strictly based on the provided answer key.

ANSWER KEY:
{key_text}

STUDENT EXAM:
{student_text}
"""
            response = model.generate_text(prompt)  
            result = response.text
        except Exception as e:
            result = f"AI Error: {e}"

    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0", # nosec B104
        port=5000,
        debug=False
    )


