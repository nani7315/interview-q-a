import os
from groq import Groq
import streamlit as st

# -------------------- CONFIG -------------------- #

# Groq model name
GROQ_MODEL = "llama3-8b-8192"   # safe, still supported model

SYSTEM_PROMPT = """
You are an Interview Preparation Assistant for Mechanical Engineering students.

Your responsibilities:
- Generate interview questions and give simple sample answers.
- Cover both HR and core Mechanical Engineering technical questions.
- Use easy English, like a well-prepared fresher in an interview.
- For HR questions: 4–6 sentences, positive & professional.
- For Technical questions: short exam-style explanation + 1 simple example.
- Keep answers suitable for freshers (campus placement level).
"""

# Create Groq client (expects GROQ_API_KEY in environment)
def get_client():
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return None, "GROQ_API_KEY environment variable is not set. " \
                    "Please add it in Streamlit Cloud → Secrets as GROQ_API_KEY."
    try:
        client = Groq(api_key=api_key)
        return client, None
    except Exception as e:
        return None, f"Error while creating Groq client: {e}"


def generate_qa(role, q_type, subjects_text, count):
    """
    Ask Groq to generate questions + answers together.
    Format: numbered list with Q and A.
    """
    client, err = get_client()
    if err:
        return f"⚠️ {err}"

    user_prompt = f"""
Role: {role}
Question type: {q_type}
Mechanical subjects focus: {subjects_text}

Generate {count} interview questions WITH simple answers.

Format **exactly** like this:
1. Q: <question text>
   A: <simple answer in 4–6 sentences>

2. Q: ...
   A: ...
    """

    try:
        chat_completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error while calling Groq API:\n\n{e}"


# -------------------- STREAMLIT UI -------------------- #

def main():
    st.set_page_config(
        page_title="Mechanical Interview Q&A Assistant",
        page_icon="🤖",
        layout="wide",
    )

    st.title("🤖 Mechanical Interview Q&A Assistant")
    st.caption("Automatically generate interview **questions + simple answers** for Mechanical Engineering roles.")

    # -------- Sidebar settings -------- #
    st.sidebar.header("⚙️ Settings")

    role = st.sidebar.text_input(
        "Target role",
        value="Mechanical Engineer - Fresher",
        help="Example: Design Engineer, Production Engineer, Maintenance Engineer, etc.",
    )

    q_type = st.sidebar.selectbox(
        "Question type",
        options=["HR", "Technical", "Both"],
    )

    tech_subjects = st.sidebar.multiselect(
        "Technical subjects (for Technical / Both)",
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

    subjects_text = ", ".join(tech_subjects) if tech_subjects else "General Mechanical Engineering topics"

    num_questions = st.sidebar.slider(
        "Number of questions",
        min_value=3,
        max_value=15,
        value=8,
    )

    st.sidebar.info("Click **Generate Q&A** to get questions with ready-made simple answers.")

    # -------- Main area -------- #
    st.markdown("### 1️⃣ Generate Questions **with Answers**")

    if st.button("Generate Q&A"):
        with st.spinner("Generating interview questions and answers..."):
            qa_text = generate_qa(role, q_type, subjects_text, num_questions)

        st.markdown("#### Generated Q&A")
        st.markdown(
            qa_text if qa_text.startswith("⚠️") else "```text\n" + qa_text + "\n```"
        )
    else:
        st.write("Set your options on the left and press **Generate Q&A** to start.")

    st.markdown("---")
    st.caption("Tip: Change role / question type / subjects and generate again for more practice sets.")


if __name__ == "__main__":
    main()
