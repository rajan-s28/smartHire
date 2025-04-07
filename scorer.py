"""
This python module is a Streamlit-based application that evaluates resumes against job descriptions using 
Google Gemini AI. It supports uploading PDF and DOCX files, extracting text, scoring candidates across multiple 
criteria, and displaying results in an interactive interface. Shortlisted candidates can be downloaded 
or scheduled for further steps through an integrated scheduling module.
"""

import os
import streamlit as st
import PyPDF2
import docx
import google.generativeai as genai
import json, re
import pandas as pd
import jobDescription, schedule

gemini_api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=gemini_api_key)


def parse_gemini_json_response(response_text):
    """
    Extracts and parses JSON data from Gemini's raw response text.

    Args:
        response_text (str): Raw text response from Gemini.

    Returns:
        dict: Parsed JSON data or error message.
    """
    try:
        json_text = re.search(r"\{.*\}", response_text, re.DOTALL).group()
        return json.loads(json_text)
    except Exception as e:
        return {"error": f"Failed to parse JSON: {e}"}

def extract_text_from_pdf(file):
    """
    Extracts text content from a PDF file.

    Args:
        file (UploadedFile): PDF file uploaded via Streamlit.

    Returns:
        str: Extracted text from the PDF.
    """
    pdf_reader = PyPDF2.PdfReader(file)  # Correct: Use PdfReader
    text = ""

    for page in pdf_reader.pages:  # Correct: Iterate over pdf_reader.pages directly
        extracted_text = page.extract_text()
        if extracted_text:  # Ensure we only append valid text
            text += extracted_text + "\n"

    return text

def extract_text_from_docx(file):
    """
    Extracts text content from a DOCX file.

    Args:
        file (UploadedFile): DOCX file uploaded via Streamlit.

    Returns:
        str: Extracted text from the DOCX.
    """
    doc = docx.Document(file)
    text = ""
    for para in doc.paragraphs:
        text += para.text
    return text

