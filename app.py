from flask import Flask, request, render_template_string
from pdf2image import convert_from_bytes
from PIL import Image
import numpy as np
import cv2
import pytesseract

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

def pil_to_bgr(img: Image.Image):
    arr = np.array(img.convert("RGB"))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

def detect_answers_table(page_bgr):
    h, w = page_bgr.shape[:2]

    # Search ONLY bottom part where the table exists
    y0 = int(h * 0.60)
    roi = page_bgr[y0:h, :]

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    bw = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 8
    )

    # Detect grid lines
    hor = cv2.morphologyEx(
        bw,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(60, w // 6), 1)),
        iterations=1,
    )
    ver = cv2.morphologyEx(
        bw,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, h // 20))),
        iterations=1,
    )

    grid = cv2.bitwise_or(hor, ver)
    grid = cv2.dilate(grid, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)), iterations=2)

    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    # Choose the widest, short rectangle (the table)
    best = None
    best_score = -1
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cw * ch
        if area < 40000:
            continue
        aspect = cw / max(ch, 1)
        # table is very wide and not tall
        if aspect < 6:
            continue
        score = area * aspect
        if score > best_score:
            best_score = score
            best = (x, y, cw, ch)

    if not best:
        return None

    x, y, cw, ch = best
    table = roi[y:y + ch, x:x + cw]
    return table

def remove_lines(bin_img):
    h, w = bin_img.shape[:2]
    hor_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, w // 2), 1))
    ver_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(10, h // 2)))

    hor = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, hor_kernel, iterations=1)
    ver = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, ver_kernel, iterations=1)

    out = cv2.subtract(bin_img, hor)
    out = cv2.subtract(out, ver)
    return out

def ocr_cell_abcd(cell_bgr):
    gray = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2GRAY)
    bw = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 7
    )

    bw = remove_lines(bw)
    bw = cv2.resize(bw, None, fx=6, fy=6, interpolation=cv2.INTER_NEAREST)
    bw = cv2.medianBlur(bw, 3)

    cfg = "--oem 1 --psm 10 -c tessedit_char_whitelist=abcdABCD"
    txt = pytesseract.image_to_string(bw, config=cfg).strip().lower()
    for ch in txt:
        if ch in "abcd":
            return ch
    return "?"

def extract_answers(pdf_file):
    pages = convert_from_bytes(pdf_file.read(), dpi=250)
    if len(pages) < 2:
        return None

    page2_bgr = pil_to_bgr(pages[1])
    table = detect_answers_table(page2_bgr)
    if table is None:
        return None

    th, tw = table.shape[:2]

    # Keep ONLY the bottom row (answers) to avoid the 1..10 header row
    answers_row = table[int(th * 0.50):th, :]

    ah, aw = answers_row.shape[:2]
    cell_w = aw / 10.0

    answers = []
    for i in range(10):
        x0 = int(i * cell_w)
        x1 = int((i + 1) * cell_w)
        cell = answers_row[:, x0:x1]

        ch, cw = cell.shape[:2]
        # cut inner region to avoid borders
        cell = cell[int(ch * 0.10):int(ch * 0.95), int(cw * 0.12):int(cw * 0.88)]

        answers.append(ocr_cell_abcd(cell))

    return answers

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

            student_ans = extract_answers(student_file)
            key_ans = extract_answers(key_file)

            if not student_ans or not key_ans:
                result = "Could not detect the answers table on page 2 (student or key)."
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