import os
import base64
import requests
from flask import Flask, request, render_template_string
from pdf2image import convert_from_bytes

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1/models/"
    "gemini-1.5-flash:generateContent?key=" + GEMINI_API_KEY
)

app = Flask(__name__)

def pdf_to_images_base64(file):
    pages = convert_from_bytes(file.read())
    images = []
    for page in pages:
        buffer = page.convert("RGB")
        from io import BytesIO
        bio = BytesIO()
        buffer.save(bio, format="PNG")
        images.append(base64.b64encode(bio.getvalue()).decode())
    return images

HTML = """
<!DOCTYPE html>
<html>
<body>
<h1>AI Exam Grader (Handwritten)</h1>
<form method="POST" enctype="multipart/form-data">
Student Exam: <input type="file" name="student" required><br><br>
Answer Key: <input type="file" name="key" required><br><br>
<button type="submit">Grade</button>
</form>

{% if result %}
<h2>Result</h2>
<pre>{{ result }}</pre>
{% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    result = None

    if request.method == "POST":
        student_imgs = pdf_to_images_base64(request.files["student"])
        key_imgs = pdf_to_images_base64(request.files["key"])

        contents = [
            {
                "role": "user",
                "parts": [
                    {"text": "You are an exam grader. Compare the student's handwritten answers with the handwritten answer key and give a grade with feedback."}
                ]
            }
        ]

        for img in key_imgs:
            contents[0]["parts"].append({
                "inline_data": {"mime_type": "image/png", "data": img}
            })

        for img in student_imgs:
            contents[0]["parts"].append({
                "inline_data": {"mime_type": "image/png", "data": img}
            })

        response = requests.post(
            GEMINI_URL,
            json={"contents": contents},
            timeout=60
        )

        result = response.json()

    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0", # nosec B104
        port=5000,
        debug=False
    )


