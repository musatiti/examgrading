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

# Patch BOTH the PDF reader and the OpenRouter AI 
@patch("app.extract_text_from_pdf")
@patch("app.grade_demo")
def test_post_with_files(mock_grade_demo, mock_extract):
    # 1. Tell the fake PDF reader what to return
    mock_extract.return_value = "Simulated extracted text from PDF"
    
    # 2. Tell the fake AI what to return
    mock_grade_demo.return_value = "Mocked AI Result: A+"

    client = app.test_client()

    # 3. Because PyPDF2 is bypassed, we can safely use simple dummy bytes again!
    data = {
        "student": (io.BytesIO(b"dummy"), "student.pdf"),
        "key": (io.BytesIO(b"dummy"), "key.pdf"),
    }

    r = client.post("/", data=data, content_type="multipart/form-data")
    
    assert r.status_code == 200  # nosec B101
    text = r.data.decode("utf-8")
    
    # 4. Verify our app processed the mocked data correctly
    assert "Grade & Feedback" in text  # nosec B101
    assert "Mocked AI Result: A+" in text  # nosec B101