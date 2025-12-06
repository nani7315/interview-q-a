import os
import io
from typing import Optional

import streamlit as st
from groq import Groq
from fpdf import FPDF

# Optional: only needed if you really want to read PDF/DOCX content.
# Make sure these are in requirements.txt if you use them.
try:
    import PyPDF2
    import docx2txt
    HAS_DOC_LIBS = True
except Exception:
    HAS_DOC_LIBS = False


# ------------------------- CONFIG ------------------------- #

st.set_page_config(
    page_title="Mechanical Interview Q&A Assistant",
    layout="wide"
)

# ---- Groq client (put your key in environment variable GROQ_API_KEY) ---- #
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Use a CURRENT Groq chat model name here.
# If this model ever gets decommissioned, just change the string.
MODEL_NAME = "llama-3.1-70b-versatile"  # <-- update from Groq console if needed


# --------------------- HELPER FUNCTIONS ------------------- #

def call_groq(system_prompt: str, user_prompt: str) -> str:
    """Call Groq chat completion with given prompts."""
    if not GROQ_API_KEY:
        return "⚠️ GROQ_API_KEY is not set. Please set it as an environment variable."

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error while calling Groq API:\n{e}"


def extract_text_from_resume(uploaded_file) -> str:
    """Try to extract plain text from PDF/DOCX/TXT resume."""
    if uploaded_file is None:
        return ""

    filename = uploaded_file.name.lower()

    if not HAS_DOC_LIBS:
        # Fallback – just try to decode as text
        return uploaded_file.read().decode("utf-8", errors="ignore")

    try:
        if filename.endswith(".pdf"):
            reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text

        elif filename.endswith(".docx"):
            # docx2txt needs a path-like object; uploaded_file works directly
            return docx2txt.process(uploaded_file)

        else:
            # Assume text
            return uploaded_file.read().decode("utf-8", errors="ignore")

    except Exception:
        # Last fallback
        return uploaded_file.read().decode("utf-8", errors="ignore")


def build_pdf(text: str, title: str) -> bytes:
    """Create a simple PDF from given text and return it as bytes."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.multi_cell(0, 10, title)
    pdf.ln(4)

    # Body
    pdf.set_font("Arial", "", 11)
    for line in text.splitlines():
        if not line.strip():
            pdf.ln(4)
        else:
            pdf.multi_cell(0, 6, line)

    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    return pdf_bytes


def qa_system_prompt(round_name: str) -> str:
    """Base system prompt for Q&A with the required format."""
    return f"""
You are an expert Mechanical Engineering interview coach.

Round / section: {round_name}.

Your job:
- Generate ONLY theoretical interview questions (no coding, no implementation details).
- Cover from simple / basic level to moderately advanced level.
- Use clear and easy English.
- Make the content suitable for a Mechanical Engineering student / fresher.

Strict output format for EVERY item:
Q: **Question text here?**        <-- question must be bold using Markdown
A: Short, simple, interview-style answer (3–6 lines).
F: One relevant formula / tiny numerical example / key point.
   If there is no natural formula, write: F: —.

- Each Q/A/F block must be separated by exactly ONE blank line.
- Do NOT number the questions.
"""


# ------------------------ SESSION STATE ------------------------ #

for key in [
    "resume_text",
    "resume_round_qa",
    "tech_round_qa",
    "hr_round_qa",
]:
    if key not in st.session_state:
        st.session_state[key] = ""


# --------------------------- UI START -------------------------- #

st.title("🧠 Mechanical Interview Q&A Assistant")
st.write(
    "Automatically generate interview **questions** + **simple answers** for "
    "Mechanical Engineering roles. All questions follow the format `Q / A / F`."
)

st.markdown("---")

# ======================= 1. Upload resume ======================= #

st.header("1️⃣ Upload your resume")

uploaded_resume = st.file_uploader(
    "Upload your resume (PDF, DOCX or TXT)",
    type=["pdf", "docx", "txt"],
    help="Resume will be used only to generate interview questions."
)

if uploaded_resume is not None:
    st.session_state.resume_text = extract_text_from_resume(uploaded_resume)
    st.success("Resume uploaded and text extracted successfully (for Q&A generation).")
else:
    st.info("Please upload your resume to enable resume-based questions.")

st.markdown("---")

# ================== 2. Company & role details =================== #

st.header("2️⃣ Company & role details")

col1, col2 = st.columns(2)
with col1:
    company_name = st.text_input("Company name", placeholder="Example: Medha Servo Drives")
    role_name = st.text_input("Target role", placeholder="Example: Graduate Engineer Trainee (Mechanical)")
with col2:
    company_domain = st.text_input(
        "Domain / department",
        placeholder="Example: R&D, Design, Production, Quality, Maintenance"
    )
    location = st.text_input("Location (optional)", placeholder="Example: Hyderabad")

process_text = st.text_area(
    "Company process / technologies / job description (optional)",
    placeholder=(
        "Example:\n"
        "- Written test on basics of Mechanical + aptitude\n"
        "- Technical interview on design, thermodynamics, SOM, TOM\n"
        "- HR round about relocation, strengths, teamwork\n"
        "- Uses tools: AutoCAD, SolidWorks, Ansys etc."
    ),
    height=150
)

st.markdown("---")

# ========== 3. Resume-based interview questions & answers ========= #

st.header("3️⃣ Resume-based interview questions")

num_resume_q = st.slider(
    "Number of resume-based Q&A (basic → advanced)",
    min_value=5,
    max_value=50,
    value=15,
    step=5,
)

if st.button("Generate resume-based Q&A"):
    if not st.session_state.resume_text.strip():
        st.warning("Please upload your resume first.")
    else:
        system_prompt = qa_system_prompt("Resume based interview")
        user_prompt = f"""
