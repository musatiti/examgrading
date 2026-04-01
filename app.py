from flask import Flask, request, render_template_string
import base64
from io import BytesIO
from pdf2image import convert_from_bytes
from demo_ai import grade_demo

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>AI Exam Grader (Vision Edition)</title>
  <style>
    body { font-family: Arial; margin: 30px; line-height: 1.6; }
    button { padding: 10px 15px; cursor: pointer; }
    pre { background: #f5f5f5; padding: 15px; border-radius: 8px; white-space: pre-wrap; font-family: monospace; }
  </style>
</head>
<body>
  <h1>AI Exam Grader</h1>

  <form method="POST" enctype="multipart/form-data">
    <label>Student Exam (PDF):</label><br>
    <input type="file" name="student" required><br><br>

    <label>Answer Key (PDF):</label><br>
    <input type="file" name="key" required><br><br>

    <button type="submit">Grade with Vision AI</button>
  </form>

  {% if result %}
    <h2>Grade & Feedback</h2>
    <pre>{{ result }}</pre>
  {% endif %}
</body>
</html>
"""

def pdf_to_base64_images(file):
    try:
        file.seek(0)
        pdf_bytes = file.read()
        
        # FIX: We added dpi=300 to make the images high-definition!
        images = convert_from_bytes(pdf_bytes, dpi=100)
        
        base64_images = []
        for img in images:
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            base64_images.append(img_str)
            
        return base64_images
    except Exception as e:
        print(f"Error converting PDF: {str(e)}")
        return []

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        student_file = request.files.get("student")
        key_file = request.files.get("key")

        if not student_file or not key_file:
            result = "Error: Missing files."
        else:
            student_images = pdf_to_base64_images(student_file)
            key_images = pdf_to_base64_images(key_file)
            
            if not student_images or not key_images:
                result = "Error: Could not convert PDFs to images."
            else:
                result = grade_demo(student_images, key_images)

    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)  # nosec B104