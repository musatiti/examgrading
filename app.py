import streamlit as st
from openai import OpenAI
from pypdf import PdfReader

# Setup OpenAI client
client = OpenAI(api_key="YOUR_OPENAI_API_KEY")

st.title("📚 AI Exam Grader")

# 1. File Uploaders
student_file = st.file_uploader("Upload Student Paper", type=["pdf", "txt"])
key_file = st.file_uploader("Upload Answer Key", type=["pdf", "txt"])

def extract_text(uploaded_file):
    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        return "\n".join([page.extract_text() for page in reader.pages])
    return str(uploaded_file.read())

if st.button("Grade Paper"):
    if student_file and key_file:
        with st.spinner("Analyzing..."):
            student_text = extract_text(student_file)
            key_text = extract_text(key_file)
            
            # 2. Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Grade the student's work based strictly on the key sheet provided."},
                    {"role": "user", "content": f"KEY SHEET:\n{key_text}\n\nSTUDENT PAPER:\n{student_text}"}
                ]
            )
            
            # 3. Show Result
            st.subheader("Final Grade & Feedback")
            st.write(response.choices[0].message.content)
    else:
        st.error("Please upload both files first!")