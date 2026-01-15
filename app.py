import os
import base64
from io import BytesIO

from flask import Flask, request, render_template_string
from pdf2image import convert_from_bytes
from openai import OpenAI

if "OPENAI_API_KEY" not in os.environ or not os.environ["OPENAI_API_KEY"].strip():
    raise RuntimeError("OPENAI_API_KEY not set")

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

app = Flask(__name__)

def pdf_to_data_urls(file_storage, max_pages=3, max_width=1100):
    data = file_storage.read()
    pages = convert_from_bytes(data)
    urls = []
    for page in pages[:max_pages]:
        img = page.convert("RGB")
        if img.width > max_width:
            new_h = int(img.height * (max_width / img.width))
            img = img.resize((max_width, new_h))

        bio = BytesIO()
        img.save(bio, format="PNG", optimize=True)
        b64 = base64.b64encode(bio.getvalue()).decode("utf-8")
        urls.append(f"data:image/png;base64,{b64}")
    return urls

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

            key_pages = pdf_to_data_urls(key_file, max_pages=3)
            student_pages = pdf_to_data_urls(student_file, max_pages=3)

            input_items = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are an exam grader.\n"
                                "The first set of images are the ANSWER KEY (handwritten).\n"
                                "The second set of images are the STUDENT EXAM (handwritten).\n"
                                "Compare question-by-question.\n\n"
                                "Return ONLY:\n"
                                "1) Total score (e.g., 17/20)\n"
                                "2) Per-question result table (Q#, Correct/Wrong, points)\n"
                                "3) Mistakes\n"
                                "4) Brief feedback\n"
                            ),
                        }
                    ],
                }
            ]

            for u in key_pages:
                input_items[0]["content"].append({"type": "input_image", "image_url": u})

            for u in student_pages:
                input_items[0]["content"].append({"type": "input_image", "image_url": u})

            resp = client.responses.create(
                model="gpt-4o",
                input=input_items,
            )

            result = resp.output_text

        except Exception as e:
            result = f"AI ERROR: {e}"

    return render_template_string(HTML, result=result)


if __name__ == "__main__":
    app.run( host="0.0.0.0", # nosec B104
            port=5000, 
            debug=False )



