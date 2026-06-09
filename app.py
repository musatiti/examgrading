<<<<<<< HEAD
from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import urllib
import os
import base64  # ضفنا هاي المكتبة عشان نشفر الصور للذكاء الاصطناعي
from demo_ai import grade_batch_exams, extract_student_info
import uuid
from datetime import datetime
import re
import fitz
import json
from flask import Response, stream_with_context
import threading
import time as time_module
import time

app = Flask(__name__)
app.secret_key = 'just_secret_key_2026'

# ==========================================
# 1. إعدادات الاتصال بقاعدة بيانات SQL Server
# ==========================================
SERVER_NAME = r'DESKTOP-QRPPRUD' 
DATABASE_NAME = 'visiongrader'

params = urllib.parse.quote_plus(
    f'DRIVER={{ODBC Driver 17 for SQL Server}};'
    f'SERVER={SERVER_NAME};'
    f'DATABASE={DATABASE_NAME};'
    f'Trusted_Connection=yes;'
)

app.config['SQLALCHEMY_DATABASE_URI'] = f"mssql+pyodbc:///?odbc_connect={params}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# 2. بناء الجداول في قاعدة البيانات
# ==========================================
class User(db.Model):
    __tablename__ = 'users'
    UserId   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Username = db.Column(db.String(50), unique=True, nullable=False)
    Password = db.Column(db.String(50), nullable=False)

class Student(db.Model):
    __tablename__ = 'students'
    StudentId   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    FullName    = db.Column(db.String(100), nullable=False)
    StudentCode = db.Column(db.String(50), nullable=False, unique=True)
    Class       = db.Column(db.String(50))

class Exam(db.Model):
    __tablename__ = 'exams'
    ExamId    = db.Column(db.Integer, primary_key=True, autoincrement=True)
    CreatedBy = db.Column(db.Integer, db.ForeignKey('users.UserId'), nullable=False)
    Subject   = db.Column(db.String(100), nullable=False)
    Title     = db.Column(db.String(200), nullable=False)
    ExamDate  = db.Column(db.Date, default=datetime.utcnow)

class Result(db.Model):
    __tablename__ = 'results'
    ResultId   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ExamId     = db.Column(db.Integer, db.ForeignKey('exams.ExamId'), nullable=False)
    StudentId  = db.Column(db.Integer, db.ForeignKey('students.StudentId'), nullable=False)
    Score      = db.Column(db.Float)
    AIFeedback = db.Column(db.Text)
    GradedAt   = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all() 
    admin_user = User.query.filter_by(Username='admin').first()
    if not admin_user:
        new_admin = User(Username='admin', Password='just123')
        db.session.add(new_admin)
        db.session.commit()
        print("✅ تم إنشاء جدول المستخدمين وإضافة حساب admin بنجاح!")

# ==========================================
# 3. إعدادات رفع الملفات
# ==========================================
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# دالة صغيرة لتحويل الصورة لـ Base64
def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# ==========================================
# 4. مسارات الموقع (Routes)
# ==========================================
@app.route("/exams", methods=["GET", "POST"])
def exams():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == "POST":
        subject  = request.form.get("subject")
        title    = request.form.get("title")
        exam_date = request.form.get("exam_date")

        new_exam = Exam(
            CreatedBy=session['user_id'],
            Subject=subject,
            Title=title,
            ExamDate=datetime.strptime(exam_date, "%Y-%m-%d").date()
        )
        db.session.add(new_exam)
        db.session.commit()

    all_exams = Exam.query.order_by(Exam.ExamDate.desc()).all()
    return render_template("exams.html", exams=all_exams)


