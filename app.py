from flask import Flask, request, render_template_string
import google.generativeai as genai
import pytesseract
from pdf2image import convert_from_bytes


genai.configure(api_key="AIzaSyDY8AoqoEx5HN62Nz67MRodL3V9BNsDsno")


models = list(genai.list_models())
model_name = None
for m in models:
    if "generateContent" in getattr(m, "supported_generation_methods", []):
        model_name = m.name
        break

if not model_name:
    raise RuntimeError("No Gemini model available for generate_content")

model = genai.GenerativeModel(model_name)

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
            student_file = request.files.get("student")
            key_file = request.files.get("key")
            student_text = pdf_to_text(student_file)
            key_text = pdf_to_text(key_file)

            prompt = f"""
You are an exam grader.
Grade strictly based on the provided answer key.

ANSWER KEY:
{key_text}

STUDENT EXAM:
{student_text}
"""
            response = model.generate_content(prompt)
            result = getattr(response, "text", str(response))
        except Exception as e:
            result = f"AI Error: {e}"

    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0", # nosec B104
        port=5000,
        debug=False
    )


