import os
import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
import assemblyai as aai
from pypdf import PdfReader
from fpdf import FPDF
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# Set your API keys
google_api_key = 'AIzaSyD2_oxzOQQtcGDmW_Ul8E7mREi_LYYJO9I'
assemblyai_api_key = '458d04f86c934454bb8148b4f595a171'
os.environ['GOOGLE_API_KEY'] = google_api_key
aai.settings.api_key = assemblyai_api_key

# Configure the API client with your API key
genai.configure(api_key=google_api_key)


def display_logos():
    st.image("ipams_logo(1).png", width=60) 
display_logos()

def generate_summary_prompt(comments):
    comments_text = " ".join(map(str, comments))
    prompt = f"...Ask first question as Introduce about yourself, next Generate 5 Technical questions based on this resume(projects, skills) for the candidate from the given resume.........ask 2 questions on SQL.....ask 2 question on DBMS......Ask Total 10 questions. I DONT WANT HEADINGS..GIVE STRAIGHT 1..... QUESTIONS LINE BY LINE.:\n\n{comments_text}"
    return prompt

def generate_text(prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = [page.extract_text() for page in reader.pages]
    return text

def generate_pdf(analysis_report):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Interview Analysis Report", ln=True, align="C")
    pdf.ln(10)
    pdf.multi_cell(0, 10, analysis_report)
    pdf_output_path = "Interview_Analysis_Report.pdf"
    pdf.output(pdf_output_path)
    return pdf_output_path

def send_email(to_email, pdf_path):
    from_email = "ipams2.ohr@gmail.com"
    subject = "Interview Analysis Report"
    body = "Please find the attached Interview Analysis Report."

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    with open(pdf_path, "rb") as f:
        part = MIMEApplication(f.read(), Name="Interview_Analysis_Report.pdf")
        part['Content-Disposition'] = 'attachment; filename="Interview_Analysis_Report.pdf"'
        msg.attach(part)

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(from_email, 'boyparupktudwtci')  # Use environment variable for actual password
        server.sendmail(from_email, to_email, msg.as_string())

# Streamlit app
st.title("IPAMS 2.O")

if 'name' not in st.session_state or 'email' not in st.session_state:
    st.header("Candidate Information")
    name = st.text_input("Enter your name")
    email = st.text_input("Enter your email")

    if st.button("Submit Info"):
        if name and email:
            st.session_state.name = name
            st.session_state.email = email
            st.write(f"Hi {name}, please upload your resume.")
        else:
            st.error("Please enter both name and email.")
else:
    st.write(f"Hi {st.session_state.name}, please upload your resume.")
    pdf_file = st.file_uploader("Upload PDF", type=["pdf"])

    if pdf_file and 'questions' not in st.session_state:
        with st.spinner("Extracting text from PDF..."):
            comments = extract_text_from_pdf(pdf_file)
            prompt = generate_summary_prompt(comments)

        st.write("Generating questions...")
        with st.spinner("Generating questions..."):
            questions = generate_text(prompt).split('\n')
            st.session_state.questions = [{"question": q, "answer": "", "transcribed": False} for q in questions if q.strip()]
            st.session_state.current_question_index = 0

    if 'questions' in st.session_state:
        st.subheader("Generated Questions")

        current_index = st.session_state.current_question_index
        question_data = st.session_state.questions[current_index]
        question = question_data["question"]
        st.write(f"{current_index + 1}. {question}")

        components.html(f"""
            <div>
                <video id="video_{current_index}" width="320" height="240" controls></video>
                <br>
                <button id="record_{current_index}">Record</button>
                <button id="stop_{current_index}">Stop</button>
                <script>
                    let video = document.getElementById('video_{current_index}');
                    let recordButton = document.getElementById('record_{current_index}');
                    let stopButton = document.getElementById('stop_{current_index}');
                    let mediaRecorder;
                    let recordedChunks = [];

                    recordButton.onclick = async () => {{
                        let stream = await navigator.mediaDevices.getUserMedia({{ video: true, audio: true }});
                        video.srcObject = stream;
                        mediaRecorder = new MediaRecorder(stream);
                        mediaRecorder.start();
                        recordedChunks = [];

                        mediaRecorder.ondataavailable = (event) => {{
                            if (event.data.size > 0) {{
                                recordedChunks.push(event.data);
                            }}
                        }};

                        mediaRecorder.onstop = () => {{
                            let blob = new Blob(recordedChunks, {{ type: 'video/mp4' }});
                            let url = URL.createObjectURL(blob);
                            let a = document.createElement('a');
                            a.href = url;
                            a.download = 'video_{current_index}.mp4';
                            document.body.appendChild(a);
                            a.click();
                            setTimeout(() => URL.revokeObjectURL(url), 100);
                        }};
                    }};

                    stopButton.onclick = () => {{
                        mediaRecorder.stop();
                        video.srcObject.getTracks().forEach(track => track.stop());
                    }};
                </script>
            </div>
        """, height=400)

        video_file = st.file_uploader(f"Upload video answer for Question {current_index + 1}", type=["mp4"], key=f"uploader_{current_index}")

        if video_file and not question_data["transcribed"]:
            with st.spinner("Transcribing video..."):
                video_path = f"uploaded_video_{current_index + 1}.mp4"
                with open(video_path, "wb") as f:
                    f.write(video_file.read())
                transcript = transcribe_video(video_path)
                st.session_state.questions[current_index]["answer"] = transcript
                st.session_state.questions[current_index]["transcribed"] = True
                st.write(f"Transcription: {transcript}")

        if st.button("Next Question") and current_index < len(st.session_state.questions) - 1:
            st.session_state.current_question_index += 1
        elif st.session_state.current_question_index == len(st.session_state.questions) - 1:
            st.success("All questions answered. Preparing analysis...")

            if st.button("Submit Answers"):
                with st.spinner("Analyzing answers..."):
                    answers = [q["answer"] for q in st.session_state.questions]
                    analysis_report = analyze_answers_with_ai(answers)
                
                st.subheader("Summary Report")
                pdf_path = generate_pdf(analysis_report)
                st.success(f"PDF report generated: {pdf_path}")
                send_email(st.session_state.email, pdf_path)
                st.write("The report has been sent to your email.")
