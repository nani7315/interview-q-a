import os
from io import BytesIO
from typing import Optional

import streamlit as st
from groq import Groq
from fpdf import FPDF

# ---------- CONFIG ---------- #

# Groq model – change here if Groq deprecates this model in future
MODEL_NAME = "llama-3.1-8b-instant"

# Get API key from environment variable
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    st.warning(
        "⚠️ GROQ_API_KEY environment variable not set. "
        "Set it in your system / Streamlit Cloud secrets."
    )

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# ---------- SMALL HELPERS ---------- #

def safe_pdf_text(line: str) -> str:
    """
    FPDF (fpdf2) only supports latin-1. This converts any unicode text
    to latin-1 with replacement so we don't get FPDFUnicodeEncodingException.
    """
    return line.encode("latin-1", "replace").decode("latin-1")


def make_pdf_from_text(title: str, content: str) -> bytes:
    """Create a PDF in memory from plain text and return bytes."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_title(safe_pdf_text(title))

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, safe_pdf_text(title), ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", size=11)

    for line in content.split("\n"):
        pdf.multi_cell(0, 6, safe_pdf_text(line))

    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    return pdf_bytes


def read_resume_file(uploaded_file) -> str:
    """Very simple resume text extractor (PDF/TXT/DOCX)."""
    if uploaded_file is None:
        return ""

    suffix = uploaded_file.name.lower().split(".")[-1]

    if suffix == "txt":
        return uploaded_file.read().decode("utf-8", errors="ignore")

    if suffix == "pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(uploaded_file)
            pages = [p.extract_text() or "" for p in reader.pages]
            return "\n".join(pages)
        except Exception:
            return ""

    if suffix in ("docx", "doc"):
        try:
            import docx
            doc = docx.Document(uploaded_file)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return ""

    # Fallback
    return ""


def call_groq(prompt: str, max_tokens: int = 4096) -> Optional[str]:
    if client is None:
        return "⚠️ Groq client is not initialised. Please set GROQ_API_KEY."

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a Mechanical Engineering interview assistant. "
                        "You ONLY ask and answer INTERVIEW questions, no stories."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error while calling Groq API:\n{e}"


def build_qa_prompt(
    section_label: str,
    num_questions: int,
    company_name: str,
    job_role: str,
    company_process: str,
    resume_text: str = "",
    focus: str = "",
) -> str:
    """
    Shared prompt builder. The model will return questions ONLY in the requested style.
    """

    return f"""
You are generating interview questions for a **Mechanical Engineering fresher**.

Section: {section_label}

Number of questions: {num_questions}

Company name: {company_name or "Not specified"}
Job role: {job_role or "Mechanical Engineer"}
Company process / products / domain: {company_process or "Not specified"}

Extra focus (if any): {focus or "General mechanical theory"}

If resume text is provided, use it mainly for RESUME-based questions.
Resume text:
\"\"\"{resume_text[:5000]}\"\"\"   # truncate just in case

RULES (VERY IMPORTANT – FOLLOW STRICTLY):

1. ONLY give **theoretical** questions (no long numerical problems, no coding).
2. Questions should start from **basic** level and then go to **moderate / little advanced**.
3. For each question, output exactly this pattern:

   **Q1. Question text here?**
   A: Simple, clean answer in 3–6 sentences, suitable for a fresher.
   F: Important formula, law or key point related to this concept.
      If no formula is needed, write: F: No key formula, only concept.

4. Q should be bold as in Markdown (**Q1. ...**) so it appears highlighted.
5. Keep language simple and interview-style.
6. DO NOT mix different sections. Only generate Q&A for this section: {section_label}.
7. Generate exactly {num_questions} Q&A pairs if possible.

