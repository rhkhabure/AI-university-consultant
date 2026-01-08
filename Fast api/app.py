import streamlit as st
import pandas as pd
import sqlite3
from collections import Counter
import random
from fpdf import FPDF
# Connect to SQLite database
conn = sqlite3.connect("C:/Users/Admin/OneDrive/Documents/Schoolwork/Projects/UNI finals project/Code stuff/faculty_evaluation.db")

st.title("Course Evaluation Parser Demo")
st.write("👋 Streamlit is rendering correctly.")

st.header("Login Portal")

faculty_id = st.text_input("Enter your Faculty ID:")
login_button = st.button("Login")

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Handle login
if login_button and faculty_id:
    query = "SELECT * FROM Faculty WHERE faculty_id = ?"
    faculty = pd.read_sql(query, conn, params=[faculty_id])

    if not faculty.empty:
        st.session_state.logged_in = True
        st.session_state.faculty_id = faculty_id
        st.session_state.full_name = faculty["full_name"].iloc[0]
        st.session_state.role = "faculty"
        st.session_state.school = None

        # Get school for this faculty
        school_query = """
        SELECT DISTINCT c.school
        FROM Courses c
        JOIN Sections s ON c.course_code = s.course_code
        JOIN TeachingAssignments t ON s.section_id = t.section_id
        WHERE t.faculty_id = ?
        """
        school_df = pd.read_sql(school_query, conn, params=[faculty_id])
        if not school_df.empty:
            st.session_state.school = school_df["school"].iloc[0]

        # Check for dean role
        dean_check = pd.read_sql("SELECT * FROM Deans WHERE faculty_id = ?", conn, params=[faculty_id])
        if not dean_check.empty:
            st.session_state.role = "dean"

        # Check for VC role
        if faculty_id == "115885":
            st.session_state.role = "vc"

        st.success(f"Welcome {st.session_state.full_name}")
    else:
        st.error("Invalid Faculty ID")

# Role-based views
if st.session_state.logged_in:
    role = st.session_state.role
    faculty_id = st.session_state.faculty_id
    school = st.session_state.school

    if role == "faculty":
        st.subheader("Your Evaluations")
        query = """
        SELECT e.*, s.course_code, s.section_code, c.course_description, c.school
        FROM Evaluations e
        JOIN Sections s ON e.section_id = s.section_id
        JOIN Courses c ON s.course_code = c.course_code
        JOIN TeachingAssignments t ON e.section_id = t.section_id
        WHERE t.faculty_id = ?
        """
        data = pd.read_sql(query, conn, params=[faculty_id])
        st.dataframe(data)

    elif role == "dean":
        st.subheader(f"School-wide Evaluations for {school}")
        query = """
        SELECT f.full_name, c.course_code, s.section_code, e.mean_score, e.letter_grade
        FROM Evaluations e
        JOIN Sections s ON e.section_id = s.section_id
        JOIN Courses c ON s.course_code = c.course_code
        JOIN TeachingAssignments t ON e.section_id = t.section_id
        JOIN Faculty f ON t.faculty_id = f.faculty_id
        WHERE c.school = ?
        ORDER BY e.mean_score DESC;
        """
        data = pd.read_sql(query, conn, params=[school])
        st.dataframe(data)

    elif role == "vc":
        st.subheader("University-wide Evaluations")

        # VC school filter
        schools = pd.read_sql("SELECT DISTINCT school FROM Courses", conn)["school"].tolist()
        selected_school = st.selectbox("Filter by School", ["All"] + schools)

        query = """
        SELECT f.full_name, c.school, c.course_code, s.section_code, e.mean_score, e.letter_grade
        FROM Evaluations e
        JOIN Sections s ON e.section_id = s.section_id
        JOIN Courses c ON s.course_code = c.course_code
        JOIN TeachingAssignments t ON e.section_id = t.section_id
        JOIN Faculty f ON t.faculty_id = f.faculty_id
        ORDER BY c.school, e.mean_score DESC;
        """
        data = pd.read_sql(query, conn)

        if selected_school != "All":
            data = data[data["school"] == selected_school]

        st.dataframe(data)



