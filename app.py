import re
from difflib import SequenceMatcher
from io import BytesIO

from flask import Flask, request, render_template_string
from pdf2image import convert_from_bytes
from PIL import Image

import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

app = Flask(__name__)

# Handwritten TrOCR model (AI OCR)
# Model exists on Hugging Face and is designed for handwritten text. :contentReference[oaicite:1]{index=1}
PROCESSOR = TrOCRProcessor.from_pretrained("microsoft/trocr-small-handwritten")
MODEL = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-small-handwritten")
MODEL.eval()

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL.to(DEVICE)

HTML = """
<!DOCTYPE html>
<html>
<head><title>AI Exam Grader</title></head>
<body>
  <h1>AI Exam Grader (Local AI - TrOCR)</h1>
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

def ocr_image_trocr(pil_img: Image.Image) -> str:
    pil_img = pil_img.convert("RGB")
    inputs = PROCESSOR(images=pil_img, return_tensors="pt")
    pixel_values = inputs.pixel_values.to(DEVICE)

    with torch.no_grad():
        generated_ids = MODEL.generate(pixel_values, max_new_tokens=128)

    text = PROCESSOR.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return text.strip()

def pdf_to_text_trocr(file_storage, max_pages=3) -> str:
    pages = convert_from_bytes(file_storage.read())
    out = []
    for page in pages[:max_pages]:
        out.append(ocr_image_trocr(page))
    return "\n".join([x for x in out if x]) or "NO TEXT DETECTED"

def normalize_lines(text: str):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines

def sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def grade_by_lines(key_text: str, student_text: str):
    key_lines = normalize_lines(key_text)
    stu_lines = normalize_lines(student_text)

    n = min(len(key_lines), len(stu_lines))
    if n == 0:
        return "Could not extract readable answers (handwriting OCR failed). Try clearer scans."

    correct = 0
    details = []

    for i in range(n):
        k = key_lines[i]
        s = stu_lines[i]
        score = sim(k, s)

        ok = score >= 0.75
        if ok:
            correct += 1

        details.append(
            f"Q{i+1} | match {score*100:.1f}% | {'Correct' if ok else 'Wrong'}\n"
            f"Key: {k}\n"
            f"Student: {s}\n"
        )

    total = f"Total: {correct}/{n}\n"
    feedback = (
        "Feedback:\n"
        "- OCR is AI-based and may misread handwriting; clearer scans improve accuracy.\n"
        "- If many mismatches are close, handwriting recognition likely introduced errors.\n"
    )
    return total + "\n".join(details) + "\n" + feedback

@app.route("/", methods=["GET", "POST"])
def index():
    result = None

    if request.method == "POST":
        try:
            student_file = request.files["student"]
            key_file = request.files["key"]

            key_text = pdf_to_text_trocr(key_file, max_pages=3)
            student_text = pdf_to_text_trocr(student_file, max_pages=3)

            result = grade_by_lines(key_text, student_text)

        except Exception as e:
            result = f"ERROR: {e}"

    return render_template_string(HTML, result=result)



if __name__ == "__main__":
    app.run( host="0.0.0.0", # nosec B104
            port=5000, 
            debug=False )



