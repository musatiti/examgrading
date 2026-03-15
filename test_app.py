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

# We patch your grade_demo function so we don't make real API calls during testing!
@patch("app.grade_demo")
def test_post_with_files(mock_grade_demo):
    # Set up the fake AI response
    mock_grade_demo.return_value = "Mocked AI Result: A+"

    client = app.test_client()

    # A minimal valid PDF structure to prevent PyPDF2 from crashing
    minimal_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\nstartxref\n0\n%%EOF"

    data = {
        "student": (io.BytesIO(minimal_pdf), "student.pdf"),
        "key": (io.BytesIO(minimal_pdf), "key.pdf"),
    }

    r = client.post("/", data=data, content_type="multipart/form-data")
    
    assert r.status_code == 200  # nosec B101
    text = r.data.decode("utf-8")
    
    # Check that it successfully processed and returned our mocked string
    assert "Grade & Feedback" in text  # nosec B101
    assert "Mocked AI Result: A+" in text  # nosec B101