# --- AI Consultant Block ---
import re
def classify_intent(question):
    q = question.lower()

    if any(kw in q for kw in ["top", "best", "highest rated", "top performing"]):
        return "ranking_top"
    if any(kw in q for kw in ["lowest", "worst", "bottom", "least performing"]):
        return "ranking_bottom"
    if any(kw in q for kw in ["grade", "grades", "distribution", "who got an e"]):
        return "grade_distribution"
    if any(kw in q for kw in ["trend", "change", "improve", "shift", "progress"]):
        return "trend"
    if any(kw in q for kw in ["compare", "difference", "vs", "variation"]):
        return "compare"
    if any(kw in q for kw in ["summary", "overview", "how did we do"]):
        return "summary"
    
    return "unknown"



@st.cache_data(ttl=60)
def fetch_scope_data(role, faculty_id, school, _conn):
    if role == "faculty":
        q = """
        SELECT e.*, s.course_code, s.section_code, c.course_description, c.school, t.faculty_id, f.full_name
        FROM Evaluations e
        JOIN Sections s ON e.section_id = s.section_id
        JOIN Courses c ON s.course_code = c.course_code
        JOIN TeachingAssignments t ON e.section_id = t.section_id
        JOIN Faculty f ON t.faculty_id = f.faculty_id
        WHERE t.faculty_id = ?
        """
        return pd.read_sql(q, _conn, params=[faculty_id])
    elif role == "dean":
        q = """
        SELECT e.*, s.course_code, s.section_code, c.course_description, c.school, t.faculty_id, f.full_name
        FROM Evaluations e
        JOIN Sections s ON e.section_id = s.section_id
        JOIN Courses c ON s.course_code = c.course_code
        JOIN TeachingAssignments t ON e.section_id = t.section_id
        JOIN Faculty f ON t.faculty_id = f.faculty_id
        WHERE c.school = ?
        """
        return pd.read_sql(q, _conn, params=[school])
    else:  # vc
        q = """
        SELECT e.*, s.course_code, s.section_code, c.course_description, c.school, t.faculty_id, f.full_name
        FROM Evaluations e
        JOIN Sections s ON e.section_id = s.section_id
        JOIN Courses c ON s.course_code = c.course_code
        JOIN TeachingAssignments t ON e.section_id = t.section_id
        JOIN Faculty f ON t.faculty_id = f.faculty_id
        """
        return pd.read_sql(q, _conn)

def answer_question(question, df_scope):
    intent = classify_intent(question)

    if intent == "ranking_top":
        return "Top ranking not implemented in this demo."
    elif intent == "ranking_bottom":
        return "Bottom ranking not implemented in this demo."
    elif intent == "grade_distribution":
        return "Grade distribution not implemented in this demo."
    elif intent == "trend":
        return "Trend analysis not implemented in this demo."
    elif intent == "compare":
        return "Comparison not implemented in this demo."
    elif intent == "summary":
        return "Summary not implemented in this demo."
    else:
        # Fallback: scoped summary with useful insights
        by_lect = (
            df_f.groupby("full_name")["mean_score"]
        .agg(["count", "mean"])
        .sort_values(by="mean", ascending=False)
        .reset_index()
        .head(5)
        )
        lines = ["### Scoped summary (top lecturers by mean score)"]
        for _, r in by_lect.iterrows():
            lines.append(f"- {r['full_name']}: {round(r['mean'], 2)} (n={int(r['count'])})")

        grade_counts = df_f["letter_grade"].value_counts().sort_index()
        lines.append("\n### Grade distribution")
        for grade, count in grade_counts.items():
            lines.append(f"- {grade}: {count}")

        lines.append(f"\n⚠️ I couldn’t interpret the question directly, so here’s a scoped summary instead.")
        lines.append(f"Filters: {', '.join(meta) if meta else 'none'} | Rows: {len(df_f)}")
        return "\n".join(lines)