@app.route("/exams/delete/<int:exam_id>")
def delete_exam(exam_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    exam = Exam.query.get(exam_id)
    if exam:
        db.session.delete(exam)
        db.session.commit()
    return redirect(url_for('exams'))


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = request.form.get("username")
        pw   = request.form.get("password")

        found_user = User.query.filter_by(Username=user).first()

        if found_user and found_user.Password == pw:
            session['logged_in'] = True
            session['user_id']   = found_user.UserId
            return redirect(url_for('exams'))
        else:
            error = "خطأ في بيانات الدخول"

    return render_template("login.html", error=error)

def pdf_to_base64_images(pdf_path):
    doc = fitz.open(pdf_path)
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("jpeg")
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        images.append(img_b64)
    doc.close()
    return images


# Global dict to track progress per session
grading_progress = {}

@app.route("/grading/progress/<session_id>")
def grading_progress_stream(session_id):
    def generate():
        while True:
            progress = grading_progress.get(session_id, {})
            data = json.dumps(progress)
            yield f"data: {data}\n\n"
            
            if progress.get("done"):
                break
            time.sleep(0.5)
    
    return Response(stream_with_context(generate()),
                    mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route("/grading", methods=["GET", "POST"])
def grading():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    all_exams        = Exam.query.order_by(Exam.ExamDate.desc()).all()
    selected_exam_id = request.args.get("exam_id", type=int)
    results_list     = []

    if request.method == "POST":
        student_files = request.files.getlist("student")
        key_file      = request.files.get("key")
        exam_id       = request.form.get("exam_id")
        session_id    = request.form.get("session_id")
        total         = len(student_files)

        if student_files and key_file and exam_id:
            key_path = os.path.join(UPLOAD_FOLDER, secure_filename(key_file.filename))
            key_file.save(key_path)
            key_images = pdf_to_base64_images(key_path)

            for idx, student_file in enumerate(student_files):
                student_filename = secure_filename(student_file.filename)

                # Update progress
                grading_progress[session_id] = {
                    "current":  idx + 1,
                    "total":    total,
                    "filename": student_filename,
                    "done":     False
                }

                student_path = os.path.join(UPLOAD_FOLDER, student_filename)
                student_file.save(student_path)

                try:
                    student_images = pdf_to_base64_images(student_path)
                    student_code, student_name = extract_student_info(student_images[0])
                    student_submissions = {student_filename: student_images}
                    result_text = grade_batch_exams(student_submissions, key_images)

                    score = None
                    match = re.search(r'FINAL SCALED SCORE:\s*([\d.]+)\s*/\s*30', result_text)
                    if match:
                        score = float(match.group(1))

                    if student_code:
                        student = Student.query.filter_by(StudentCode=str(student_code)).first()
                        if not student:
                            student = Student(
                                FullName=student_name or "Unknown",
                                StudentCode=str(student_code),
                                Class="Unknown"
                            )
                            db.session.add(student)
                            db.session.flush()

                        grade_result = Result(
                            ExamId=int(exam_id),
                            StudentId=student.StudentId,
                            Score=score,
                            AIFeedback=result_text,
                            GradedAt=datetime.utcnow()
                        )
                        db.session.add(grade_result)
                        db.session.commit()

                        results_list.append({
                            "filename": student_filename,
                            "name":     student.FullName,
                            "code":     student.StudentCode,
                            "score":    score,
                            "status":   "success"
                        })
                    else:
                        results_list.append({
                            "filename": student_filename,
                            "name":     "Unknown",
                            "code":     "Not detected",
                            "score":    score,
                            "status":   "warning"
                        })

                except Exception as e:
                    db.session.rollback()
                    results_list.append({
                        "filename": student_filename,
                        "name":     "—",
                        "code":     "—",
                        "score":    None,
                        "status":   "error",
                        "error":    str(e)
                    })

            # Mark done
            grading_progress[session_id] = {
                "current":  total,
                "total":    total,
                "filename": "Complete",
                "done":     True
            }

    return render_template("grading.html", results_list=results_list,
                           exams=all_exams, selected_exam_id=selected_exam_id)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route("/students", methods=["GET", "POST"])
def students():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    if request.method == "POST":
        full_name    = request.form.get("full_name")
        student_code = request.form.get("student_code")
        student_class = request.form.get("student_class")
        
        existing = Student.query.filter_by(StudentCode=student_code).first()
        if not existing:
            new_student = Student(
                FullName=full_name,
                StudentCode=student_code,
                Class=student_class
            )
            db.session.add(new_student)
            db.session.commit()
    
    all_students = Student.query.all()
    return render_template("students.html", students=all_students)


@app.route("/students/delete/<student_id>")
def delete_student(student_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    student = Student.query.get(student_id)
    if student:
        db.session.delete(student)
        db.session.commit()
    return redirect(url_for('students'))


@app.route("/students/edit/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    student = Student.query.get(student_id)
    if not student:
        return redirect(url_for('students'))

    if request.method == "POST":
        student.FullName    = request.form.get("full_name")
        student.StudentCode = request.form.get("student_code")
        student.Class       = request.form.get("student_class")
        db.session.commit()
        return redirect(url_for('students'))

    return render_template("edit_student.html", student=student)

@app.route("/results")
def results():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    all_results = db.session.query(Result, Student, Exam)\
        .join(Student, Result.StudentId == Student.StudentId)\
        .join(Exam, Result.ExamId == Exam.ExamId)\
        .order_by(Result.GradedAt.desc()).all()

    return render_template("results.html", results=all_results)
@app.route("/results/<int:result_id>")
def view_result(result_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    result  = Result.query.get(result_id)
    student = Student.query.get(result.StudentId)
    exam    = Exam.query.get(result.ExamId)

    return render_template("view_result.html", result=result, student=student, exam=exam)


if __name__ == "__main__":
    app.run(debug=True)
=======
import os
import base64
import secrets
from flask import Flask, request, render_template_string
from demo_ai import grade_batch_exams 

app = Flask(__name__)
# Securely generates a random key if one isn't provided in the environment
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(24))

# ==========================================
# FRONTEND: HTML TEMPLATES (EMBEDDED)
# ==========================================

INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Exam Grader</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f9; margin: 0; padding: 0; }
        .navbar { background-color: #333; overflow: hidden; padding: 14px 20px; margin-bottom: 20px; }
        .navbar a { color: white; text-decoration: none; padding: 14px 20px; font-weight: bold; }
        .navbar a:hover { background-color: #ddd; color: black; border-radius: 4px; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h1 { color: #0056b3; text-align: center; }
        form { display: flex; flex-direction: column; gap: 15px; margin-top: 20px; }
        label { font-weight: bold; }
        input[type="file"] { padding: 10px; border: 1px solid #ccc; border-radius: 4px; }
        button { background-color: #0056b3; color: white; padding: 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold; }
        button:hover { background-color: #004494; }
    </style>
</head>
<body>
    <div class="navbar">
        <a href="/">Grader Home</a>
        <a href="/syllabus">Course Syllabi</a>
    </div>
    <div class="container">
        <h1>AI Exam Grader</h1>
        <form action="/grade" method="POST" enctype="multipart/form-data">
            <label for="key_files">Upload Answer Key (Images or PDF):</label>
            <input type="file" name="key_files" id="key_files" multiple required>
            
            <label for="student_files">Upload Student Exams (Images or PDFs):</label>
            <input type="file" name="student_files" id="student_files" multiple required>
            
            <button type="submit">Grade Exams</button>
        </form>
    </div>
</body>
</html>
"""

# THE NEW DIRECTORY MENU
SYLLABUS_LIST_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Course Syllabi</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f9; margin: 0; padding: 0; }
        .navbar { background-color: #333; overflow: hidden; padding: 14px 20px; margin-bottom: 20px; }
        .navbar a { color: white; text-decoration: none; padding: 14px 20px; font-weight: bold; }
        .navbar a:hover { background-color: #ddd; color: black; border-radius: 4px; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h1 { color: #0056b3; border-bottom: 2px solid #0056b3; padding-bottom: 10px; }
        .course-list { display: flex; flex-direction: column; gap: 10px; margin-top: 20px; }
        .course-list a { padding: 15px; background: #e9ecef; border-left: 5px solid #0056b3; text-decoration: none; color: #333; font-weight: bold; border-radius: 0 4px 4px 0; transition: background 0.2s; }
        .course-list a:hover { background: #d3d9df; }
    </style>
</head>
<body>
    <div class="navbar">
        <a href="/">Grader Home</a>
        <a href="/syllabus">Course Syllabi</a>
    </div>
    <div class="container">
        <h1>Select a Syllabus</h1>
        <p>Choose a course below to view its grading policies and schedule.</p>
        <div class="course-list">
            <a href="/syllabus/cs451">CS451: Computer Architecture</a>
            <a href="#">More courses can be added here...</a>
        </div>
    </div>
</body>
</html>
"""

# THE SPECIFIC CS451 SYLLABUS
CS451_SYLLABUS_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CS451 Syllabus</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f9; margin: 0; padding: 0; }
        .navbar { background-color: #333; overflow: hidden; padding: 14px 20px; margin-bottom: 20px; }
        .navbar a { color: white; text-decoration: none; padding: 14px 20px; font-weight: bold; }
        .navbar a:hover { background-color: #ddd; color: black; border-radius: 4px; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h1 { color: #0056b3; border-bottom: 2px solid #0056b3; padding-bottom: 10px; }
        h2 { color: #333; margin-top: 25px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #0056b3; color: white; }
        .back-link { display: inline-block; margin-bottom: 20px; text-decoration: none; color: #0056b3; font-weight: bold; }
        .back-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="navbar">
        <a href="/">Grader Home</a>
        <a href="/syllabus">Course Syllabi</a>
    </div>
    <div class="container">
        <a href="/syllabus" class="back-link">&larr; Back to Syllabus List</a>
        <h1>CS451: Computer Architecture</h1>
        <p><strong>Institution:</strong> Jordan University of Science and Technology, Faculty of Computer & Information Technology</p>
        <p><strong>Semester:</strong> First Semester 2025-2026 | <strong>Credits:</strong> 3 | <strong>Level:</strong> JNQF 7</p>
        <h2>Course Description</h2>
        <p>The role of performance, essential notions of computer systems design, datapath and control of processor, memory hierarchies, control units, registers, data transfer and buses. The characteristics of instruction sets, pipeline techniques, high-speed memories like cache, and multiprocessors.</p>
        <h2>Instructors & Schedule</h2>
        <ul>
            <li><strong>Prof. Yahya Tashtoush</strong> (A1L3) | yahya-t@just.edu.jo</li>
            <li><strong>Dr. Ala'a Jararwah</strong> (A1L3)</li>
        </ul>
        <p><strong>Lectures:</strong> Sunday & Tuesday, 11:00 - 12:00 (Rooms CH2106 & C3013)</p>
        <h2>Course Outline</h2>
        <table>
            <tr><th>Weeks</th><th>Topic</th><th>Readings</th></tr>
            <tr><td>Weeks 1-4</td><td>Computer Abstractions and Technology</td><td>Chapter 1</td></tr>
            <tr><td>Weeks 5-8</td><td>Instructions: Language of the Computer</td><td>Chapter 2</td></tr>
            <tr><td>Weeks 9-10</td><td>Arithmetic for Computers</td><td>Chapter 3</td></tr>
            <tr><td>Weeks 10-14</td><td>The Processor</td><td>Chapter 4</td></tr>
        </table>
        <h2>Evaluation</h2>
        <table>
            <tr><th>Assessment Tool</th><th>Weight</th></tr>
            <tr><td>First Exam</td><td>30%</td></tr>
            <tr><td>Second Exam</td><td>30%</td></tr>
            <tr><td>Final Exam</td><td>40%</td></tr>
        </table>
    </div>
</body>
</html>
"""

# ==========================================
# SERVER: FLASK ROUTING
# ==========================================

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

# Shows the list of syllabi
@app.route('/syllabus')
def syllabus_list():
    return render_template_string(SYLLABUS_LIST_HTML)

# Shows the specific CS451 syllabus
@app.route('/syllabus/cs451')
def syllabus_cs451():
    return render_template_string(CS451_SYLLABUS_HTML)

@app.route('/grade', methods=['POST'])
def grade():
    try:
        key_files = request.files.getlist('key_files')
        key_images = [base64.b64encode(f.read()).decode('utf-8') for f in key_files if f.filename]
        
        if not key_images:
            return "Error: No Answer Key uploaded."

        student_files = request.files.getlist('student_files')
        student_submissions = {}
        
        for f in student_files:
            if f.filename:
                b64_img = base64.b64encode(f.read()).decode('utf-8')
                if f.filename not in student_submissions:
                    student_submissions[f.filename] = []
                student_submissions[f.filename].append(b64_img)

        if not student_submissions:
            return "Error: No Student Exams uploaded."

        final_report = grade_batch_exams(student_submissions, key_images)
        
        return f"<a href='/' style='font-family: Arial; padding: 10px; background: #333; color: white; text-decoration: none; border-radius: 4px;'>&larr; Back to Grader</a><br><br><pre style='font-family: monospace; background: #f4f4f9; padding: 20px;'>{final_report}</pre>"
        
    except Exception as e:
        return f"An error occurred: {str(e)}"

if __name__ == '__main__':
    # Debug turned off for production security. 
    # nosec B104 tells Bandit that 0.0.0.0 is intentional for Docker.
    app.run(host='0.0.0.0', port=5000, debug=False)  # nosec B104
>>>>>>> 4e6cd8e0f0c4a521577d4ac76ef7cad7606edfdd
