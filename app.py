from flask import Flask, request, render_template_string
from demo_ai import grade_demo

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>AI Exam Grader</title>
  <style>
    body { font-family: Arial; margin: 30px; }
    button { padding: 10px 15px; }
    pre { background: #f5f5f5; padding: 15px; border-radius: 8px; }
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

@app.route("/", methods=["GET", "POST"])
def index():
    result = None

    if request.method == "POST":
        student_file = request.files.get("student")
        key_file = request.files.get("key")

        if not student_file or not key_file:
            result = "Error: Missing files."
        else:
            result = grade_demo()

    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    app.run( host="0.0.0.0", # nosec B104
            port=5000, 
            debug=False )
    