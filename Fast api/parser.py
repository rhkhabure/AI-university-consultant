import pdfplumber
import re
import pandas as pd

# Map question prompts to categories
question_map = {
    "enjoyed most": "Strengths",
    "didn't like": "Weaknesses",
    "improve": "Suggestions",
    "feedback on assignments": "Feedback Evaluation",
    "course text": "Course Text",
    "materials or resources": "Resources",
    "overall evaluation": "Overall"
}

# Regex patterns
section_header_pattern = re.compile(r"\(([A-Z]{3,}\d{3,}) \(UG\d+\)\)\s*Section:\s*([A-Z])", re.IGNORECASE)
instructor_pattern = re.compile(r"Instructor:\s*(.+)", re.IGNORECASE)

# Prompt fragments to exclude
prompt_patterns = [
    re.compile(r"your lecturer would like to know", re.IGNORECASE),
    re.compile(r"aspects of his/her teaching", re.IGNORECASE),
    re.compile(r"specific things you believe", re.IGNORECASE),
    re.compile(r"and why", re.IGNORECASE),
    re.compile(r"comments$", re.IGNORECASE),
    re.compile(r"comment on your evaluation", re.IGNORECASE),
    re.compile(r"explain your evaluation", re.IGNORECASE),
    re.compile(r"what other materials", re.IGNORECASE),
    re.compile(r"my overall evaluation", re.IGNORECASE),
    re.compile(r"per week\?", re.IGNORECASE),
    re.compile(r"should be added to support your learning\?", re.IGNORECASE),
    re.compile(r"improve his/her teaching in this course\.", re.IGNORECASE),
    re.compile(r"hours or by appointment", re.IGNORECASE),
    re.compile(r"satisfact below dept all", re.IGNORECASE),
]

# Table and header noise to exclude
noise_patterns = [
    re.compile(r"Course Evaluation Section Report", re.IGNORECASE),
    re.compile(r"Average|Mean|Dept Mean|All College", re.IGNORECASE),
    re.compile(r"STUDENT SELF EVALUATION", re.IGNORECASE),
    re.compile(r"STUDENT SELF EVAL 2", re.IGNORECASE),
    re.compile(r"STUDENT SELF EVAL 3", re.IGNORECASE),
    re.compile(r"15\+\s*12-14|9-11|7-8|4-6|1-3", re.IGNORECASE),
    re.compile(r"COURSE EVALUATION", re.IGNORECASE),
]

# Known atomic responses
atomic_responses = {"n/a", "na", "none", "nil", "ok", "good", "fair", "excellent", "poor"}

def repair_broken_words(text):
    text = re.sub(r'\b(?:[A-Za-z]\s+){2,}[A-Za-z]\b',
                  lambda m: m.group(0).replace(" ", ""), text)
    text = text.replace("D is cuss ion", "Discussion")
    return text

def clean_line(line):
    line = re.sub(r"\s+", " ", line).strip()
    line = repair_broken_words(line)
    return line

def is_noise(line):
    return any(p.search(line) for p in noise_patterns)

def is_prompt(line):
    return any(p.search(line) for p in prompt_patterns)

def looks_like_table(line):
    if "%" in line:
        return True
    if len(re.findall(r"\d+", line)) >= 2:
        return True
    return False

def flush_atomic_or_comment(candidate, records, current_course, current_section, current_instructor, current_type):
    candidate = candidate.strip()
    if not candidate or candidate in {".", ".."}:
        return  # Skip empty or punctuation-only comments

    tokens = candidate.split()
    buffer_tokens = []

    for tok in tokens:
        if tok.lower() in atomic_responses:
            if buffer_tokens:
                comment = " ".join(buffer_tokens)
                records.append({
                    "Course Code": current_course,
                    "Section Code": current_section,
                    "Instructor": current_instructor,
                    "Comment Type": current_type,
                    "Comment Text": comment
                })
                print(f"Added comment: {comment}")
                buffer_tokens = []
            records.append({
                "Course Code": current_course,
                "Section Code": current_section,
                "Instructor": current_instructor,
                "Comment Type": current_type,
                "Comment Text": tok
            })
            print(f"Added atomic: {tok}")
        else:
            buffer_tokens.append(tok)

    if buffer_tokens:
        comment = " ".join(buffer_tokens)
        records.append({
            "Course Code": current_course,
            "Section Code": current_section,
            "Instructor": current_instructor,
            "Comment Type": current_type,
            "Comment Text": comment
        })
        print(f"Added comment: {comment}")

def parse_pdf(pdf_path):
    records = []
    current_course = current_section = current_instructor = current_type = None
    buffer = ""

    print(f"Opened PDF: {pdf_path}")
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if not text:
                continue
            lines = text.split("\n")
            print(f"Processing page {page_num}, extracted {len(lines)} lines")
            for raw_line in lines:
                line = clean_line(raw_line)
                if not line:
                    continue

                cs_match = section_header_pattern.search(line)
                if cs_match:
                    current_course, current_section = cs_match.groups()
                    continue

                instr_match = instructor_pattern.search(line)
                if instr_match:
                    current_instructor = re.sub(r"Summer Semester.*", "", instr_match.group(1)).strip()
                    continue

                for key, label in question_map.items():
                    if key in line.lower():
                        current_type = label
                        buffer = ""
                        break

                if is_prompt(line) or is_noise(line) or looks_like_table(line):
                    buffer = ""
                    continue

                if line.lower() in atomic_responses:
                    flush_atomic_or_comment(line, records, current_course, current_section, current_instructor, current_type)
                    buffer = ""
                    continue

                buffer += " " + line
                if re.search(r"[.?!]$", line):
                    candidate = buffer.strip()
                    buffer = ""
                    if current_course and current_section and current_instructor and current_type:
                        flush_atomic_or_comment(candidate, records, current_course, current_section, current_instructor, current_type)

    print(f"Parsed {len(records)} comments")
    return records