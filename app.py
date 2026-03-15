from flask import Flask, request, render_template_string
import PyPDF2
from demo_ai import grade_demo

app = Flask(__name__)

# (Your HTML string remains the same as your snippet)

def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        student_file = request.files.get("student")
        key_file = request.files.get("key")

        if not student_file or not key_file:
            result = "Error: Missing files."
        else:
            # 1. Extract text from the uploaded PDFs
            student_text = extract_text_from_pdf(student_file)
            key_text = extract_text_from_pdf(key_file)
            
            # 2. Pass the text to your OpenRouter function
            result = grade_demo(student_text, key_text)

    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)