Here is the candidate's resume text:

\"\"\"{st.session_state.resume_text[:6000]}\"\"\"

Generate {num_resume_q} interview Q&A **based ONLY on the resume**.
Follow the required Q/A/F format exactly.
"""
        st.session_state.resume_round_qa = call_groq(system_prompt, user_prompt)

if st.session_state.resume_round_qa:
    st.subheader("Resume-based Q&A")
    st.markdown("Below are the questions generated from your resume:")

    st.text_area(
        "Resume-based Q&A (copy if you want)",
        value=st.session_state.resume_round_qa,
        height=400,
    )

    pdf_bytes = build_pdf(
        st.session_state.resume_round_qa,
        "Resume-based Mechanical Interview Q&A"
    )
    st.download_button(
        "⬇️ Download resume-based Q&A as PDF",
        data=pdf_bytes,
        file_name="resume_round_QA.pdf",
        mime="application/pdf",
    )

st.markdown("---")

# =========== 4. Subject / company-specific technical round ======= #

st.header("4️⃣ Technical round – subject / company knowledge")

subjects = st.text_input(
    "Main subjects for this company & role",
    placeholder="Example: Strength of Materials, Theory of Machines, Thermodynamics, Manufacturing"
)

num_tech_q = st.slider(
    "Number of technical Q&A (basic → advanced)",
    min_value=10,
    max_value=50,
    value=20,
    step=5,
)

if st.button("Generate technical round Q&A"):
    system_prompt = qa_system_prompt("Technical round – company / subject knowledge")

    user_prompt = f"""
Company: {company_name or "N/A"}
Role: {role_name or "N/A"}
Domain / Dept: {company_domain or "N/A"}
Location: {location or "N/A"}

Subjects to focus on: {subjects or "core Mechanical Engineering subjects"}
Company process / technologies / JD notes:
\"\"\"{process_text[:2000]}\"\"\"

Generate {num_tech_q} theoretical interview questions **for this company & role**.
- Start with very basic concept questions.
- Then move slowly to more advanced, but still undergraduate Mechanical level.
- Only theory (definitions, concepts, simple formula-based questions).

Follow the strict Q/A/F format for every item.
"""

    st.session_state.tech_round_qa = call_groq(system_prompt, user_prompt)

if st.session_state.tech_round_qa:
    st.subheader("Technical round Q&A")
    st.text_area(
        "Technical Q&A",
        value=st.session_state.tech_round_qa,
        height=450,
    )

    pdf_bytes = build_pdf(
        st.session_state.tech_round_qa,
        "Technical Round Mechanical Interview Q&A"
    )
    st.download_button(
        "⬇️ Download technical round Q&A as PDF",
        data=pdf_bytes,
        file_name="technical_round_QA.pdf",
        mime="application/pdf",
    )

st.markdown("---")

# ========================= 5. HR round =========================== #

st.header("5️⃣ HR round questions")

num_hr_q = st.slider(
    "Number of HR Q&A",
    min_value=10,
    max_value=50,
    value=20,
    step=5,
)

if st.button("Generate HR round Q&A"):
    system_prompt = qa_system_prompt("HR round – behavioural & general")

    user_prompt = f"""
Generate {num_hr_q} HR round interview questions for:

Company: {company_name or "N/A"}
Role: {role_name or "Mechanical Engineer – Fresher"}

Focus areas:
- Self introduction, strengths, weaknesses
- Teamwork, conflicts, leadership, time management
- Relocation, shift work, long-term goals
- Family background in a simple, respectful way
- Basic questions about why this company and this role

Even though these are HR questions, still follow this format:

Q: **HR question text here?**
A: Polished, professional sample answer (5–8 sentences).
F: Extra note / small tip for the candidate ("F: Tip: Keep answer honest...", etc.)

Use only theory / discussion, do not ask the candidate to perform any task.
"""

    st.session_state.hr_round_qa = call_groq(system_prompt, user_prompt)

if st.session_state.hr_round_qa:
    st.subheader("HR round Q&A")
    st.text_area(
        "HR Q&A",
        value=st.session_state.hr_round_qa,
        height=450,
    )

    pdf_bytes = build_pdf(
        st.session_state.hr_round_qa,
        "HR Round Interview Q&A"
    )
    st.download_button(
        "⬇️ Download HR round Q&A as PDF",
        data=pdf_bytes,
        file_name="hr_round_QA.pdf",
        mime="application/pdf",
    )

st.markdown("---")

st.caption(
    "Tip: You can tweak company details, subjects, and number of questions, "
    "then regenerate and download fresh PDFs for each section."
)
