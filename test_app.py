import io
import pytest
from unittest.mock import patch
from app import app, db, User, Exam
from datetime import datetime

# --- FIXTURE: Set up the test environment ---
@pytest.fixture
def client():
    # Tell Flask we are testing (disables error catching so we can see real errors)
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        # Push an application context so we can interact with the database
        with app.app_context():
            db.create_all()
            
            # Ensure the admin user exists for our tests
            if not User.query.filter_by(Username='admin').first():
                new_admin = User(Username='admin', Password='just123')  # nosec B106
                db.session.add(new_admin)
                db.session.commit()
                
        yield client
        
        # Clean up the database after the test finishes
        with app.app_context():
            db.drop_all()

# --- TESTS ---

def test_homepage(client):
    """Test that the homepage (login screen) loads correctly."""
    r = client.get("/")
    assert r.status_code == 200  # nosec B101
    assert b"Visionary Graders" in r.data  # nosec B101


def test_post_without_files(client):
    """Test submitting the form without files returns safely."""
    # 1. Mock a logged-in user session
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['user_id'] = 1

    # 2. Post to the correct /grading route with no files
    r = client.post("/grading", data={}, content_type="multipart/form-data")
    
    # 3. The app should just re-render the grading template (200 OK)
    assert r.status_code == 200  # nosec B101


# We must mock the PDF extractor and AI grading functions so they don't actually run during tests
@patch('app.grade_batch_exams')
@patch('app.extract_student_info')
@patch('app.pdf_to_base64_images')
def test_post_with_files(mock_pdf, mock_extract, mock_grade, client):
    """Test that submitting files successfully processes without crashing."""
    
    # 1. Set up our fake AI/PDF responses
    mock_pdf.return_value = ["fake_base64_image_data"]
    mock_extract.return_value = ("12345", "John Doe")
    mock_grade.return_value = "FINAL SCALED SCORE: 25 / 30"

    # 2. Mock a logged-in user session
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['user_id'] = 1

    # 3. Create a fake Exam in the database so the result has an ExamId to link to
    with app.app_context():
        test_exam = Exam(CreatedBy=1, Subject="Math", Title="Midterm", ExamDate=datetime.utcnow().date())
        db.session.add(test_exam)
        db.session.commit()
        exam_id = test_exam.ExamId

    # 4. Prepare the fake files (notice the keys match the 'name' attributes in your HTML forms)
    data = {
        'key': (io.BytesIO(b"fake key pdf data"), 'key.pdf'),
        'student': (io.BytesIO(b"fake student pdf data"), 'student.pdf'),
        'exam_id': str(exam_id),
        'session_id': 'test_session_123'
    }

    # 5. Make the post request
    r = client.post("/grading", data=data, content_type="multipart/form-data")

    # 6. Ensure the request succeeded
    assert r.status_code == 200  # nosec B101