# app.py
import os
from io import BytesIO

from flask import Flask, request, render_template_string
from pdf2image import convert_from_bytes
from google import genai
from google.genai import types

if "GEMINI_API_KEY" not in os.environ or not os.environ["GEMINI_API_KEY"].strip():
    raise RuntimeError("GEMINI_API_KEY not set")

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL_NAME = "gemini-2.0-flash"

app = Flask(__name__)

def pdf_to_png_bytes_list(file_storage, max_pages=3):
    data = file_storage.read()
    pages = convert_from_bytes(data)
    out = []
    for page in pages[:max_pages]:
        bio = BytesIO()
        page.convert("RGB").save(bio, format="PNG")
        out.append(bio.getvalue())
    return out

HTML = """
<!DOCTYPE html>
<html>
<head><title>AI Exam Grader</title></head>
<body>
  <h1>AI Exam Grader (Handwritten)</h1>
  <form method="POST" enctype="multipart/form-data">
    <label>Student Exam (PDF):</label><br>
    <input type="file" name="student" required><br><br>

    <label>Answer Key (PDF):</label><br>
    <input type="file" name="key" required><br><br>

    <button type="submit">Grade</button>
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

            key_imgs = pdf_to_png_bytes_list(key_file, max_pages=3)
            student_imgs = pdf_to_png_bytes_list(student_file, max_pages=3)

            contents = [
                "You are an exam grader. The exam and key are handwritten.\n"
                "The first images are the ANSWER KEY, then the STUDENT EXAM.\n"
                "Compare answers question-by-question.\n"
                "Return ONLY:\n"
                "1) Total score (e.g., 17/20)\n"
                "2) Per-question results (Correct/Wrong)\n"
                "3) Mistakes\n"
                "4) Brief feedback\n"
            ]

            for b in key_imgs:
                contents.append(types.Part.from_bytes(data=b, mime_type="image/png"))

            for b in student_imgs:
                contents.append(types.Part.from_bytes(data=b, mime_type="image/png"))

            resp = client.models.generate_content(model=MODEL_NAME, contents=contents)
            result = resp.text

        except Exception as e:
            result = f"AI ERROR: {e}"

    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    app.run( host="0.0.0.0", # nosec B104
            port=5000, 
            debug=False )



