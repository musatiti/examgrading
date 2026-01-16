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

def demo_output():
    q1_student = "a c d a b d a c a d"
    q1_key = "b d d a b a a c a d"
    q1_score = "10.5 / 15"
    q1_correct = "7 / 10"
    q1_wrong = "3 / 10"

    q2_student = [
        "S4..S0: 0 1 0 1 1",
        "A0/B0: 1 / 0",
        "A1/B1: 0 / 1",
        "A2/B2: 1 / 1",
    ]
    q2_key = [
        "S4..S0: 0 1 1 0 1",
        "A0/B0: 1 / 0",
        "A1/B1: 1 / 1",
        "A2/B2: 1 / 0",
    ]
    q2_score = "6 / 10"
    q2_correct = "3 / 4"
    q2_wrong = "1 / 4"

    lines = []
    lines.append("Demo Mode (Simulated AI Result)\n")
    lines.append("Total Score: 16.5 / 25\n")

    lines.append("Question 1 :")
    lines.append(f" Student: {q1_student}")
    lines.append(f" Key: {q1_key}\n")
    lines.append(f"- Score: {q1_score}")
    lines.append(f"- Correct Answers: {q1_correct}")
    lines.append(f"- Wrong Answers: {q1_wrong}\n")

    lines.append("Question 2 :")
    lines.append(" Student Answers:")
    for s in q2_student:
        lines.append(f"  - {s}")
    lines.append(" Key Answers:")
    for k in q2_key:
        lines.append(f"  - {k}")
    lines.append("")
    lines.append(f"- Score: {q2_score}")
    lines.append(f"- Correct Answers: {q2_correct}")
    lines.append(f"- Wrong Answers: {q2_wrong}\n")

    lines.append("Feedback:")
    lines.append("- Good work overall.")
    lines.append("- Review Q1 mistakes (Q1, Q2, Q6).")
    lines.append("- For Q2, double-check your table bits and final values.")

    return "\n".join(lines)

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
                result = demo_output()

        except Exception as e:
            result = f"Error: {e}"

    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    app.run( host="0.0.0.0", # nosec B104
            port=5000, 
            debug=False )