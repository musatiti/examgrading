import base64
import fitz  # PyMuPDF
from flask import Flask, render_template, request
from demo_ai import grade_batch_exams

app = Flask(__name__)

HTML="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Exam Grader</title>
    <style>
        body { font-family: sans-serif; margin: 40px; }
        form { margin-bottom: 20px; padding: 20px; border: 1px solid #ccc; max-width: 600px; }
        div { margin-bottom: 15px; }
        label { font-weight: bold; display: block; margin-bottom: 5px; }
        pre { background: #f4f4f4; padding: 15px; white-space: pre-wrap; word-wrap: break-word; }
    </style>
</head>
<body>
    <h1>AI Exam Grader</h1>
    <form method="POST" enctype="multipart/form-data">
        <div>
            <label>Upload Answer Key (Image or PDF):</label>
            <input type="file" name="key_files" accept="image/*, application/pdf" multiple required>
        </div>
        <div>
            <label>Upload Student Exams (Images or PDFs):</label>
            <input type="file" name="student_files" accept="image/*, application/pdf" multiple required>
        </div>
        <button type="submit">Grade Exams</button>
    </form>

    {% if result %}
        <h2>Grading Results:</h2>
        <pre>{{ result }}</pre>
    {% endif %}
</body>
</html>

"""

def pdf_to_base64_images(file_storage):
    """Takes an uploaded PDF file, slices it into pages, and returns base64 images."""
    base64_images = []
    pdf_document = fitz.open(stream=file_storage.read(), filetype="pdf")
    
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        # Zoom in 2x for high-resolution images so the AI can read small handwriting
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) 
        img_bytes = pix.tobytes("jpeg")
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        base64_images.append(b64)
        
    pdf_document.close()
    return base64_images

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Process Answer Key files
        key_files = request.files.getlist("key_files") 
        key_images = []
        for file in key_files:
            if file.filename:
                if file.filename.lower().endswith('.pdf'):
                    key_images.extend(pdf_to_base64_images(file))
                else:
                    key_images.append(base64.b64encode(file.read()).decode('utf-8'))

        # Process Student Exam files into a dictionary
        student_files = request.files.getlist("student_files") 
        student_submissions = {}
        
        for file in student_files:
            if file.filename:
                if file.filename.lower().endswith('.pdf'):
                    student_submissions[file.filename] = pdf_to_base64_images(file)
                else:
                    student_submissions[file.filename] = [base64.b64encode(file.read()).decode('utf-8')]

        # Run the grading loop
        result = grade_batch_exams(student_submissions, key_images)
        return render_template("index.html", result=result)

    return render_template("index.html", result=None)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)