import io
from unittest.mock import patch
from app import app

def test_homepage():
    """Test that the homepage loads successfully."""
    client = app.test_client()
    r = client.get("/")
    assert r.status_code == 200

def test_post_without_files():
    """Test submitting the form without files safely returns the homepage."""
    client = app.test_client()
    r = client.post("/", data={}, content_type="multipart/form-data")
    assert r.status_code == 200

@patch('app.grade_batch_exams')
def test_post_with_files(mock_grade_batch):
    """Test that submitting files successfully triggers the grading engine."""
    # Tell the mock function to return a fake grade report instead of pinging the real API
    mock_grade_batch.return_value = "--- BATCH GRADING ENGINE: GPT-4O ---\nFINAL SCORE: 10/10"
    
    client = app.test_client()
    
    # Create fake files in memory to simulate a user upload
    data = {
        'key_files': (io.BytesIO(b"fake key image data"), 'key.png'),
        'student_files': (io.BytesIO(b"fake student exam data"), 'student.png')
    }
    
    r = client.post("/", data=data, content_type="multipart/form-data")
    
    # Verify the server accepted the files and rendered the result
    assert r.status_code == 200
    assert b"FINAL SCORE: 10/10" in r.data