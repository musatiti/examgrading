import io
from unittest.mock import patch
from app import app

def test_homepage():
    """Test that the homepage loads correctly."""
    client = app.test_client()
    r = client.get("/")
    assert r.status_code == 200  # nosec B101
    assert b"AI Exam Grader" in r.data  # nosec B101

def test_post_without_files():
    """Test submitting the form without files returns the expected error message safely."""
    client = app.test_client()
    r = client.post("/grade", data={}, content_type="multipart/form-data")
    assert r.status_code == 200  # nosec B101
    assert b"Error: No Answer Key uploaded." in r.data  # nosec B101

@patch('app.grade_batch_exams')
def test_post_with_files(mock_grade_batch):
    """Test that submitting files successfully triggers the grading engine."""
    mock_grade_batch.return_value = "--- BATCH GRADING ENGINE: GPT-4O ---\nFINAL SCORE: 10/10"

    client = app.test_client()

    data = {
        'key_files': (io.BytesIO(b"fake key image data"), 'key.png'),
        'student_files': (io.BytesIO(b"fake student exam data"), 'student.png')
    }

    r = client.post("/grade", data=data, content_type="multipart/form-data")

    assert r.status_code == 200  # nosec B101
    assert b"FINAL SCORE: 10/10" in r.data  # nosec B101