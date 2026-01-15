from flask import Flask, request, render_template_string
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head><title>AI Exam Grader</title></head>
<body>
  <h1>AI Exam Grader</h1>
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

def crop_answer_area(page_img: Image.Image) -> Image.Image:
    w, h = page_img.size
    # Bottom part where the 1..10 answers are
    # These ratios work for your provided PDFs
    return page_img.crop((int(w * 0.06), int(h * 0.79), int(w * 0.94), int(h * 0.94)))

def split_10_cells(row_img: Image.Image):
    w, h = row_img.size
    cell_w = w / 10.0
    cells = []
    for i in range(10):
        x0 = int(i * cell_w)
        x1 = int((i + 1) * cell_w)
        # crop inside a bit to avoid borders
        cells.append(row_img.crop((x0 + 6, 0, x1 - 6, h)))
    return cells

def read_one_choice(cell_img: Image.Image) -> str:
    img = cell_img.convert("L")
    img = img.point(lambda p: 0 if p < 160 else 255)  # simple threshold
    cfg = "--psm 10 -c tessedit_char_whitelist=abcdABCD"
    text = pytesseract.image_to_string(img, config=cfg).strip().lower()
    for ch in text:
        if ch in "abcd":
            return ch
    return "?"

def extract_mcq_answers(pdf_file, page_index=1):
    # page_index=1 => second page (0-based)
    pages = convert_from_bytes(pdf_file.read())
    if len(pages) <= page_index:
        return None

    page = pages[page_index].convert("RGB")
    area = crop_answer_area(page)
    cells = split_10_cells(area)
    answers = [read_one_choice(c) for c in cells]
    return answers

def grade_mcq(student_ans, key_ans):
    correct = 0
    lines = []
    for i in range(10):
        s = student_ans[i]
        k = key_ans[i]
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
                result = "Could not read page 2 from one of the PDFs."
            else:
                correct, details = grade_mcq(student_ans, key_ans)
                result = (
                    f"MCQ (Q1) Score: {correct}/10\n"
                    f"Student: {' '.join(student_ans)}\n"
                    f"Key:     {' '.join(key_ans)}\n\n"
                    f"{details}"
                )

        except Exception as e:
            result = f"ERROR: {e}"

    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    app.run( host="0.0.0.0", # nosec B104
            port=5000, 
            debug=False )



