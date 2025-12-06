import os
from io import StringIO
from typing import List

import streamlit as st
from groq import Groq

from pypdf import PdfReader
import docx


# ------------------ CONFIG ------------------ #

MODEL_NAME = "llama-3.1-8b-instant"  # Current Groq production model :contentReference[oaicite:0]{index=0}

SYSTEM_PROMPT = """
You are a Mechanical Engineering Interview Preparation Assistant.

Your job:
- Generate high-quality interview *questions with answers*.
- Cover basic, intermediate and advanced level.
- For technical questions, include important formulas and short numeric examples when useful.
- Keep answers simple, clear and student-friendly.
- Write answers as if the candidate (the user) is speaking in the interview.
- Use this format exactly:

1. Question text...?
   Answer: Short but clear answer...

2. Question text...?
   Answer: ...

Do NOT write anything outside the numbered list.
"""

# --------------- HELPER FUNCTIONS --------------- #

@st.cache_resource(show_spinner=False)
def get_client() -> Groq:
    """Create a Groq client using the GROQ_API_KEY env variable."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        # In Streamlit Cloud, user must set this in Secrets
        raise RuntimeError(
            "GROQ_API_KEY is not set. Please set it in your environment or Streamlit secrets."
        )
    return Groq(api_key=api_key)


def call_model(prompt: str, temperature: float = 0.3) -> str:
    """Call Groq chat completion API."""
    client = get_client()

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=temperature,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content.strip()


def extract_text_from_pdf(file) -> str:
    reader = PdfReader(file)
    text = []
    for page in reader.pages:
        text.append(page.extract_text() or "")
    return "\n".join(text)


def extract_text_from_docx(file) -> str:
    document = docx.Document(file)
    return "\n".join(p.text for p in document.paragraphs)


def read_resume_file(uploaded_file) -> str:
    if uploaded_file is None:
        return ""

    file_type = uploaded_file.type.lower()

    try:
        if "pdf" in file_type:
            return extract_text_from_pdf(uploaded_file)
        elif "word" in file_type or uploaded_file.name.endswith(".docx"):
            return extract_text_from_docx(uploaded_file)
        else:
            # Treat as plain text
            stringio = StringIO(uploaded_file.getvalue().decode("utf-8", errors="ignore"))
            return stringio.read()
    except Exception as e:
        st.error(f"Could not read resume file: {e}")
        return ""


def shorten(text: str, max_chars: int = 8000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[Resume text truncated for length...]"


def combine_sections_text(sections: List[str]) -> str:
    return "\n\n".join(s for s in sections if s)


# ------------------ STREAMLIT UI ------------------ #

st.set_page_config(
    page_title="Mechanical Interview Q&A Assistant",
    layout="wide",
)

st.title("🧠 Mechanical Interview Q&A Assistant")
st.write(
    "Automatically generate interview **questions + simple answers** for Mechanical Engineering roles.\n"
    "Upload your resume, enter company details, then generate up to **50 questions** per section."
)

# Groq key check
if not os.environ.get("GROQ_API_KEY"):
    st.warning(
        "⚠️ `GROQ_API_KEY` is not set. "
        "Locally: `setx GROQ_API_KEY \"YOUR_KEY\"`. "
        "On Streamlit Cloud: Settings → Secrets → add `GROQ_API_KEY`."
    )

# Use session state to store generated text for download
for key in ["resume_qa", "technical_qa", "hr_qa"]:
    if key not in st.session_state:
        st.session_state[key] = ""

st.markdown("---")

# ---------- SECTION 1: Upload Resume ---------- #
st.header("1️⃣ Upload your resume")

uploaded_resume = st.file_uploader(
    "Upload resume (PDF / DOCX / TXT). Max ~200MB.",
    type=["pdf", "docx", "txt"],
)

resume_text = read_resume_file(uploaded_resume)
if uploaded_resume and resume_text:
    st.success(f"Loaded resume: **{uploaded_resume.name}**")
    with st.expander("Preview extracted resume text"):
        st.text(resume_text[:5000] + ("\n...\n[truncated]" if len(resume_text) > 5000 else ""))
else:
    st.info("Please upload your resume to enable resume-based interview questions.")

st.markdown("---")

# ---------- SECTION 2: Company / Role Details ---------- #
st.header("2️⃣ Company & role details")

col1, col2 = st.columns(2)
with col1:
    company_name = st.text_input("Company name", value="ACME Mechanical Solutions")
    role_title = st.text_input("Role / position", value="Graduate Mechanical Engineer")
with col2:
    experience_level = st.selectbox(
        "Experience level",
        ["Fresher", "0-2 years", "2-5 years", "5+ years"],
        index=0,
    )
    location = st.text_input("Job location (optional)", value="")

job_description = st.text_area(
    "Paste key responsibilities / job description (optional)",
    height=150,
    placeholder="Example: Responsibilities include design calculations, 3D modelling, testing, maintenance, coordination with production team...",
)

subjects = st.multiselect(
    "Technical subjects to focus on (for subject knowledge section)",
    [
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
        "Manufacturing / Production",
    ],
)

st.markdown("---")

# ---------- SECTION 3: Resume-based Q&A ---------- #
st.header("3️⃣ Resume-based interview questions")

resume_q_count = st.slider(
    "Number of resume-based Q&A",
    min_value=5,
    max_value=50,
    value=10,
    step=5,
)

if st.button("Generate resume-based Q&A"):
    if not resume_text:
        st.error("Please upload your resume first.")
    else:
        with st.spinner("Generating resume-based questions and answers..."):
            resume_prompt = f"""
