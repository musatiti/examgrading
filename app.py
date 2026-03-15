from flask import Flask, request, render_template_string
import PyPDF2
from demo_ai import grade_demo

app = Flask(__name__)

# The missing HTML string!
HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>AI Exam Grader</title>
  <style>
    body { font-family: Arial; margin: 30px; }
    button { padding: 10px 15px; }
    pre { background: #f5f5f5; padding: 15px; border-radius: 8px; white-space: pre-wrap; }
  </style>
</head>
<body>
  <h1>AI Exam Grader</h1>

  <form method="POST" enctype="multipart/form-data">
    <label>Student Exam (PDF):</label><br>
    <input type="file" name="student" required><br><br>

    <label>Answer Key (PDF):</label><br>
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

def extract_text_from_pdf(file):
    try:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        student_file = request.files.get("student")
        key_file = request.files.get("key")

        if not student_file or not key_file:
            result = "Error: Missing files."
        else:
            # Extract text
            student_text = extract_text_from_pdf(student_file)
            key_text = extract_text_from_pdf(key_file)
            
            # Send to OpenRouter AI
            result = grade_demo(student_text, key_text)

    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)