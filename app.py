import os
import json
import streamlit as st
from groq import Groq

# ------------------  CONFIG  ------------------ #

MODEL_NAME = "llama-3.1-8b-instant"   # Current Groq fast model

SYSTEM_PROMPT = """
You are a Mechanical Engineering Interview Q&A generator.

Your job:
- Generate interview QUESTIONS with simple, professional sample ANSWERS.
- Audience: Mechanical Engineering students / freshers.
- Cover HR and/or Technical questions depending on user choice.
- For technical questions, stay inside Mechanical topics like SOM, TOM, Thermal, FM,
  Manufacturing, Design, etc.
- Use very simple English.
- Answers should sound like a well-prepared fresher speaking in an interview.

OUTPUT FORMAT (IMPORTANT):
Return ONLY JSON, no extra text.
It must be a list of objects like:
[
  {
    "question": "Question text here?",
    "answer": "Answer text here."
  },
  ...
]
"""


def get_client() -> Groq:
    """Create a Groq client using the GROQ_API_KEY env variable."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable is not set. "
            "Set it in your system or in Streamlit Cloud → App settings → Secrets."
        )
    return Groq(api_key=api_key)


def generate_qa(role: str, q_type: str, subjects_text: str, count: int):
    """
    Ask Groq to generate `count` Q&A pairs and return them as a Python list.
    """

    user_prompt = f"""
I am preparing for an interview for the role: {role}.

Question type: {q_type}
- HR  -> only HR / personal / behavioral questions.
- Technical -> only core Mechanical Engineering technical questions.
- Both -> mix of HR and Technical questions.

Technical subjects focus: {subjects_text}

Generate exactly {count} interview questions.
For EACH question, also generate a simple, clear sample answer.

Requirements:
- Answers short and clean (3–6 sentences).
- Use very simple English.
- Suitable for a Mechanical Engineering fresher.
- Return ONLY valid JSON as described in the system prompt.
"""

    client = get_client()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0.4,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_text = response.choices[0].message.content.strip()

    # The model may wrap JSON in ```json ... ``` – clean that.
    if "```" in raw_text:
        parts = raw_text.split("```")
        # Try to find the json block
        for p in parts:
            if "{" in p or "[" in p:
                raw_text = p.strip()
                break

    try:
        qa_list = json.loads(raw_text)
    except json.JSONDecodeError:
        # Fallback: wrap into a single item if JSON fails
        qa_list = [{"question": "Parsing error", "answer": raw_text}]

    # Make sure it's a list
    if isinstance(qa_list, dict):
        qa_list = [qa_list]

    return qa_list


# ------------------  STREAMLIT APP  ------------------ #

st.set_page_config(
    page_title="Mechanical Interview Q&A Assistant",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Mechanical Interview Q&A Assistant")
st.write(
    "Automatically generate interview **questions + simple answers** "
    "for Mechanical Engineering roles."
)

# -------- Sidebar settings -------- #
st.sidebar.header("Settings")

role = st.sidebar.text_input(
    "Target Role",
    value="Mechanical Engineer - Fresher",
)

q_type = st.sidebar.selectbox(
    "Question Type",
    options=["HR", "Technical", "Both"],
)

tech_subjects = st.sidebar.multiselect(
    "Technical Subjects (used when Technical/Both)",
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
subjects_text = ", ".join(tech_subjects) if tech_subjects else "General Mechanical topics"

count = st.sidebar.slider("Number of Q&A pairs", min_value=3, max_value=15, value=8)

st.sidebar.info("Click **Generate Q&A** to create questions with answers.")

# -------- Main button -------- #
st.markdown("### 1️⃣ Generate Questions with Answers")

if st.button("Generate Q&A"):
    try:
        with st.spinner("Talking to Groq and generating Q&A..."):
            qa_list = generate_qa(role, q_type, subjects_text, count)

        st.markdown("### Generated Q&A")
        if not qa_list:
            st.warning("No Q&A generated. Try again.")
        else:
            for idx, item in enumerate(qa_list, start=1):
                question = item.get("question", "").strip()
                answer = item.get("answer", "").strip()

                with st.expander(f"Q{idx}. {question}"):
                    st.write(answer)

    except Exception as e:
        st.error(f"⚠️ Error while calling Groq API:\n\n{e}")

st.markdown("---")
st.caption(
    "Tip: Change role / question type / subjects in the sidebar and click "
    "**Generate Q&A** again for more practice sets."
)
