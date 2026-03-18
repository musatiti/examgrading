from flask import Flask, request, render_template_string
import PyPDF2
import pytesseract
from pdf2image import convert_from_bytes
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
        # 1. Try reading it as a normal digital text PDF
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        
        # If it found digital text, return it!
        if text.strip():
            return text
            
        # 2. If text is empty, it must be a scanned image! Let's use OCR.
        file.seek(0) # Reset the file reader back to the beginning
        pdf_bytes = file.read()
        images = convert_from_bytes(pdf_bytes)
        
        ocr_text = ""
        for image in images:
            ocr_text += pytesseract.image_to_string(image) + "\n"
            
        return ocr_text
        
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
    app.run(host="0.0.0.0", port=5000)  # nosec B104