You are preparing an interview for this candidate.

Resume:
\"\"\"{shorten(resume_text)}\"\"\"

Company: {company_name}
Role: {role_title}
Experience level: {experience_level}
Location: {location}
Job description:
\"\"\"{job_description}\"\"\"

Generate {resume_q_count} interview questions *based on the resume*:
- Focus on projects, internships, skills, tools, certifications, achievements and strengths mentioned in the resume.
- Start with easy questions and move to more advanced or detailed questions.
- For each question, immediately provide a short, confident sample answer as if the candidate is speaking.
- Use the required numbered format (Question + 'Answer:').
"""
            try:
                text = call_model(resume_prompt)
                st.session_state["resume_qa"] = text
            except Exception as e:
                st.error(f"Error while calling Groq API: {e}")

if st.session_state["resume_qa"]:
    st.subheader("Resume-based Q&A")
    st.markdown(st.session_state["resume_qa"])

st.markdown("---")

# ---------- SECTION 4: Subject knowledge Q&A ---------- #
st.header("4️⃣ Subject / technical knowledge questions")

tech_q_count = st.slider(
    "Number of technical Q&A",
    min_value=10,
    max_value=50,
    value=20,
    step=5,
)

difficulty = st.selectbox(
    "Difficulty range",
    ["Mostly basic", "Basic to intermediate", "Intermediate to advanced", "Full range (basic → advanced)"],
    index=3,
)

if st.button("Generate subject-knowledge Q&A"):
    with st.spinner("Generating technical questions and answers..."):
        subjects_text = ", ".join(subjects) if subjects else "core Mechanical Engineering subjects"

        tech_prompt = f"""
Company: {company_name}
Role: {role_title}

Generate {tech_q_count} *technical* interview questions for a Mechanical Engineering role.
Subjects to focus on: {subjects_text}
Difficulty range: {difficulty}

Requirements:
- Mix of conceptual, numerical and practical questions.
- Include important formulas where relevant.
- For numerical-type or formula questions, add a very small numeric example (1–3 lines) in the answer.
- Start from simple basics and gradually move to deeper, advanced concepts.
- For each question, give a clear and compact sample answer immediately.
- Use the required numbered format (Question + 'Answer:').
"""
        try:
            text = call_model(tech_prompt)
            st.session_state["technical_qa"] = text
        except Exception as e:
            st.error(f"Error while calling Groq API: {e}")

if st.session_state["technical_qa"]:
    st.subheader("Subject / technical Q&A")
    st.markdown(st.session_state["technical_qa"])

st.markdown("---")

# ---------- SECTION 5: HR / Behavioural Q&A ---------- #
st.header("5️⃣ Final HR round questions")

hr_q_count = st.slider(
    "Number of HR / behavioural Q&A",
    min_value=5,
    max_value=40,
    value=15,
    step=5,
)

if st.button("Generate HR round Q&A"):
    with st.spinner("Generating HR questions and answers..."):
        hr_prompt = f"""
Company: {company_name}
Role: {role_title}
Experience level: {experience_level}

Generate {hr_q_count} HR / behavioural interview questions for this candidate.
Cover topics like:
- Self introduction, strengths & weaknesses
- Team work, conflict handling, time management
- Learning attitude, handling pressure, relocation, night shifts (if relevant)
- Why this company, why this role, career goals
- Basic questions related to salary expectations and notice period

For each question, give a professional, positive and realistic sample answer as if the candidate is a Mechanical Engineering student / fresher.
Use the required numbered format (Question + 'Answer:').
"""
        try:
            text = call_model(hr_prompt)
            st.session_state["hr_qa"] = text
        except Exception as e:
            st.error(f"Error while calling Groq API: {e}")

if st.session_state["hr_qa"]:
    st.subheader("HR / behavioural Q&A")
    st.markdown(st.session_state["hr_qa"])

st.markdown("---")

# ---------- DOWNLOAD ALL Q&A ---------- #
st.header("6️⃣ Download all Q&A")

combined_text = combine_sections_text(
    [
        "# Resume-based Q&A\n" + st.session_state["resume_qa"]
        if st.session_state["resume_qa"]
        else "",
        "# Technical / subject Q&A\n" + st.session_state["technical_qa"]
        if st.session_state["technical_qa"]
        else "",
        "# HR round Q&A\n" + st.session_state["hr_qa"]
        if st.session_state["hr_qa"]
        else "",
    ]
)

if combined_text:
    st.download_button(
        label="⬇️ Download all questions & answers as .txt",
        data=combined_text.encode("utf-8"),
        file_name="mechanical_interview_qa.txt",
        mime="text/plain",
    )
else:
    st.info("Generate at least one section of Q&A to enable download.")
