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

def find_table_bbox_lines(page_bgr):
    gray = cv2.cvtColor(page_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    thr = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 10
    )

    h, w = thr.shape
    hor_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(40, w // 8), 1))
    ver_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(40, h // 15)))

    horizontal = cv2.morphologyEx(thr, cv2.MORPH_OPEN, hor_kernel, iterations=1)
    vertical = cv2.morphologyEx(thr, cv2.MORPH_OPEN, ver_kernel, iterations=1)

    grid = cv2.bitwise_or(horizontal, vertical)
    grid = cv2.dilate(grid, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)), iterations=2)

    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    best_area = 0
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cw * ch
        aspect = cw / max(ch, 1)
        if area < 50000:
            continue
        if aspect < 3:
            continue
        if area > best_area:
            best_area = area
            best = (x, y, cw, ch)

    return best

def find_table_bbox(page_bgr):
    h, w = page_bgr.shape[:2]

    # avoid bottom black strip in some scans
    top_roi = page_bgr[:int(h * 0.85), :]
    bb = find_table_bbox_lines(top_roi)
    if bb:
        return bb

    # fallback: search bottom half (student table often near bottom)
    bottom = page_bgr[int(h * 0.55):h, :]
    bb2 = find_table_bbox_lines(bottom)
    if bb2:
        x, y, cw, ch = bb2
        return (x, y + int(h * 0.55), cw, ch)

    return None

def crop_table(page_bgr):
    bb = find_table_bbox(page_bgr)
    if not bb:
        return None

    x, y, cw, ch = bb
    h, w = page_bgr.shape[:2]

    # expand horizontally to capture all 10 columns (student scan shadow can cut bbox)
    x0 = int(w * 0.02)
    x1 = int(w * 0.98)

    y0 = max(0, y - 5)
    y1 = min(h, y + ch + 5)

    return page_bgr[y0:y1, x0:x1]

def remove_table_lines(bin_img):
    h, w = bin_img.shape[:2]
    hor_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, w // 3), 1))
    ver_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, h // 2)))

    horizontal = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, hor_kernel, iterations=1)
    vertical = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, ver_kernel, iterations=1)

    no_lines = cv2.subtract(bin_img, horizontal)
    no_lines = cv2.subtract(no_lines, vertical)
    return no_lines

def ocr_cell_abcd(cell_bgr):
    gray = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2GRAY)
    thr = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 7
    )
    thr = remove_table_lines(thr)
    thr = cv2.resize(thr, None, fx=5, fy=5, interpolation=cv2.INTER_NEAREST)
    thr = cv2.medianBlur(thr, 3)

    cfg = "--oem 1 --psm 10 -c tessedit_char_whitelist=abcdABCD"
    txt = pytesseract.image_to_string(thr, config=cfg).strip().lower()

    for ch in txt:
        if ch in "abcd":
            return ch
    return "?"

def extract_answers_from_page2(pdf_file):
    pages = convert_from_bytes(pdf_file.read(), dpi=250)
    if len(pages) < 2:
        return None

    page2_bgr = pil_to_bgr(pages[1])
    table = crop_table(page2_bgr)
    if table is None:
        return None

    th, tw = table.shape[:2]

    # letters are in the lower band of the table (skip the numbers row)
    letters_band = table[int(th * 0.35):int(th * 0.95), :]

    bh, bw = letters_band.shape[:2]
    cell_w = bw / 10.0

    answers = []
    for i in range(10):
        x0 = int(i * cell_w)
        x1 = int((i + 1) * cell_w)
        cell = letters_band[:, x0:x1]

        ch, cw = cell.shape[:2]
        cell = cell[int(ch * 0.05):int(ch * 0.95), int(cw * 0.12):int(cw * 0.88)]

        answers.append(ocr_cell_abcd(cell))

    return answers

def grade(student_ans, key_ans):
    correct = 0
    lines = []
    for i in range(10):
        s = student_ans[i]
        k = key_ans[i]
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

            student_ans = extract_answers_from_page2(student_file)
            key_ans = extract_answers_from_page2(key_file)

            if not student_ans or not key_ans:
                result = "Could not detect the answers table on page 2 for student or key."
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