# --- UI block ---
st.divider()
st.subheader("🧠 AI consultant (beta)")
if st.session_state.get("logged_in", False):
    role = st.session_state.role
    faculty_id = st.session_state.faculty_id
    school = st.session_state.school

    df_scope = fetch_scope_data(role, faculty_id, school, conn)

    question = st.text_input("Ask a question (e.g., 'Top lecturers', 'Compare sections: IST3005', 'Trend for MKT3010')")
    if st.button("Answer"):
        resp = answer_question(question, df_scope)
        st.markdown(resp)
else:
    st.info("Log in to ask scoped questions (faculty, dean, or VC).")






# File uploader
uploaded_file = st.file_uploader("Upload a course evaluation PDF", type=["pdf"])

# Try to import real parser
try:
    from parser import parse_pdf
    st.write("✅ Real parser imported successfully.")
except Exception as e:
    st.error(f"❌ Real parser import failed: {e}")
    def parse_pdf(pdf_path):
        return []

# --- Micro report generator ---
def generate_micro_report_md(df_course, quote_bank):
    course_code = df_course['Course Code'].iloc[0]
    section_code = df_course['Section Code'].iloc[0]
    lecturer_name = df_course['Instructor'].iloc[0]
    semester = df_course['Semester'].iloc[0] if 'Semester' in df_course else "Semester not captured"
    responses = len(df_course)

    total_comments = sum(sum(len(v) for v in sentiments.values()) for sentiments in quote_bank.values()) or max(responses, 1)
    pos_total = sum(len(sentiments.get("Positive", [])) for sentiments in quote_bank.values())
    neg_total = sum(len(sentiments.get("Negative", [])) for sentiments in quote_bank.values())
    neu_total = sum(len(sentiments.get("Neutral", [])) for sentiments in quote_bank.values())

    pos_pct = round((pos_total / total_comments) * 100, 1)
    neu_pct = round((neu_total / total_comments) * 100, 1)
    neg_pct = round((neg_total / total_comments) * 100, 1)

    praises, suggestions = [], []
    for sentiments in quote_bank.values():
        praises.extend([q for _, q in sentiments.get("Positive", [])])
        suggestions.extend([q for _, q in sentiments.get("Neutral", [])])

    praise_counts = Counter(praises)
    suggestion_counts = Counter(suggestions)
    top_praises = praise_counts.most_common(3)
    top_suggestions = suggestion_counts.most_common(3)

    lines = []
    lines.append(f"## 📄 Lecturer Feedback Report — Micro Level")
    lines.append(f"**Course:** {course_code} – Section {section_code}")
    lines.append(f"**Lecturer:** {lecturer_name}")
    lines.append(f"**Semester:** {semester}")
    lines.append(f"**Responses:** {responses} students\n")
    lines.append(f"### 📊 Overall Sentiment")
    lines.append(f"- Positive: **{pos_pct}%**")
    lines.append(f"- Neutral: **{neu_pct}%**")
    lines.append(f"- Negative: **{neg_pct}%**\n")

    lines.append("### 🌟 What Students Consistently Praised")
    if top_praises:
        for theme, count in top_praises:
            pct = round((count / total_comments) * 100, 1)
            lines.append(f"- {theme} — {pct}% of positive comments")
        lines.append(f"\n🗣️ Example student voice: “{random.choice(praises)}”")
    else:
        lines.append("- No explicit praise captured.")

    lines.append("\n### 💡 Common Suggestions for Improvement")
    if top_suggestions:
        for theme, count in top_suggestions:
            pct = round((count / total_comments) * 100, 1)
            lines.append(f"- {theme} — {pct}% of suggestions")
        lines.append(f"\n🗣️ Example student voice: “{random.choice(suggestions)}”")
    else:
        lines.append("- No explicit suggestions captured.")

    lines.append("\n### ✅ Recommended Actions")
    if top_suggestions:
        for theme, _ in top_suggestions:
            lines.append(f"- {theme}")
    else:
        lines.append("- No actions inferred due to limited suggestions.")

    lines.append("\n### 🧾 AI Summary")
    lines.append("“Students value your delivery and clarity. The main opportunities are adding practical elements, "
                 "adjusting pacing, and posting materials earlier. Addressing these should strengthen engagement and satisfaction.”")

    return "\n".join(lines)

