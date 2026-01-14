import os
from flask import Flask, request, render_template_string
from pypdf import PdfReader
import google.generativeai as genai

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

app = Flask(__name__)

def read_file(file):
    if file and file.filename.lower().endswith(".pdf"):
        reader = PdfReader(file.stream)
        text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        return "\n".join(text) or "EMPTY PDF"
    return file.read().decode("utf-8", errors="ignore")

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
            student_file = request.files.get("student")
            key_file = request.files.get("key")

            student_text = read_file(student_file)
            key_text = read_file(key_file)

            response = model.generate_content(f"""
You are an exam grader.
Grade strictly based on the provided answer key.

ANSWER KEY:
{key_text}

STUDENT EXAM:
{student_text}
""")

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


