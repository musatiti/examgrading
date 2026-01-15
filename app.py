from flask import Flask, request, render_template_string
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
import numpy as np
import cv2

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head><title>AI Exam Grader</title></head>
<body>
  <h1>AI Exam Grader (MCQ Q1)</h1>
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

def pil_to_cv(img: Image.Image):
    arr = np.array(img.convert("RGB"))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

def find_answer_table(page_bgr):
    h, w = page_bgr.shape[:2]
    bottom = page_bgr[int(h * 0.55):h, 0:w]  # search only bottom half

    gray = cv2.cvtColor(bottom, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # make borders/ink pop
    thr = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 7
    )

    # connect table lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 5))
    thr2 = cv2.dilate(thr, kernel, iterations=2)

    contours, _ = cv2.findContours(thr2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    # choose the widest large rectangle (the answers table)
    best = None
    best_score = 0
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cw * ch
        if area < 20000:
            continue
        aspect = cw / max(ch, 1)
        score = area * aspect
        if score > best_score:
            best_score = score
            best = (x, y, cw, ch)

    if not best:
        return None

    x, y, cw, ch = best
    table = bottom[y:y + ch, x:x + cw]
    return table

def remove_table_lines(cell_bin):
    # remove horizontal and vertical lines so OCR sees only handwriting
    h, w = cell_bin.shape[:2]

    hor_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(10, w // 3), 1))
    ver_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(10, h // 3)))

    horizontal = cv2.morphologyEx(cell_bin, cv2.MORPH_OPEN, hor_kernel, iterations=1)
    vertical = cv2.morphologyEx(cell_bin, cv2.MORPH_OPEN, ver_kernel, iterations=1)

    no_lines = cv2.subtract(cell_bin, horizontal)
    no_lines = cv2.subtract(no_lines, vertical)
    return no_lines

def ocr_choice_from_cell(cell_bgr):
    gray = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2GRAY)

    # binarize
    thr = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 7
    )

    thr = remove_table_lines(thr)

    # enlarge
    thr = cv2.resize(thr, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)

    # denoise slightly
    thr = cv2.medianBlur(thr, 3)

    # OCR single char
    cfg = "--oem 1 --psm 10 -c tessedit_char_whitelist=abcdABCD"
    txt = pytesseract.image_to_string(thr, config=cfg).strip().lower()

    for ch in txt:
        if ch in "abcd":
            return ch
    return "?"

def extract_mcq_answers(pdf_file, page_index=1):
    pages = convert_from_bytes(pdf_file.read(), dpi=200)
    if len(pages) <= page_index:
        return None

    page_bgr = pil_to_cv(pages[page_index])
    table = find_answer_table(page_bgr)
    if table is None:
        return None

    # focus on the lower half of the table where answers are written (letters row)
    th, tw = table.shape[:2]
    letters_row = table[int(th * 0.45):th, 0:tw]

    # split into 10 equal columns
    cell_w = tw / 10.0
    answers = []
    for i in range(10):
        x0 = int(i * cell_w)
        x1 = int((i + 1) * cell_w)

        cell = letters_row[:, x0:x1]

        # trim borders inside each cell
        ch, cw = cell.shape[:2]
        cell = cell[int(ch * 0.05):int(ch * 0.95), int(cw * 0.10):int(cw * 0.90)]

        answers.append(ocr_choice_from_cell(cell))

    return answers

def grade_mcq(student_ans, key_ans):
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

            student_ans = extract_mcq_answers(student_file, page_index=1)
            key_ans = extract_mcq_answers(key_file, page_index=1)

            if not student_ans or not key_ans:
                result = "Could not detect the answers table on page 2. Try a clearer scan."
            else:
                correct, details = grade_mcq(student_ans, key_ans)
                unknowns = sum(1 for x in student_ans if x == "?") + sum(1 for x in key_ans if x == "?")

                result = (
                    f"MCQ (Q1) Score: {correct}/10\n"
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