import os
from flask import Flask, request, render_template_string
from openai import OpenAI
from pypdf import PdfReader

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def read_file(file):
    if file.filename.endswith(".pdf"):
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    return file.read().decode("utf-8")

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
        <input type="file" name="student"><br><br>

        <label>Answer Key:</label><br>
        <input type="file" name="key"><br><br>

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

        if student_file and key_file:
            student_text = read_file(student_file)
            key_text = read_file(key_file)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an exam grader. Grade strictly based on the provided answer key."
                    },
                    {
                        "role": "user",
                        "content": f"ANSWER KEY:\n{key_text}\n\nSTUDENT EXAM:\n{student_text}"
                    }
                ]
            )

            result = response.choices[0].message.content

    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0", # nosec B104
        port=5000,
        debug=False
    )


