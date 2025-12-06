import os
from io import StringIO

import streamlit as st
from groq import Groq

from PyPDF2 import PdfReader
import docx


# ---------------------- CONFIG ---------------------- #

# Groq client – set GROQ_API_KEY in environment / Streamlit secrets
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# CHANGE model name if you get model_decommissioned error
MODEL_NAME = "llama3-8b-8192"   # or any latest Groq chat model you have


SYSTEM_PROMPT = """
You are a Mechanical Engineering Interview Assistant.

Goal:
- Generate interview QUESTIONS and ANSWERS for mechanical engineering roles.
- Levels: basic, intermediate, advanced.
- For technical topics, include:
  - Relevant formulas (nicely written, e.g., σ = F/A)
  - Short, simple numerical examples where appropriate.
- Use clear, simple English – like a well-prepared fresher speaking in an interview.
- Put answer immediately after each question in Q&A format.

Formatting rules:
- Number each question.
- For each question:
  Q: <question text>
  A: <answer text>
- Break long answers into short paragraphs or bullet points.
"""


# ---------------------- HELPERS ---------------------- #

def call_llm(user_prompt: str) -> str:
    """Call Groq LLM and return text."""
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=4096,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error while calling Groq API:\n{e}"


def read_resume_file(uploaded_file) -> str:
    """Extract text from PDF / DOCX / TXT."""
    if uploaded_file is None:
        return ""

    name = uploaded_file.name.lower()

    try:
        if name.endswith(".pdf"):
            reader = PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text

        elif name.endswith(".docx"):
            doc = docx.Document(uploaded_file)
            return "\n".join([para.text for para in doc.paragraphs])

        else:  # txt or others – treat as text
            return uploaded_file.read().decode("utf-8", errors="ignore")

    except Exception as e:
        return f"[ERROR READING RESUME: {e}]"


def add_to_session(key: str, content: str):
    if "sections" not in st.session_state:
        st.session_state["sections"] = {}
    st.session_state["sections"][key] = content


def get_all_qa_text() -> str:
    if "sections" not in st.session_state:
        return ""
    out = []
    for sec_name, text in st.session_state["sections"].items():
        out.append(f"===== {sec_name} =====\n\n{text}\n")
    return "\n\n".join(out)


# ---------------------- UI ---------------------- #

st.set_page_config(
    page_title="Mechanical Interview Q&A Assistant",
    layout="wide",
)

st.title("🧠 Mechanical Interview Q&A Assistant")
st.write(
    "Automatically generate mechanical engineering interview **questions + simple answers** "
    "from your **resume, company details, technical subjects and HR round**."
)

st.markdown("---")

# ========== SECTION 1 – Upload Resume ==========
st.header("1️⃣ Upload your resume")

resume_file = st.file_uploader(
    "Upload your resume (PDF, DOCX or TXT)",
    type=["pdf", "docx", "txt"],
)

resume_text = ""
if resume_file is not None:
    resume_text = read_resume_file(resume_file)
    if resume_text.startswith("[ERROR"):
        st.error(resume_text)
        resume_text = ""
    else:
        st.success("✅ Resume uploaded and processed successfully.")
        with st.expander("🔍 Preview extracted resume text"):
            st.text_area("Extracted text", resume_text, height=200)


# ========== SECTION 2 – Company & Role Details ==========
st.header("2️⃣ Company & role details")

col1, col2 = st.columns(2)
with col1:
    company_name = st.text_input("Company name", placeholder="Example: Medha Servo Drives Pvt Ltd")
    location = st.text_input("Location (optional)", placeholder="Hyderabad, Pune, etc.")
with col2:
    role_title = st.text_input("Role / Position", placeholder="Example: Graduate Engineer Trainee (R&D)")
    domain = st.text_input("Domain / Department", placeholder="Design, Production, R&D, Quality, etc.")

job_description = st.text_area(
    "Paste important points from Job Description (JD) (optional)",
    placeholder="Tools, skills, responsibilities from the JD...",
)

st.markdown("---")


# Helper: build context string for prompts
def build_context():
    parts = []
    if company_name:
        parts.append(f"Company: {company_name}")
    if role_title:
        parts.append(f"Role: {role_title}")
    if location:
        parts.append(f"Location: {location}")
    if domain:
        parts.append(f"Domain: {domain}")
    if job_description:
        parts.append(f"Job Description:\n{job_description}")
    if resume_text:
        parts.append(f"Candidate Resume:\n{resume_text}")
    return "\n\n".join(parts)


context_text = build_context()


