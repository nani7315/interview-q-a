import os
from io import BytesIO

import streamlit as st
from groq import Groq

# Optional: for reading resume files
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None


# ------------------ GROQ CONFIG ------------------ #

MODEL_NAME = "llama3-8b-8192"
"""
If you see an error like `model_decommissioned` in the app logs,
log into the Groq console, check which chat models are available now,
and put the new model name in MODEL_NAME.
"""

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def call_groq(system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str:
    """
    Helper to call Groq chat completion.
    """
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error while calling Groq API:\n\n{e}"


# ------------------ RESUME HELPERS ------------------ #

def extract_text_from_pdf(file: BytesIO) -> str:
    if PdfReader is None:
        return "PyPDF2 is not installed. Please add `PyPDF2` to requirements.txt."
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def extract_text_from_docx(file: BytesIO) -> str:
    if docx is None:
        return "python-docx is not installed. Please add `python-docx` to requirements.txt."
    document = docx.Document(file)
    return "\n".join(p.text for p in document.paragraphs)


def get_resume_text(uploaded_file) -> str:
    if uploaded_file is None:
        return ""

    name = uploaded_file.name.lower()
    data = BytesIO(uploaded_file.read())

    if name.endswith(".pdf"):
        return extract_text_from_pdf(data)
    elif name.endswith(".docx") or name.endswith(".doc"):
        return extract_text_from_docx(data)
    else:
        return uploaded_file.getvalue().decode("utf-8", errors="ignore")


# ------------------ STREAMLIT UI ------------------ #

st.set_page_config(
    page_title="Mechanical Interview Q&A Assistant",
    layout="wide"
)

st.title("🧠 Mechanical Interview Q&A Assistant")

st.markdown(
    "Automatically generate **interview questions + simple answers** for Mechanical Engineering roles."
)
st.markdown("---")

# Session state for storing Q&A for download
if "resume_qa" not in st.session_state:
    st.session_state.resume_qa = ""
if "subject_qa" not in st.session_state:
    st.session_state.subject_qa = ""
if "hr_qa" not in st.session_state:
    st.session_state.hr_qa = ""

# ============= SECTION 1: Upload Resume ============= #

st.header("1️⃣ Upload your resume")

resume_file = st.file_uploader(
    "Upload your resume (PDF, DOCX or TXT)",
    type=["pdf", "docx", "doc", "txt"]
)

resume_text = ""
if resume_file is not None:
    resume_text = get_resume_text(resume_file)
    st.success("✅ Resume uploaded and text extracted.")
    with st.expander("Show extracted resume text (optional)"):
        st.text_area("Extracted text", resume_text, height=200)
else:
    st.info("Please upload your resume to get resume-based interview questions.")

st.markdown("---")

# ============= SECTION 2: Company details ============= #

st.header("2️⃣ Company & Role details")

col1, col2 = st.columns(2)

with col1:
    company_name = st.text_input("Company name", placeholder="e.g. Medha Servo Drives Pvt Ltd")
    role = st.text_input("Role / Position", placeholder="e.g. Graduate Engineer Trainee - R&D")
    location = st.text_input("Location (optional)", placeholder="e.g. Hyderabad")

with col2:
    domain = st.text_input(
        "Main domain / department",
        placeholder="e.g. Design, Production, R&D, Testing"
    )
    tech_stack = st.text_area(
        "Key tools / technologies (comma separated)",
        placeholder="e.g. SolidWorks, AutoCAD, FEA, MATLAB, CNC machining"
    )

job_desc = st.text_area(
    "Job description or important points (paste from JD if available)",
    placeholder="Paste important responsibilities, skills, and expectations from JD..."
)

company_block = f"""
Company: {company_name or 'N/A'}
Role: {role or 'N/A'}
Location: {location or 'N/A'}
Domain: {domain or 'N/A'}
Tools / Technologies: {tech_stack or 'N/A'}
Job Description / Important Points:
{job_desc or 'N/A'}
"""

st.markdown("---")

# ============= SECTION 3: Resume-based Q&A ============= #

st.header("3️⃣ Resume-based interview questions (with answers)")

st.caption("These questions focus on your projects, internships, skills, and experience mentioned in the resume.")

if st.button("Generate resume-based Q&A (10–15 questions)"):
    if not resume_text.strip():
        st.warning("⚠️ Please upload your resume first.")
    else:
        system_prompt = """
        You are an Interview Assistant for Mechanical Engineering students and freshers.
        Your job is to generate realistic interview Q&A based ONLY on the candidate's resume
        and the target company role.

        Style:
        - Give **10–15 questions**.
        - Mix basic to advanced level.
        - For each question, immediately give the answer below it.
        - Format like:
          Q1: ...
          A1: ...
        - Use very simple English, like a well-prepared student speaking.
        - Focus on projects, internships, tools, skills, and strengths in the resume.
        """

        user_prompt = f"""
        ===== RESUME TEXT =====
        {resume_text}

        ===== COMPANY & ROLE =====
        {company_block}

        Based on the above, generate 10–15 resume-based interview questions with answers.
        """

        st.session_state.resume_qa = call_groq(system_prompt, user_prompt)

if st.session_state.resume_qa:
    st.subheader("Resume-based Q&A")
    st.markdown(st.session_state.resume_qa.replace("Q1:", "\n\n**Q1:**"), unsafe_allow_html=True)

st.markdown("---")

# ============= SECTION 4: Subject / Company technical Q&A ============= #

st.header("4️⃣ Subject & company-related technical questions")

st.caption(
    "Here we create **50 technical questions** (basic → advanced) related to your chosen subjects "
    "and the company domain, with examples and formulas where useful."
)

subject_focus = st.text_input(
    "Main technical subjects / topics",
    placeholder="e.g. Strength of Materials, Theory of Machines, Design of Machine Elements"
)

if st.button("Generate technical Q&A (50 questions)"):
    if not subject_focus.strip():
        st.warning("⚠️ Please enter at least one subject/topic.")
    else:
        system_prompt = """
        You are a Mechanical Engineering interview trainer.
        Your job is to create technical interview Q&A from basic to advanced level.

        Requirements:
        - Prepare 50 questions in total.
        - Split roughly: 20 basic, 20 intermediate, 10 advanced.
        - Focus only on the given subjects and the company domain.
        - For numerical / formula related topics, include:
          - the main formula (clearly written),
          - a very small example or explanation.
        - Answer just below each question.
        - Use the format:
          Q1 (Basic): ...
          A1: ...
          Q2 (Basic): ...
          A2: ...
          ...
        - Use simple, exam-style and interview-style language.
        """

        user_prompt = f"""
        Subjects / topics the candidate wants to prepare:
        {subject_focus}

        Company & role information:
        {company_block}

        Now create 50 technical interview questions with answers
        following the instructions.
        """

        st.session_state.subject_qa = call_groq(system_prompt, user_prompt, temperature=0.5)

if st.session_state.subject_qa:
    st.subheader("Technical (subject & company) Q&A")
    st.markdown(st.session_state.subject_qa.replace("Q1", "\n\nQ1"), unsafe_allow_html=True)

st.markdown("---")

# ============= SECTION 5: HR round Q&A ============= #

st.header("5️⃣ Final HR round questions (with answers)")

st.caption(
    "General HR questions: communication, attitude, goals, family background, relocation, etc., "
    "customised for this company and role."
)

if st.button("Generate HR round Q&A (15 questions)"):
    system_prompt = """
    You are an HR Interview Assistant for Mechanical Engineering freshers.
    Generate practical HR interview questions and sample answers.

    Requirements:
    - Give around 15 questions.
    - Mix personal, behavioral, and job-related HR questions.
    - Format:
      Q1: ...
      A1: ...
    - Answers must be polite, positive, and realistic for an Indian fresher.
    - Mention family background and strengths when appropriate.
    - Keep English simple and clear.
    """

    user_prompt = f"""
    Company & role:
    {company_block}

    Candidate is a fresher (Mechanical Engineering). Generate 15 HR questions with sample answers.
    """

    st.session_state.hr_qa = call_groq(system_prompt, user_prompt, temperature=0.6)

if st.session_state.hr_qa:
    st.subheader("HR Round Q&A")
    st.markdown(st.session_state.hr_qa.replace("Q1", "\n\nQ1"), unsafe_allow_html=True)

st.markdown("---")

# ============= DOWNLOAD SECTION ============= #

st.header("📥 Download all generated Q&A")

all_sections = []

if st.session_state.resume_qa:
    all_sections.append("===== RESUME-BASED Q&A =====\n" + st.session_state.resume_qa)

if st.session_state.subject_qa:
    all_sections.append("===== TECHNICAL (SUBJECT & COMPANY) Q&A =====\n" + st.session_state.subject_qa)

if st.session_state.hr_qa:
    all_sections.append("===== HR ROUND Q&A =====\n" + st.session_state.hr_qa)

if all_sections:
    full_text = "\n\n\n".join(all_sections)
    st.download_button(
        label="⬇️ Download all Q&A as .txt",
        data=full_text.encode("utf-8"),
        file_name="mechanical_interview_QA_full_set.txt",
        mime="text/plain"
    )
else:
    st.info("Generate some Q&A first, then the download button will appear.")
