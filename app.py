from flask import Flask, request, render_template_string
from pdf2image import convert_from_bytes
import pytesseract
import re
from difflib import SequenceMatcher

app = Flask(__name__)

def pdf_to_text(file):
    pages = convert_from_bytes(file.read())
    text = ""
    for page in pages:
        text += pytesseract.image_to_string(page) + "\n"
    return text.strip() or "NO TEXT DETECTED"

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def grade_exam(key_text, student_text):
    key_lines = [line.strip() for line in key_text.split("\n") if line.strip()]
    student_lines = [line.strip() for line in student_text.split("\n") if line.strip()]

    total_questions = min(len(key_lines), len(student_lines))
    if total_questions == 0:
        return "Could not detect answers. OCR failed."

    correct = 0
    report = []

    for i in range(total_questions):
        key_ans = key_lines[i]
        student_ans = student_lines[i]

        score = similarity(key_ans.lower(), student_ans.lower())
        status = "✅ Correct" if score >= 0.75 else "❌ Wrong"

        if score >= 0.75:
            correct += 1

        report.append(
            f"Q{i+1}:\n"
            f"Key: {key_ans}\n"
            f"Student: {student_ans}\n"
            f"Match: {score*100:.1f}% → {status}\n"
        )

    final_score = f"Final Score: {correct}/{total_questions}\n\n"
    feedback = "Feedback:\n"
    if correct == total_questions:
        feedback += "- Excellent work ✅\n"
    elif correct >= total_questions * 0.7:
        feedback += "- Good work, revise mistakes ⚠️\n"
    else:
        feedback += "- Needs improvement, study the key answers more ❗\n"

    return final_score + "\n".join(report) + "\n" + feedback

HTML = """
<!DOCTYPE html>
<html>
<head><title>Exam Grader</title></head>
<body>
    <h1>Offline Exam Grader (No API)</h1>

    <form method="POST" enctype="multipart/form-data">
        <label>Student Exam (PDF):</label><br>
        <input type="file" name="student" required><br><br>

        <label>Answer Key (PDF):</label><br>
        <input type="file" name="key" required><br><br>

        <button type="submit">Grade</button>
    </form>

    {% if result %}
        <h2>Results</h2>
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

            result = grade_exam(key_text, student_text)

        except Exception as e:
            result = f"Error: {e}"

    return render_template_string(HTML, result=result)


if __name__ == "__main__":
    app.run( host="0.0.0.0", # nosec B104
            port=5000, 
            debug=False )



