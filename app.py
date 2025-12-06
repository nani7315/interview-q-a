# app.py
import os
import textwrap

import streamlit as st
from groq import Groq

# ----------------- CONFIG ----------------- #

st.set_page_config(
    page_title="Mechanical Interview Q&A Assistant",
    page_icon="🛠️",
    layout="wide",
)

SYSTEM_PROMPT = """
You are an Interview Q&A Assistant for Mechanical Engineering students (mostly freshers).

Your job:
- Generate interview question–answer pairs.
- Explain in very simple English.
- For technical topics, include key formulas and, when possible, a tiny numerical-style example.
- For HR topics, keep answers 4–7 sentences, positive and professional.
- When analysing resumes, give practical and clear suggestions.
"""

# Load Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def call_groq(prompt: str, temperature: float = 0.4) -> str:
    """
    Helper to call Groq chat completion.
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # use a currently supported Groq model
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error while calling Groq API:\n\n{e}"


# -------------- RESUME READER -------------- #
def read_resume_file(uploaded_file) -> str:
    """
    Try to read text from uploaded resume.
    Supports: .txt, .pdf, .docx (basic).
    """
    if uploaded_file is None:
        return ""

    name = uploaded_file.name.lower()

    if name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8", errors="ignore")

    # Lazy imports so app still works if libs not installed
    if name.endswith(".pdf"):
        try:
            import PyPDF2

            reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception:
            return "Could not read PDF. Please upload a .txt version of your resume."

    if name.endswith(".docx"):
        try:
            import docx  # python-docx

            doc = docx.Document(uploaded_file)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return "Could not read DOCX. Please upload a .txt version of your resume."

    return "Unsupported file type. Please upload .txt, .pdf or .docx."


# ----------------- UI SIDEBAR ----------------- #
st.sidebar.header("⚙️ Settings")

role = st.sidebar.text_input(
    "Target role",
    value="Mechanical Engineer - Fresher",
)

q_type = st.sidebar.selectbox(
    "Question type",
    options=["HR", "Technical", "Both"],
)

subjects = st.sidebar.multiselect(
    "Technical subjects (for Technical/Both)",
    options=[
        "Strength of Materials (SOM)",
        "Theory of Machines (TOM)",
        "Thermodynamics",
        "Heat Transfer",
        "Fluid Mechanics",
        "Manufacturing / Production",
        "Machine Design",
        "Engineering Mechanics",
        "Material Science",
    ],
    default=[
        "Strength of Materials (SOM)",
        "Theory of Machines (TOM)",
        "Thermodynamics",
        "Manufacturing / Production",
    ],
)

num_qas = st.sidebar.slider(
    "Number of Q&A pairs",
    min_value=3,
    max_value=20,
    value=8,
)

st.sidebar.info(
    "1️⃣ Generate Q&A with formulas/examples\n\n"
    "2️⃣ Upload your resume for personalised tips."
)

subjects_text = ", ".join(subjects) if subjects else "General Mechanical Engineering topics"


# ----------------- MAIN TITLE ----------------- #
st.title("🛠️ Mechanical Interview Q&A Assistant")
st.write(
    "Automatically generate interview **questions + simple answers** for Mechanical "
    "Engineering roles. For technical topics, the assistant tries to include **formulas** "
    "and **small examples**."
)

# =============== SECTION 1: Q&A GENERATION =============== #
st.markdown("## 1️⃣ Generate Questions with Answers")

if not os.getenv("GROQ_API_KEY"):
    st.warning(
        "GROQ_API_KEY environment variable is not set. "
        "Set it before deploying/running this app."
    )

if st.button("Generate Q&A", type="primary"):
    user_prompt = f"""
    Role: {role}
    Question type: {q_type}
    Technical subjects: {subjects_text}
    Number of Q&A pairs: {num_qas}

    Task:
    Generate {num_qas} interview QUESTION + ANSWER pairs.

    Rules:
    - If Question type is 'HR', only HR questions.
    - If 'Technical', only core Mechanical Engineering questions.
    - If 'Both', mix HR and technical (about 50-50).
    - Format output EXACTLY like this:
      Q1: <question text>
      A1: <answer text>

      Q2: <question text>
      A2: <answer text>
      ... and so on.

    - For technical questions:
        * Give short but correct explanations.
        * Include important formulas in LaTeX style, e.g., σ = P / A.
        * Add a one-line numeric-style example where possible.
    - For HR questions:
        * Answers should be 4–7 sentences.
        * Sound like a well-prepared fresher (polite and confident).
    """

    with st.spinner("Talking to Groq and generating Q&A..."):
        qa_text = call_groq(user_prompt)

    st.session_state["qa_text"] = qa_text

# Show generated Q&A
st.markdown("### Generated Q&A")
if "qa_text" in st.session_state:
    st.markdown(st.session_state["qa_text"])
else:
    st.info("Click **Generate Q&A** to create interview questions with answers.")


# =============== SECTION 2: RESUME UPLOAD & ANALYSIS =============== #
st.markdown("---")
st.markdown("## 2️⃣ Upload your Resume (Optional)")

uploaded_resume = st.file_uploader(
    "Upload your resume file (.pdf / .docx / .txt)",
    type=["pdf", "docx", "txt"],
)

if uploaded_resume is not None:
    resume_text = read_resume_file(uploaded_resume)

    if resume_text.startswith("Could not") or resume_text.startswith("Unsupported"):
        st.error(resume_text)
    else:
        st.success("Resume uploaded. Generating personalised summary & tips...")

        trimmed_text = textwrap.shorten(
            resume_text, width=6000, placeholder="\n...[truncated]..."
        )

        resume_prompt = f"""
        Here is the text of a Mechanical Engineering fresher's resume:

        \"\"\"{trimmed_text}\"\"\"

        Tasks:
        1. Write a 5–7 line introduction I can use to answer
           "Tell me about yourself" in an interview.
        2. Give 5 bullet-point suggestions to improve this resume.
        3. Create 3 HR-style and/or technical interview questions
           based on this resume, with sample answers.

        Format your response in clear markdown with headings.
        """

        with st.spinner("Analysing your resume using Groq..."):
            resume_feedback = call_groq(resume_prompt, temperature=0.5)

        st.markdown("### Resume-based Guidance")
        st.markdown(resume_feedback)
else:
    st.info("Upload your resume to get a custom 'Tell me about yourself' and tips.")