def evaluate_resume_to_json(resume_text, job_title):
    """
    Sends resume and job description to Gemini and returns structured JSON response.

    Args:
        resume_text (str): Extracted text content of the resume.
        job_title (str): Selected job title for matching.

    Returns:
        str: Raw JSON-like text response from Gemini.
    """
    jd = updated_jd.get(job_title)

    if not jd:
        return {
            "error": f"No structured job description found for '{job_title}'"
        }

    skills = ', '.join(jd.get('skills', []))
    domains = ', '.join(jd.get('ProjectDomain', []))
    experience = ', '.join(jd.get('Experience', []))
    locations = ', '.join(jd.get('Location', []))
    must_to_have = ', '.join(jd.get('Must to have', []))
    good_to_have = ', '.join(jd.get('Good to have', []))
    candidate_name = resume_text.splitlines()[0]  # Basic assumption

    prompt = f"""
    You are a smart hiring assistant. Evaluate the following resume for the job title '{job_title}' and respond in a strict JSON format.

    Resume:
    {resume_text}

    Job Criteria:
    - Required Skills: {skills}
    - Preferred Project Domains: {domains}
    - Experience Required: {experience}
    - Preferred Locations: {locations}

    Must to have skills:
    - Must to have: {must_to_have}

    Good to have skills:
    - Good to have: {good_to_have}

    NOTE:
    - Calculate the Must to have and Good to have scores separately with a score out of 10.
    - Divide Must to have and Good to have scores by 10 and add to Job Criteria final score to create final score.

    Use this JSON format exactly:

    {{
    "candidate_name": {{
        "name": "{candidate_name}",
        "reason": "N/A"
    }},
    "Skills": {{
        "score": int (0–10),
        "reason": "short explanation"
    }},
    "Project Domain": {{
        "score": int (0–10),
        "reason": "short explanation"
    }},
    "Experience": {{
        "score": int (0–10),
        "reason": "short explanation"
    }},
    "Location": {{
        "score": int (0–10),
        "reason": "short explanation"
    }},
    "Must to have": {{
        "score": int (0–10),
        "reason": "short explanation"
    }},
    "Good to have": {{
        "score": int (0–10),
        "reason": "short explanation"
    }},
    "Final Score": {{
        "score": float (0.0–10.0),
        "reason": "average explanation"
    }},
    "Mobile Number": {{
        "Number": "extracted number or null",
        "reason": "N/A"
    }},
    "Email Address": {{
        "Email": "extracted email or null",
        "reason": "N/A"
    }}
    }}

    Notes:
    - Do not explain outside the JSON.
    - If any value is missing, assume it as 0 or "N/A".
    - Return only the JSON. No prose explanation.
    """

    model = genai.GenerativeModel(model_name='gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text

def upload_files(uploaded_files):
    """
    Parses uploaded resumes and returns a list of filename-text tuples.

    Args:
        uploaded_files (list): List of UploadedFile objects.

    Returns:
        list: List of tuples (filename, resume text).
    """
    resumes_texts = []
    if not uploaded_files:
        return

    for uploaded_file in uploaded_files:
        file_extension = uploaded_file.name.split(".")[-1].lower()
        
        if file_extension in ["pdf", "docx"]:
            if file_extension == "pdf":
                st.write(f"Resume: {uploaded_file.name} (PDF)")
                text = extract_text_from_pdf(uploaded_file)
                resumes_texts.append((uploaded_file.name, text))
            elif file_extension == "docx":
                st.write(f"Resume: {uploaded_file.name} (DOCX)")
                text = extract_text_from_docx(uploaded_file)
                resumes_texts.append((uploaded_file.name, text))
    return resumes_texts

def display_results(results):
    """
    Displays results in a styled DataFrame and enables CSV download of shortlisted candidates.
    It also return passed candidates as dataframe.

    Args:
        results (list): List of resume evaluation dictionary.

    Returns:
        pd.DataFrame: DataFrame of shortlisted candidates.
    """
    df = pd.DataFrame(results)
    
    # Determine "Shortlisted" based on Cutoff Score
    df["Shortlisted"] = df["Final Score"].apply(lambda x: "Yes" if x >= cutoff_score else "No")

    # Filter only passed candidates
    passed_df = df[df["Shortlisted"] == "Yes"]

    # Display results with colored rows
    def highlight_rows(row):
        return ["background-color: #90EE90;" if row["Shortlisted"] == "Yes" else "background-color: #FFB6C1;"] * len(row)

    styled_df = df.style.apply(highlight_rows, axis=1)

    st.subheader("📊 Resume Scoring Summary")
    st.dataframe(styled_df)

    # Generate CSV only for Passed candidates
    if not passed_df.empty:
        csv_passed = passed_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Passed Candidates", data=csv_passed, file_name="passed_candidates.csv", mime="text/csv")
    else:
        st.warning("⚠️ No candidates passed the cutoff score.")
    return passed_df

def score_resumes(analyze_disabled, resumes_texts, job_title):
    """
    Main scoring loop: sends resumes to Gemini and collects parsed scores.

    Args:
        analyze_disabled (bool): Whether the analyze button is disabled.
        resumes_texts (list): List of (filename, text) tuples.
        job_title (str): Selected job title.

    Returns:
        dict: dictionary of structured results according to resumes.
    """
    results = []
    if st.button("📊 Analyze and Score Resumes", disabled=analyze_disabled):
        st.write(f"Analyzing resumes for job title: {job_title}...\n")
        with st.spinner("Wait for it...", show_time=True):
        
            for resume_name, resume_text in resumes_texts:
                st.markdown(f"### 📄 {resume_name}")

                json_response = evaluate_resume_to_json(resume_text, job_title)

                # Step 3: Parse the JSON string
                parsed = parse_gemini_json_response(json_response)

                if "error" in parsed:
                    st.error(f"❌ {parsed['error']}")
                    # st.code(gemini_response, language="text")
                    continue

                # Step 4: Display scores + reasons in 7 columns
                cols = st.columns(7)

                # Inject Custom CSS for Hover Tooltips
                st.markdown(
                    """
                    <style>
                        .tooltip {
                            position: relative;
                            display: inline-block;
                            cursor: pointer;
                            font-size: 14px;
                            margin-top: 5px;
                        }

                        .tooltip .tooltiptext {
                            visibility: hidden;
                            width: 250px;
                            background-color: black;
                            color: #fff;
                            text-align: center;
                            border-radius: 5px;
                            padding: 10px;
                            position: absolute;
                            z-index: 1;
                            bottom: 120%;
                            left: 50%;
                            transform: translateX(-50%);
                            opacity: 0;
                            transition: opacity 0.3s ease-in-out;
                        }

                        .tooltip:hover .tooltiptext {
                            visibility: visible;
                            opacity: 1;
                        }

                        .metric-container {
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                            justify-content: center;
                        }

                    </style>
                    """,
                    unsafe_allow_html=True
                )

                # Iterate over categories and display metrics with hover tooltips
                for i, category in enumerate(["Skills", "Project Domain", "Experience", "Location", "Must to have", "Good to have", "Final Score"]):
                    with cols[i]:
                        # Display the metric
                        st.metric(label=category, value=f"{parsed[category]['score']}/10")

                        # Hover tooltip icon below the score
                        st.markdown(
                            f"""
                            <div class="metric-container">
                                <div class="tooltip">ℹ️
                                    <span class="tooltiptext">{parsed[category]['reason']}</span>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )


                # Step 5: Save to results list for summary table
                results.append({
                    "Candidate Name": parsed["candidate_name"]["name"],
                    "Resume": resume_name,
                    "Skills": parsed["Skills"]["score"],
                    "Skills_Reason": parsed["Skills"]["reason"],
                    "Project Domain": parsed["Project Domain"]["score"],
                    "ProjectDomain_Reason": parsed["Project Domain"]["reason"],
                    "Experience": parsed["Experience"]["score"],
                    "Experience_Reason": parsed["Experience"]["reason"],
                    "Location": parsed["Location"]["score"],
                    "Location_Reason": parsed["Location"]["reason"],
                    "Must to have": parsed["Must to have"]["score"],
                    "Must to have_reason": parsed["Must to have"]["reason"],
                    "Good to have": parsed["Good to have"]["score"],
                    "Good to have_reason": parsed["Good to have"]["reason"],
                    "Final Score": parsed["Final Score"]["score"],
                    "FinalScore_Reason": parsed["Final Score"]["reason"],
                    "Mobile Number": parsed["Mobile Number"]["Number"],
                    "Email Address": parsed["Email Address"]["Email"]
                })
    return results

def get_jd():
    """
    Returns:
        dict: Pre-defined job descriptions for different roles.
    """
    job_descriptions = {
        "Python/Django": {
            "skills": ["Python", "Django", "Flask", "SQL", "PostgreSQL", "REST API"],
            "ProjectDomain": ["Healthcare", "E-commerce", "Finance", "Education", "Real Estate"],
            "Experience": ["3-5 years"],
            "Location": ["Pune"],
            "Must to have" : ["Basic Python", "Django"],
            "Good to have" : ["Docker", "AWS", "Kubernetes","PyQt", "streamlit", "Machine Learning"]
        },
        "Java/Spring Boot": {
            "skills": ["Java", "Spring Boot", "SQL", "PostgreSQL", "REST API", "Docker", "AWS", "Git", "HTML", "CSS", "JavaScript"],
            "ProjectDomain": ["Healthcare", "E-commerce", "Finance", "Education", "Real Estate"],
            "Experience": ["3-5 years"],
            "Location": ["Bangalore", "Pune", "Hyderabad", "Chennai", "Mumbai"],
            "Must to have" : ["Java", "Spring framework"],
            "Good to have" : ["Docker", "AWS", "Kubernetes","database management"]
        },
        "MERN Developer": {
            "skills": ["React", "Node.js", "MongoDB", "REST API", "Docker", "AWS", "Git", "JavaScript"],
            "ProjectDomain": ["Healthcare", "E-commerce", "Finance", "Education", "Real Estate"],
            "Experience": ["3-5 years"],
            "Location": ["Bangalore", "Pune", "Hyderabad", "Chennai", "Mumbai"],
            "Must to have" : ["JavaScript", "React (for frontend)", " Node.js (for backend)"],
            "Good to have" : ["Docker", "AWS", "MongoDB", "Git"]
        },
        "Graphic Designer": {
            "skills": ["Photoshop", "Illustrator", "Creativity", "UX/UI", "Design Thinking"],
            "ProjectDomain": ["VFX", "Animation", "Web Design", "Mobile App Design"],
            "Experience": ["5-6 years"],
            "Location": ["Remote"],
            "Must to have" : ["Photoshop", "Illustrator","UI/UX"],
            "Good to have" : ["motion graphics", "3D design", "Blender", "Adobe After Effects"]
        }
    }

    return job_descriptions


################# -- Streamlit UI -- #################
st.markdown(
    "<h3 style='padding: 8px; text-align: center; background-color: #EAF2F8; color: #1A5276;'>"
    "SmartHire</h3>",
    unsafe_allow_html=True
)

st.write("")#extra space between heading and upload section

# Upload Section: multiple resumes (PDF, DOCX)
st.subheader("Upload Resumes (PDF, DOCX)")
uploaded_files = st.file_uploader("Choose files", accept_multiple_files=True, type=["pdf", "docx"])
analyze_disabled = len(uploaded_files) == 0 # Disable analyze button if no files uploaded
resumes_texts = upload_files(uploaded_files)

#getting job description
job_descriptions = get_jd()

# Call Job Description Editor
jd_manager = jobDescription.JobDescriptionManager(job_descriptions)
job_title = jd_manager.job_title
updated_jd = jd_manager.JDEditor()

# User input for cutoff score (float values allowed)
cutoff_score = st.number_input("🎯 Enter Cutoff Score", min_value=0.0, max_value=10.0, value=6.0, step=0.1)

results = score_resumes(analyze_disabled, resumes_texts, job_title)
if results:
    passed_df = display_results(results)

    # Check if 'passed_df' exists in session state, if not, initialize it
    if "passed_df" not in st.session_state:
        st.session_state["passed_df"] = passed_df
    else:
        # Update existing session state variable
        st.session_state["passed_df"] = passed_df

# Ensure 'passed_df' exists before accessing it
if "passed_df" in st.session_state and not st.session_state["passed_df"].empty:
    schedule_manager = schedule.PassedCandidatesManager(st.session_state["passed_df"])
    schedule_manager.handle_schedule()
else:
    st.warning("⚠️ No passed candidates available for scheduling.")



