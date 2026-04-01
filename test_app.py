import io
from unittest.mock import patch
from app import app

def test_homepage():
    client = app.test_client()
    r = client.get("/")
    assert r.status_code == 200  # nosec B101
    text = r.data.decode("utf-8")
    assert "AI Exam Grader" in text  # nosec B101

def test_post_without_files():
    client = app.test_client()
    r = client.post("/", data={}, content_type="multipart/form-data")
    assert r.status_code == 200  # nosec B101
    text = r.data.decode("utf-8")
    assert "Error: Missing files." in text  # nosec B101

# Ensure BOTH patches are here!
@patch("app.pdf_to_base64_images")
@patch("app.grade_demo")
def test_post_with_files(mock_grade_demo, mock_extract):
    # Mock the new image extractor to return a fake list
    mock_extract.return_value = ["fake_base64_string"] 
    mock_grade_demo.return_value = "Mocked AI Result: A+"

    client = app.test_client()

    data = {
        "student": (io.BytesIO(b"dummy"), "student.pdf"),
        "key": (io.BytesIO(b"dummy"), "key.pdf"),
    }

    r = client.post("/", data=data, content_type="multipart/form-data")
    
    assert r.status_code == 200  # nosec B101
    text = r.data.decode("utf-8")
    
    assert "Grade & Feedback" in text  # nosec B101
    assert "Mocked AI Result: A+" in text  # nosec B101