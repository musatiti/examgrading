from flask import Flask, request, render_template_string

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

def demo_ai_grade_output():
    return """Demo Mode (Simulated AI Result)

Total Score: 10.5 / 15

Question 1 (MCQ):
- Score: 10.5 / 15
- Correct Answers: 7 / 10
- Wrong Answers: 3 / 10

Mistakes:
- Q1: Incorrect choice
- Q2: Incorrect choice
- Q6: Incorrect choice

Feedback:
- Good work overall.
- Review the incorrect questions and make sure you understand why the correct choice is correct.
- Your answers are consistent and clearly written.
"""

@app.route("/", methods=["GET", "POST"])
def index():
    result = None

    if request.method == "POST":
        try:
            student_file = request.files.get("student")
            key_file = request.files.get("key")

            if not student_file or not key_file:
                result = "Error: Missing files."
            else:
                result = demo_ai_grade_output()

        except Exception as e:
            result = f"Error: {e}"

    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    app.run( host="0.0.0.0", # nosec B104
            port=5000, 
            debug=False )