Output MUST be pure Markdown text containing only the Q / A / F blocks.
"""


# ---------- STREAMLIT UI ---------- #

st.set_page_config(
    page_title="Mechanical Interview Q&A Assistant",
    layout="wide",
)

st.title("🧠 Mechanical Interview Q&A Assistant")
st.write(
    "Automatically generate **theoretical interview questions + simple answers + formulas** "
    "for Mechanical Engineering roles."
)

st.divider()

# 1) UPLOAD RESUME
st.header("1️⃣ Upload your resume")

uploaded_resume = st.file_uploader(
    "Upload resume file (PDF, DOCX, or TXT)",
    type=["pdf", "docx", "doc", "txt"],
)

resume_text = read_resume_file(uploaded_resume)

if uploaded_resume and not resume_text:
    st.warning("Could not read text from this file. Try a simpler PDF/TXT if possible.")

if resume_text:
    with st.expander("🔍 Preview extracted resume text (first 1000 chars)", expanded=False):
        st.text(resume_text[:1000])

st.divider()

# 2) COMPANY DETAILS & PROCESS
st.header("2️⃣ Company details & process")

col1, col2 = st.columns(2)
with col1:
    company_name = st.text_input("Company name", placeholder="e.g., Medha Servo Drives")
with col2:
    job_role = st.text_input("Job role", placeholder="e.g., Graduate Mechanical Engineer")

company_process = st.text_area(
    "Describe company products / process / domain (will help to aim questions)",
    placeholder=(
        "Example: Company designs and manufactures traction motors, power electronics, "
        "control systems for railway locomotives, etc."
    ),
)

st.divider()

# Question count (for all sections)
num_questions = st.slider(
    "Number of questions for each section",
    min_value=5,
    max_value=50,
    value=20,
    step=5,
    help="Be careful: very high numbers can generate a long response.",
)

# We'll store generated texts in session_state so that download buttons work.
if "resume_qa" not in st.session_state:
    st.session_state.resume_qa = ""
if "subject_qa" not in st.session_state:
    st.session_state.subject_qa = ""
if "hr_qa" not in st.session_state:
    st.session_state.hr_qa = ""


# ---------- 3) RESUME-BASED Q&A ---------- #

st.header("3️⃣ Resume-based interview questions")

st.write(
    "These focus on your **projects, skills, internships, tools, strengths** written in the resume."
)

if st.button("Generate RESUME-based Q&A"):
    if not resume_text:
        st.warning("Please upload a resume first.")
    else:
        with st.spinner("Generating resume-based questions & answers..."):
            prompt = build_qa_prompt(
                section_label="Resume-based interview round",
                num_questions=num_questions,
                company_name=company_name,
                job_role=job_role,
                company_process=company_process,
                resume_text=resume_text,
                focus="Ask about projects, tools, software, internships, strengths mentioned in resume.",
            )
            st.session_state.resume_qa = call_groq(prompt)

st.subheader("Resume-based Q&A")

if st.session_state.resume_qa:
    st.markdown(st.session_state.resume_qa)

    pdf_bytes = make_pdf_from_text("Resume-based Q&A", st.session_state.resume_qa)
    st.download_button(
        "📥 Download this section as PDF",
        data=pdf_bytes,
        file_name="resume_based_QA.pdf",
        mime="application/pdf",
    )
else:
    st.info("Click **Generate RESUME-based Q&A** to create questions for this section.")

st.divider()

# ---------- 4) COMPANY SUBJECT / TECHNICAL Q&A ---------- #

st.header("4️⃣ Company-related subject questions (technical)")

st.write(
    "Pure **theoretical subject questions** related to the company domain "
    "(design, manufacturing, thermal, machines, etc.)."
)

subject_focus = st.text_input(
    "Subject / domain focus (optional)",
    placeholder="e.g., Strength of Materials, Theory of Machines, Thermal, Manufacturing…",
)

if st.button("Generate TECHNICAL Q&A"):
    with st.spinner("Generating technical questions & answers..."):
        prompt = build_qa_prompt(
            section_label="Company related technical round",
            num_questions=num_questions,
            company_name=company_name,
            job_role=job_role,
            company_process=company_process,
            resume_text="",  # here we don't need resume content
            focus=subject_focus or "core mechanical subjects relevant to the company domain",
        )
        st.session_state.subject_qa = call_groq(prompt)

st.subheader("Technical Q&A")

if st.session_state.subject_qa:
    st.markdown(st.session_state.subject_qa)

    pdf_bytes = make_pdf_from_text("Technical Q&A", st.session_state.subject_qa)
    st.download_button(
        "📥 Download this section as PDF",
        data=pdf_bytes,
        file_name="technical_QA.pdf",
        mime="application/pdf",
    )
else:
    st.info("Click **Generate TECHNICAL Q&A** to create questions for this section.")

st.divider()

# ---------- 5) HR ROUND Q&A ---------- #

st.header("5️⃣ HR round questions")

st.write(
    "Behavioural and HR questions such as strengths, weaknesses, teamwork, relocation, etc."
)

if st.button("Generate HR Q&A"):
    with st.spinner("Generating HR questions & answers..."):
        prompt = build_qa_prompt(
            section_label="HR interview round",
            num_questions=num_questions,
            company_name=company_name,
            job_role=job_role,
            company_process=company_process,
            resume_text=resume_text,
            focus="HR questions: about candidate personality, teamwork, goals, family background, relocation, etc.",
        )
        st.session_state.hr_qa = call_groq(prompt)

st.subheader("HR Q&A")

if st.session_state.hr_qa:
    st.markdown(st.session_state.hr_qa)

    pdf_bytes = make_pdf_from_text("HR Q&A", st.session_state.hr_qa)
    st.download_button(
        "📥 Download this section as PDF",
        data=pdf_bytes,
        file_name="hr_QA.pdf",
        mime="application/pdf",
    )
else:
    st.info("Click **Generate HR Q&A** to create questions for this section.")

st.divider()

st.caption(
    "Tip: You can change number of questions, company details or subject focus and generate again for more practice sets."
)