# ========== SECTION 3 – Resume-based Q&A ==========
st.header("3️⃣ Resume-based interview questions")

st.write(
    "These questions focus on your **projects, skills, internships and strengths** written in your resume."
)

num_resume_q = st.slider("Number of resume-based Q&A", 5, 20, 10)

if st.button("Generate resume-based Q&A"):
    if not resume_text:
        st.warning("Please upload your resume first.")
    else:
        with st.spinner("Generating resume-based questions and answers..."):
            user_prompt = f"""
Use the following candidate information and resume to generate INTERVIEW Q&A.

Context:
{context_text}

Task:
- Create about {num_resume_q} interview questions **strictly based on the resume**.
- Cover: projects, internships, tools, achievements, strengths, soft skills.
- Start from basic questions, then go to more detailed / deeper questions.
- For each question, give a strong sample answer suitable for a fresher.

Remember format:
1.
Q: ...
A: ...
"""
            resume_qa = call_llm(user_prompt)
        st.subheader("📄 Resume-based Q&A")
        st.markdown(resume_qa)
        add_to_session("Resume-based Q&A", resume_qa)

st.markdown("---")


# ========== SECTION 4 – Technical / Subject Q&A ==========
st.header("4️⃣ Technical questions – subject knowledge related to company")

st.write(
    "These questions check your **mechanical subject knowledge** relevant to the role / company.\n"
    "Technical level should go from **basic → advanced**, with formulas and small examples."
)

subjects = st.multiselect(
    "Select subjects related to this role",
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
        "Mechatronics / Controls",
    ],
    default=["Strength of Materials (SOM)", "Manufacturing / Production"],
)

num_tech_q = st.slider("Number of technical Q&A", 10, 30, 20)

if st.button("Generate technical Q&A"):
    if not subjects:
        st.warning("Please select at least one subject.")
    else:
        subjects_text = ", ".join(subjects)
        with st.spinner("Generating technical questions and answers..."):
            user_prompt = f"""
Context:
{context_text}

Subjects to focus on: {subjects_text}

Task:
- Generate around {num_tech_q} **technical** interview questions for a mechanical engineering fresher.
- Questions should be from **basic level to advanced level**.
- Strong focus on topics that are relevant for company/role/domain above.

For each technical question:
- Provide a clear conceptual answer.
- If any formula is relevant, write it clearly (e.g., σ = F / A).
- Add a very small numerical example or simple real-life example wherever helpful.
- Keep explanations short and easy to understand.

Use strict Q&A format:
1.
Q: ...
A: ...
"""
            tech_qa = call_llm(user_prompt)
        st.subheader("🔧 Technical Q&A")
        st.markdown(tech_qa)
        add_to_session("Technical Q&A", tech_qa)

st.markdown("---")


# ========== SECTION 5 – HR round Q&A ==========
st.header("5️⃣ HR round questions")

st.write(
    "These are **HR / behavioural questions** – about your goals, teamwork, family background, "
    "strengths & weaknesses, relocation, etc."
)

num_hr_q = st.slider("Number of HR Q&A", 5, 20, 15)

if st.button("Generate HR round Q&A"):
    with st.spinner("Generating HR round questions and answers..."):
        user_prompt = f"""
Context:
Company: {company_name or "NA"}
Role: {role_title or "Mechanical Engineer - Fresher"}

Task:
- Generate about {num_hr_q} HR / behavioural interview questions for a fresher.
- Include topics such as:
  - Self introduction, family background
  - Strengths & weaknesses
  - Teamwork, leadership, handling pressure
  - Relocation, shifts, long-term goals
  - Why this company? Why this role?
- Answers should sound polite, confident and honest.

Format (for each):
1.
Q: ...
A: ...
"""
        hr_qa = call_llm(user_prompt)
    st.subheader("🧑‍💼 HR round Q&A")
    st.markdown(hr_qa)
    add_to_session("HR Q&A", hr_qa)

st.markdown("---")


# ========== DOWNLOAD ALL Q&A ==========
st.header("⬇️ Download all generated Q&A")

all_qa_text = get_all_qa_text()

if not all_qa_text:
    st.info("Generate some Q&A above. They will appear here for download.")
else:
    st.text_area("Combined Q&A preview", all_qa_text, height=200)
    st.download_button(
        label="Download all Q&A as .txt",
        data=all_qa_text,
        file_name="mechanical_interview_QA.txt",
        mime="text/plain",
    )

st.markdown("---")
st.caption("Tip: Change subjects / company / role and generate again for more practice sets.")
