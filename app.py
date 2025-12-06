import os
from groq import Groq
import streamlit as st

# ---------------- AI CONFIG ---------------- #

# Load Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are an Interview Preparation Assistant for Mechanical Engineering students.

Your responsibilities:
- Generate HR and Technical interview questions.
- Give clear, simple sample answers.
- Keep answers suitable for freshers.
- For technical topics, stick to Mechanical subjects.
"""

# -------------- HELPER FUNCTIONS -------------- #

def call_model(messages):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error while calling Groq API:\n{e}"


def generate_questions(role, q_type, count, subjects_text):
    user_prompt = f"""
    I am preparing for the role: {role}.
    Give me {count} {q_type} interview questions.
    Technical subjects: {subjects_text}
    Only give numbered questions, without answers.
    """

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    return call_model(messages)


def generate_answer(role, question, q_type, subjects_text):
    user_prompt = f"""
    Role: {role}
    Question type: {q_type}
    Subjects: {subjects_text}

    Question:
    "{question}"

    Give a sample answer in simple English, suitable for freshers.
    """

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    return call_model(messages)


# ----------------- STREAMLIT APP ----------------- #

def main():
    st.set_page_config(page_title="Interview Q&A Assistant - Groq", layout="centered")
    st.title("🤖 Mechanical Interview Q&A Assistant (FREE Groq API)")

    # Sidebar
    st.sidebar.header("⚙️ Settings")

    role = st.sidebar.text_input("Target Role", "Mechanical Engineer - Fresher")

    q_type = st.sidebar.selectbox("Question Type", ["HR", "Technical", "Both"])

    tech_subjects = st.sidebar.multiselect(
        "Technical Subjects",
        ["SOM", "TOM", "Thermodynamics", "Heat Transfer", "Fluid Mechanics", "Manufacturing", "Design", "Mechanics", "Materials"],
        default=["SOM", "TOM", "Manufacturing"]
    )

    subjects_text = ", ".join(tech_subjects)
    num_questions = st.sidebar.slider("Number of Questions", 3, 20, 5)

    st.markdown("### 1️⃣ Generate Interview Questions")

    if st.button("Generate Questions"):
        with st.spinner("Generating..."):
            output = generate_questions(role, q_type, num_questions, subjects_text)
        st.session_state["questions"] = output

    if "questions" in st.session_state:
        st.text_area("Generated Questions", st.session_state["questions"], height=200)

    st.markdown("---")

    st.markdown("### 2️⃣ Get a Sample Answer")

    question = st.text_input("Enter any question:")

    if st.button("Get Sample Answer"):
        with st.spinner("Generating..."):
            answer = generate_answer(role, question, q_type, subjects_text)
        st.write(answer)


if __name__ == "__main__":
    main()
