import io
import pytest
from unittest.mock import patch
from app import app, db, User, Exam
from datetime import datetime


@pytest.fixture
def client():
    
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        # Push an application context so we can interact with the database
        with app.app_context():
            db.create_all()
            
            
            if not User.query.filter_by(Username='admin').first():
                new_admin = User(Username='admin', Password='just123')  # nosec B106
                db.session.add(new_admin)
                db.session.commit()
                
        yield client
        
        
        with app.app_context():
            db.drop_all()



def test_homepage(client):
    """Test that the homepage (login screen) loads correctly."""
    r = client.get("/")
    assert r.status_code == 200  # nosec B101
    assert b"Visionary Graders" in r.data  # nosec B101


def test_post_without_files(client):
    """Test submitting the form without files returns safely."""
   
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['user_id'] = 1

    
    r = client.post("/grading", data={}, content_type="multipart/form-data")
    
    
    assert r.status_code == 200  # nosec B101



@patch('app.grade_batch_exams')
@patch('app.extract_student_info')
@patch('app.pdf_to_base64_images')
def test_post_with_files(mock_pdf, mock_extract, mock_grade, client):
    """Test that submitting files successfully processes without crashing."""
    
    
    mock_pdf.return_value = ["fake_base64_image_data"]
    mock_extract.return_value = ("12345", "John Doe")
    mock_grade.return_value = "FINAL SCALED SCORE: 25 / 30"

    
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['user_id'] = 1

    
    with app.app_context():
        test_exam = Exam(CreatedBy=1, Subject="Math", Title="Midterm", ExamDate=datetime.utcnow().date())
        db.session.add(test_exam)
        db.session.commit()
        exam_id = test_exam.ExamId

    data = {
        'key': (io.BytesIO(b"fake key pdf data"), 'key.pdf'),
        'student': (io.BytesIO(b"fake student pdf data"), 'student.pdf'),
        'exam_id': str(exam_id),
        'session_id': 'test_session_123'
    }

    
    r = client.post("/grading", data=data, content_type="multipart/form-data")

    
    assert r.status_code == 200  # nosec B101