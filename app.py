from flask import Flask, request, render_template_string
from pdf2image import convert_from_bytes
from PIL import Image
import numpy as np
import cv2
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head><title>AI Exam Grader</title></head>
<body>
  <h1>AI Exam Grader (Q1 MCQ)</h1>
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

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

MODEL_ID = "microsoft/trocr-small-handwritten"
REVISION = "main"

PROCESSOR = TrOCRProcessor.from_pretrained(MODEL_ID, revision=REVISION)  # nosec B615
MODEL = VisionEncoderDecoderModel.from_pretrained(MODEL_ID, revision=REVISION)  # nosec B615
MODEL.to(DEVICE)
MODEL.eval()

def pil_to_bgr(img: Image.Image):
    arr = np.array(img.convert("RGB"))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

def crop_table_region(page_bgr):
    h, w = page_bgr.shape[:2]
    return page_bgr[int(h * 0.66):int(h * 0.90), int(w * 0.05):int(w * 0.95)]

def get_answer_row(table_bgr):
    th, tw = table_bgr.shape[:2]
    return table_bgr[int(th * 0.45):th, :]

def split_10_cells(row_bgr):
    h, w = row_bgr.shape[:2]
    cell_w = w / 10.0
    cells = []
    for i in range(10):
        x0 = int(i * cell_w)
        x1 = int((i + 1) * cell_w)
        cell = row_bgr[:, x0:x1]
        ch, cw = cell.shape[:2]
        cell = cell[int(ch * 0.08):int(ch * 0.95), int(cw * 0.12):int(cw * 0.88)]
        cells.append(cell)
    return cells

def mask_handwriting(cell_bgr):
    b, g, r = cv2.split(cell_bgr.astype(np.int16))
    blue = b - ((g + r) // 2)
    red = r - ((g + b) // 2)

    m1 = (blue > 18).astype(np.uint8) * 255
    m2 = (red > 18).astype(np.uint8) * 255
    mask = cv2.bitwise_or(m1, m2)

    mask = cv2.medianBlur(mask, 3)
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
    return mask

def trocr_single_letter(cell_bgr):
    mask = mask_handwriting(cell_bgr)

    ys, xs = np.where(mask > 0)
    if len(xs) < 20:
        return "?"

    x0, x1 = xs.min(), xs.max()
    y0, y1 = ys.min(), ys.max()

    pad = 8
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(mask.shape[1] - 1, x1 + pad)
    y1 = min(mask.shape[0] - 1, y1 + pad)

    crop = mask[y0:y1 + 1, x0:x1 + 1]
    crop = cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)

    pil = Image.fromarray(255 - crop).convert("RGB")

    inputs = PROCESSOR(images=pil, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        ids = MODEL.generate(inputs.pixel_values, max_new_tokens=4)
    text = PROCESSOR.batch_decode(ids, skip_special_tokens=True)[0].strip().lower()

    for ch in text:
        if ch in "abcd":
            return ch
    return "?"

def extract_answers(pdf_file, page_index=1):
    pages = convert_from_bytes(pdf_file.read(), dpi=250)
    if len(pages) <= page_index:
        return None

    page_bgr = pil_to_bgr(pages[page_index])
    table = crop_table_region(page_bgr)
    row = get_answer_row(table)
    cells = split_10_cells(row)
    return [trocr_single_letter(c) for c in cells]

def grade(student, key):
    correct = 0
    lines = []
    for i in range(10):
        s, k = student[i], key[i]
        if s == "?" or k == "?":
            lines.append(f"Q{i+1}: student={s} | key={k} -> Unknown (OCR)")
            continue
        ok = (s == k)
        correct += 1 if ok else 0
        lines.append(f"Q{i+1}: student={s} | key={k} -> {'Correct' if ok else 'Wrong'}")
    return correct, "\n".join(lines)

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        try:
            student_file = request.files["student"]
            key_file = request.files["key"]

            student_ans = extract_answers(student_file, page_index=1)
            key_ans = extract_answers(key_file, page_index=1)

            if not student_ans or not key_ans:
                result = "Could not read page 2 from PDFs."
            else:
                score, details = grade(student_ans, key_ans)
                unknowns = sum(1 for x in student_ans if x == "?") + sum(1 for x in key_ans if x == "?")
                result = (
                    f"MCQ (Q1) Score: {score}/10\n"
                    f"Student: {' '.join(student_ans)}\n"
                    f"Key:     {' '.join(key_ans)}\n"
                    f"Unknown cells: {unknowns}\n\n"
                    f"{details}"
                )
        except Exception as e:
            result = f"ERROR: {e}"

    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    app.run( host="0.0.0.0", # nosec B104
            port=5000, 
            debug=False )