# --- Quote bank builder ---
def build_quote_bank(df):
    quote_bank = {}
    for _, row in df.iterrows():
        aspect = "General sentiment"
        text = row["Comment Text"].strip().lower()
        sentiment = "Neutral"
        if text in {"good", "great", "excellent", "well done", "amazing"}:
            sentiment = "Positive"
        elif text in {"poor", "bad", "confusing", "unclear"}:
            sentiment = "Negative"
        if aspect not in quote_bank:
            quote_bank[aspect] = {"Positive": [], "Neutral": [], "Negative": []}
        quote_bank[aspect][sentiment].append((None, row["Comment Text"].strip()))
    return quote_bank

# --- PDF export with character fix ---
def export_report_to_pdf(report_md, filename="micro_report.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Replace unsupported characters
    safe_text = (
        report_md.replace("—", "-")   # em dash
                 .replace("–", "-")   # en dash
                 .replace("“", '"')   # left quote
                 .replace("”", '"')   # right quote
                 .replace("’", "'")   # apostrophe
                 .replace("•", "-")   # bullet
                 .replace("…", "...") # ellipsis
                 .encode("ascii", "ignore")  # remove emojis and non-ascii
                 .decode("ascii")


    )

    for line in safe_text.split("\n"):
        pdf.multi_cell(0, 10, line)
    return pdf.output(dest="S").encode("latin-1")

# --- Main app logic ---
if uploaded_file is not None:
    st.write("✅ File uploaded successfully!")
    temp_path = "uploaded.pdf"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())
    st.write("📂 File saved locally.")

    try:
        st.write("🔄 Running parser...")
        comments = parse_pdf(temp_path)
        st.write(f"✅ Parser returned {len(comments)} comments.")

        if comments:
            topics_df = pd.DataFrame(comments)

            instructors = sorted(topics_df["Instructor"].dropna().unique())
            courses = sorted(topics_df["Course Code"].dropna().unique())

            selected_instructor = st.selectbox("🎓 Filter by Instructor", ["All"] + instructors)
            selected_course = st.selectbox(" Filter by Course Code", ["All"] + courses)

            filtered_df = topics_df.copy()
            if selected_instructor != "All":
                filtered_df = filtered_df[filtered_df["Instructor"] == selected_instructor]
            if selected_course != "All":
                filtered_df = filtered_df[filtered_df["Course Code"] == selected_course]

            st.subheader("📝 Filtered Parsed Comments")
            st.dataframe(filtered_df.head(50))

            csv = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download filtered comments as CSV", csv, "parsed_comments.csv", "text/csv")

            summary = (
                filtered_df.groupby(["Instructor", "Comment Type"])
                .size()
                .unstack(fill_value=0)
                .reset_index()
            )
            summary["Total"] = summary.drop(columns=["Instructor"]).sum(axis=1)
            totals = summary.drop(columns=["Instructor"]).sum()
            totals["Instructor"] = "All Instructors"
            summary = pd.concat([summary, pd.DataFrame([totals])], ignore_index=True)
            st.subheader("📊 Summary of Comments per Instructor")
            st.dataframe(summary)

            # --- Micro report ---
            st.subheader("📄 Micro-Level Report")
            if not filtered_df.empty:
                quote_bank = build_quote_bank(filtered_df)
                report_md = generate_micro_report_md(filtered_df, quote_bank)
                st.markdown(report_md)

                # PDF download button
                pdf_bytes = export_report_to_pdf(report_md)
                st.download_button(
                    label="⬇️ Download Micro-Level Report as PDF",
                    data=pdf_bytes,
                    file_name="micro_report.pdf",
                    mime="application/pdf",
                )

        else:
            st.warning("⚠️ Parser ran but returned no comments.")

    except Exception as e:
        st.error(f"❌ Parser execution failed: {e}")


if st.session_state.logged_in:
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.faculty_id = None
        st.session_state.full_name = None
        st.session_state.role = None
        st.session_state.school = None
        st.success("You have been logged out.")