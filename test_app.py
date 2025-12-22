from app import add_numbers

def test_addition_correct():
    assert add_numbers(2, 3) == 5 # nosec B101

def test_addition_fail():
    # This test will fail intentionally to demonstrate CI catching it
    assert add_numbers(2, 3) == 5  # nosec B101
