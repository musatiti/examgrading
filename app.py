from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import urllib
import os
import base64
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
# Use environment variable, fallback to random secure bytes
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

SERVER_NAME = r'host.docker.internal\SQLEXPRESS'
DATABASE_NAME = 'visiongraders'

params = urllib.parse.quote_plus(
    f'DRIVER={{ODBC Driver 17 for SQL Server}};'
    f'SERVER={SERVER_NAME};'
    f'DATABASE={DATABASE_NAME};'
    f'UID=sa;'
    f'PWD=mypass123;'
)


# Check if we are running in a test environment (like GitHub Actions)
if os.environ.get('TESTING') == 'True':
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///:memory:" # Fast, temporary, built-in DB
    print("Using in-memory SQLite for testing...")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mssql+pyodbc:///?odbc_connect={params}"
    print("Using SQL Server...")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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
        admin_pw = os.environ.get('ADMIN_PASSWORD', 'SecureDefault123!')
        new_admin = User(Username='admin', Password=admin_pw)
        db.session.add(new_admin)
        db.session.commit()
        print("Successfully created the users table and added the admin account!")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

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
            error = "Login data error"

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
    is_debug = os.environ.get('FLASK_DEBUG') == 'True'
    app.run(debug=is_debug)