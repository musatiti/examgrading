import os
from flask import Flask, request, render_template_string
import google.generativeai as genai
import pytesseract
from pdf2image import convert_from_bytes

if "GEMINI_API_KEY" not in os.environ:
    raise RuntimeError("GEMINI_API_KEY not set")

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")


app = Flask(__name__)

def pdf_to_text(file):
    pages = convert_from_bytes(file.read())
    text = ""
    for page in pages:
        text += pytesseract.image_to_string(page)
    return text.strip() or "NO TEXT DETECTED"

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Exam Grader</title>
</head>
<body>
    <h1>AI Exam Grader</h1>
    <form method="POST" enctype="multipart/form-data">
        <label>Student Exam (PDF / Image):</label><br>
        <input type="file" name="student" required><br><br>

        <label>Answer Key (PDF / Image):</label><br>
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
            student_file = request.files["student"]
            key_file = request.files["key"]

            student_text = pdf_to_text(student_file)
            key_text = pdf_to_text(key_file)

            prompt = f"""
You are an exam grader.

Compare the STUDENT ANSWERS with the ANSWER KEY.
The exams are handwritten and converted using OCR.

ANSWER KEY:
{key_text}

STUDENT ANSWERS:
{student_text}

Return:
- Score
- Mistakes
- Brief feedback
"""

            response = model.generate_content(prompt)
            result = response.text

        except Exception as e:
            result = f"AI ERROR: {e}"

    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0", # nosec B104
        port=5000,
        debug=False
    )


