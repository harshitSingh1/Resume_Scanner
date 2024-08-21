import streamlit as st
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF
import google.generativeai as genai
import hashlib

# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Function to estimate reading time
def estimate_reading_time(text):
    words_per_minute = 200  # Average reading speed
    words = len(text.split())
    reading_time = words / words_per_minute
    return round(reading_time, 2)

# Define prompts for resume evaluation
summary_prompt = """You are a resume summarizer. You will be provided with the text of a resume
and need to summarize its content, highlighting key skills, experiences, and achievements within 250 words.
Resume Text: 📝"""

rating_prompt_template = """You are an ATS evaluator. You will be provided with the summary of a resume
and you need to rate it out of 10 based on relevance to the provided job description.
Summary: {summary}
Job Description: {job_description}
Rating: 📝"""

feedback_prompt_template = """You are an ATS evaluator. You will be provided with the summary of a resume
and you need to provide constructive feedback on how to improve it.
Summary: {summary}
Job Description: {job_description}
Feedback: 📝"""

question_prompt_template = """You are a helpful assistant. You will be provided with the text of a resume
and a question. Please provide a clear and concise answer to the question based on the text provided.
Resume Text: {resume_text}
Question: {question}
Answer: 📝"""

comparison_prompt_template = """You are a resume comparison assistant. You will be provided with summaries of two resumes
and a job description. Please provide a detailed comparison of the two resumes in terms of their suitability for the job.
Resume 1 Summary: {summary1}
Resume 2 Summary: {summary2}
Job Description: {job_description}
Comparison Analysis: 📝"""

# Function to extract text from PDF
def extract_text_from_pdf(file):
    try:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        raise e

# Function to get content from Google Gemini Pro
def generate_gemini_content(transcript_text, prompt):
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt + transcript_text)
    return response.text

# Function to generate a unique identifier for the PDF
def generate_pdf_id(pdf_text):
    return hashlib.md5(pdf_text.encode()).hexdigest()

# Store Q&A history for PDFs
if 'pdf_qa_history' not in st.session_state:
    st.session_state.pdf_qa_history = {}

# Store Q&A history for compared resumes
if 'compare_qa_history' not in st.session_state:
    st.session_state.compare_qa_history = {}

# Streamlit UI
st.title("Resume ATS Scanner 📄➡️🔍")
uploaded_file = st.file_uploader("Upload a Resume PDF file", type="pdf")

add_job_description = st.checkbox("Add Job Description")
job_description = ""
company_name = ""
job_post = ""

if add_job_description:
    company_name = st.text_input("Company Name")
    job_post = st.text_input("Job Post")
    job_description = st.text_area("Job Description")

if uploaded_file:
    # Extract text from PDF
    resume_text = extract_text_from_pdf(uploaded_file)

    # Generate unique ID for the PDF
    resume_id = generate_pdf_id(resume_text)

    # Initialize Q&A history for this PDF if not already present
    if resume_id not in st.session_state.pdf_qa_history:
        st.session_state.pdf_qa_history[resume_id] = {}

    # Estimate and display reading time at the top
    reading_time = estimate_reading_time(resume_text)
    st.markdown(f"**Estimated Reading Time:** {reading_time} minutes")

    # Define maximum input length for LLM
    max_input_length = 2000

    # Check if the extracted text exceeds the maximum input length
    if len(resume_text) > max_input_length:
        resume_text = resume_text[:max_input_length]
        st.warning("The resume is too long. The text has been truncated to fit within the input limit.")

    # Show a portion of the extracted text
    st.markdown("## Extracted Text:")
    st.write(resume_text[:1000])  # Display first 1000 characters of the extracted text for reference

    if st.button("Review Resume 📄"):
        # Generate summary
        combined_summary = generate_gemini_content(resume_text, summary_prompt)

        st.markdown("## Resume Summary:")
        st.write(combined_summary)

        # Ask Google Gemini to rate the resume
        rating_prompt = rating_prompt_template.format(summary=combined_summary, job_description=job_description)
        rating_response = generate_gemini_content("", rating_prompt)
        st.markdown("## ATS Rating:")
        st.write(rating_response)

        # Ask Google Gemini to provide feedback
        feedback_prompt = feedback_prompt_template.format(summary=combined_summary, job_description=job_description)
        feedback_response = generate_gemini_content("", feedback_prompt)
        st.markdown("## ATS Feedback:")
        st.write(feedback_response)

    # Add a text input for questions
    st.markdown("## Ask a Question:")
    user_question = st.text_input("Enter your question here")

    if user_question:
        if user_question in st.session_state.pdf_qa_history[resume_id]:
            combined_answer = st.session_state.pdf_qa_history[resume_id][user_question]
        else:
            question_prompt = question_prompt_template.format(resume_text=resume_text, question=user_question)
            combined_answer = generate_gemini_content("", question_prompt)
            st.session_state.pdf_qa_history[resume_id][user_question] = combined_answer

        st.markdown("## Answer:")
        st.write(combined_answer)

    # Display previously asked questions and answers for this PDF
    if st.session_state.pdf_qa_history[resume_id]:
        st.markdown("## Previously Asked Questions:")
        for question, answer in st.session_state.pdf_qa_history[resume_id].items():
            with st.expander(f"Question: {question}"):
                st.write(answer)

# Optional: Compare multiple resumes
st.markdown("## Compare Resumes")
uploaded_files = st.file_uploader("Upload Resume PDF files for comparison", type="pdf", accept_multiple_files=True)

if uploaded_files:
    resume_texts = [extract_text_from_pdf(uploaded_file) for uploaded_file in uploaded_files]
    resume_summaries = [generate_gemini_content(resume_text, summary_prompt) for resume_text in resume_texts]
    file_names = [uploaded_file.name for uploaded_file in uploaded_files]

    if len(uploaded_files) > 1:
        resume_options = st.multiselect("Select two resumes to compare", file_names, default=file_names[:2])
        if len(resume_options) == 2:
            idx1 = file_names.index(resume_options[0])
            idx2 = file_names.index(resume_options[1])

            if st.button("Compare Resumes"):
                summary1 = resume_summaries[idx1]
                summary2 = resume_summaries[idx2]
                comparison_prompt = comparison_prompt_template.format(summary1=summary1, summary2=summary2, job_description=job_description)
                comparison_analysis = generate_gemini_content("", comparison_prompt)

                st.markdown(f"### Comparison of {resume_options[0]} and {resume_options[1]}")
                st.markdown(f"**Comparison Analysis:** {comparison_analysis}")

                # Store previously asked questions and answers for the compared resumes
                combined_resumes_text = " ".join([resume_texts[idx1], resume_texts[idx2]])
                combined_resumes_id = generate_pdf_id(combined_resumes_text)

                if combined_resumes_id not in st.session_state.compare_qa_history:
                    st.session_state.compare_qa_history[combined_resumes_id] = comparison_analysis
                else:
                    comparison_analysis = st.session_state.compare_qa_history[combined_resumes_id]

                # Display final conclusion in bold
                st.markdown(f"**Final Conclusion:** {comparison_analysis}")

                # Store the comparison result for future reference
                st.session_state.compare_qa_history[combined_resumes_id] = comparison_analysis
