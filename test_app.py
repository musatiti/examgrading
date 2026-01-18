import io
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


def test_post_with_files():
    client = app.test_client()

    data = {
        "student": (io.BytesIO(b"test"), "student.pdf"),
        "key": (io.BytesIO(b"test"), "key.pdf"),
    }

    r = client.post("/", data=data, content_type="multipart/form-data")
    assert r.status_code == 200  # nosec B101
    text = r.data.decode("utf-8")
    assert "Grade & Feedback" in text  # nosec B101
    assert "Demo Mode (Simulated AI Result)" in text  # nosec B101 
