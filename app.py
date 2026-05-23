import os
import base64
from flask import Flask, request, render_template_string
from demo_ai import grade_batch_exams 

app = Flask(__name__)
app.secret_key = "super_secret_key"

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
        <a href="/syllabus">Course Syllabus</a>
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

SYLLABUS_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Course Syllabus - CS451</title>
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
    </style>
</head>
<body>
    <div class="navbar">
        <a href="/">Grader Home</a>
        <a href="/syllabus">Course Syllabus</a>
    </div>
    <div class="container">
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

@app.route('/syllabus')
def syllabus():
    return render_template_string(SYLLABUS_HTML)

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

        # Calls the AI logic from your separate demo_ai.py file
        final_report = grade_batch_exams(student_submissions, key_images)
        
        return f"<a href='/' style='font-family: Arial; padding: 10px; background: #333; color: white; text-decoration: none; border-radius: 4px;'>&larr; Back to Grader</a><br><br><pre style='font-family: monospace; background: #f4f4f9; padding: 20px;'>{final_report}</pre>"
        
    except Exception as e:
        return f"An error occurred: {str(e)}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)