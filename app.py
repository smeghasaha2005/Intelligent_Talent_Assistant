import streamlit as st

from utils import extract_resume_text, build_candidate_profile, parse_skills_from_text
from data_store import RecruitmentDataStore
from agents import ScreeningAgent, SchedulingAgent, EngagementAgent, StatusChatAgent, RAGQAAgent
from vector_store import ResumeVectorStore

st.set_page_config(
    page_title="Intelligent Talent Acquisition Assistant",
    page_icon="🤖",
    layout="wide"
)


def init_session():
    if "store" not in st.session_state:
        st.session_state.store = RecruitmentDataStore()

    if "screening_agent" not in st.session_state:
        st.session_state.screening_agent = ScreeningAgent()

    if "scheduling_agent" not in st.session_state:
        st.session_state.scheduling_agent = SchedulingAgent()

    if "engagement_agent" not in st.session_state:
        st.session_state.engagement_agent = EngagementAgent()

    if "status_chat_agent" not in st.session_state:
        st.session_state.status_chat_agent = StatusChatAgent()

    if "rag_qa_agent" not in st.session_state:
        st.session_state.rag_qa_agent = RAGQAAgent()

    if "vector_store" not in st.session_state:
        st.session_state.vector_store = ResumeVectorStore()

    if "resume_text" not in st.session_state:
        st.session_state.resume_text = ""

    if "candidate_profile" not in st.session_state:
        st.session_state.candidate_profile = None

    if "screening_result" not in st.session_state:
        st.session_state.screening_result = None

    if "interview_schedule" not in st.session_state:
        st.session_state.interview_schedule = None

    if "engagement_message" not in st.session_state:
        st.session_state.engagement_message = ""

    if "rag_ready" not in st.session_state:
        st.session_state.rag_ready = False

    if "last_uploaded_file_name" not in st.session_state:
        st.session_state.last_uploaded_file_name = ""


def main():
    init_session()

    st.title("🤖 Intelligent Talent Acquisition Dashboard")
    st.write(
        "Upload a resume, screen it with a job description, shortlist the candidate, "
        "schedule the interview, generate candidate communication, and ask HR/status questions."
    )

    st.sidebar.header("Job Input")
    company_name = st.sidebar.text_input("Company Name", value="ABC Technologies")
    recruiter_name = st.sidebar.text_input("Recruiter Name", value="HR Manager")
    job_title = st.sidebar.text_input("Job Title", value="AI/ML Engineer")

    job_description = st.sidebar.text_area(
        "Job Description",
        height=220,
        value=(
            "We are looking for an AI/ML Engineer with Python, SQL, Machine Learning, "
            "NLP, Git, and Streamlit experience. Candidates with project experience "
            "and good communication skills are preferred."
        )
    )

    st.sidebar.header("Resume Upload")
    uploaded_file = st.sidebar.file_uploader("Upload Resume", type=["pdf", "docx", "txt"])

    if uploaded_file is not None:
        # Process only when a NEW file is uploaded
        if st.session_state.last_uploaded_file_name != uploaded_file.name:
            resume_text = extract_resume_text(uploaded_file)

            if resume_text.strip():
                profile = build_candidate_profile(resume_text)

                st.session_state.resume_text = resume_text
                st.session_state.candidate_profile = profile
                st.session_state.screening_result = None
                st.session_state.interview_schedule = None
                st.session_state.engagement_message = ""

                st.session_state.store.set_candidate_data(
                    candidate_name=profile["name"],
                    resume_text=resume_text,
                    job_description=job_description,
                    force_reset=True
                )

                try:
                    st.session_state.vector_store.create_vector_store(resume_text)
                    st.session_state.rag_ready = True
                except Exception:
                    st.session_state.rag_ready = False

                st.session_state.last_uploaded_file_name = uploaded_file.name
                st.sidebar.success(f"Resume uploaded successfully for {profile['name']}.")
            else:
                st.sidebar.error("Could not extract text from the uploaded file.")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Screening",
        "📅 Scheduling",
        "💬 Engagement",
        "🤖 RAG Q&A / HR Chat"
    ])

    with tab1:
        st.subheader("Resume Screening")

        if st.session_state.resume_text:
            candidate_name = (
                st.session_state.candidate_profile["name"]
                if st.session_state.candidate_profile else "Candidate"
            )

            left, right = st.columns([2, 1])

            with left:
                st.write(f"**Candidate Name:** {candidate_name}")
                st.text_area("Extracted Resume Text", st.session_state.resume_text, height=280)

            with right:
                detected_skills = parse_skills_from_text(st.session_state.resume_text)
                st.write("**Detected Skills**")
                st.write(", ".join(detected_skills) if detected_skills else "No common skills found.")

            if st.button("Analyze Resume", use_container_width=True):
                result = st.session_state.screening_agent.screen_resume(
                    st.session_state.resume_text,
                    job_description
                )
                st.session_state.screening_result = result
                st.session_state.store.set_screening_result(result)

            if st.session_state.screening_result:
                result = st.session_state.screening_result

                col1, col2 = st.columns(2)
                col1.metric("Match Score", f"{result.get('match_score', 0)}%")
                col2.metric("Current Status", st.session_state.store.current_status)

                st.write("**Matched Skills:**", ", ".join(result.get("matched_skills", [])) or "None")
                st.write("**Missing Skills:**", ", ".join(result.get("missing_skills", [])) or "None")
                st.write("**Strengths:**", ", ".join(result.get("strengths", [])) or "None")
                st.write("**Weaknesses:**", ", ".join(result.get("weaknesses", [])) or "None")
                st.write("**Recommendation:**", result.get("recommendation", ""))
                st.write("**Reason:**", result.get("short_reason", ""))

                if st.session_state.store.current_status == "Shortlisted":
                    st.success("Candidate is shortlisted.")
                elif st.session_state.store.current_status == "Rejected":
                    st.error("Candidate is rejected.")
                elif st.session_state.store.current_status == "Hold":
                    st.warning("Candidate is on hold.")
                else:
                    st.info(f"Current status: {st.session_state.store.current_status}")
        else:
            st.info("Please upload a resume from the sidebar.")

    with tab2:
        st.subheader("Interview Scheduling")

        if not st.session_state.screening_result:
            st.info("Please analyze the resume first.")
        elif st.session_state.store.current_status != "Shortlisted":
            st.warning("Interview can be scheduled only for shortlisted candidates.")
        else:
            candidate_name = (
                st.session_state.candidate_profile["name"]
                if st.session_state.candidate_profile else "Candidate"
            )

            st.write(f"**Candidate Name:** {candidate_name}")

            interview_date = st.date_input("Interview Date")
            interview_time = st.text_input("Interview Time", value="11:00 AM")

            if st.button("Schedule Interview", use_container_width=True):
                schedule = st.session_state.scheduling_agent.schedule_interview(
                    candidate_name=candidate_name,
                    recruiter_name=recruiter_name,
                    date=interview_date,
                    time=interview_time
                )
                st.session_state.interview_schedule = schedule
                st.session_state.store.set_interview_schedule(schedule)
                st.success(
                    f"Interview scheduled for {schedule['candidate_name']} on "
                    f"{schedule['date']} at {schedule['time']} with {schedule['recruiter_name']}."
                )

            if st.session_state.interview_schedule:
                st.write("**Scheduled Interview Details**")
                st.json(st.session_state.interview_schedule)

    with tab3:
        st.subheader("Candidate Engagement")

        if not st.session_state.interview_schedule:
            st.info("Please schedule the interview first.")
        else:
            candidate_name = (
                st.session_state.candidate_profile["name"]
                if st.session_state.candidate_profile else "Candidate"
            )

            if st.button("Generate Candidate Message", use_container_width=True):
                schedule = st.session_state.interview_schedule

                message = st.session_state.engagement_agent.generate_message(
                    candidate_name=candidate_name,
                    job_title=job_title,
                    company_name=company_name,
                    interview_date=schedule["date"],
                    interview_time=schedule["time"],
                    current_status=st.session_state.store.current_status
                )

                st.session_state.engagement_message = message
                st.session_state.store.set_engagement_message(message)

            if st.session_state.engagement_message:
                st.text_area(
                    "Generated Candidate Message",
                    value=st.session_state.engagement_message,
                    height=220
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Send Message", use_container_width=True):
                        st.session_state.store.mark_message_sent()
                        st.success(f"Message marked as sent to {candidate_name}.")
                with col2:
                    st.download_button(
                        label="Download Message",
                        data=st.session_state.engagement_message,
                        file_name="candidate_message.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

                if st.session_state.store.message_sent:
                    st.info("Current message status: Sent")

    with tab4:
        st.subheader("RAG Q&A / HR Chat")

        qa_mode = st.radio(
            "Choose Mode",
            ["Resume RAG Q&A", "HR Status Chatbot"],
            horizontal=True
        )

        question = st.text_input("Ask a question")

        if st.button("Get Answer", use_container_width=True):
            if not question.strip():
                st.warning("Please enter a question.")
            else:
                if qa_mode == "Resume RAG Q&A":
                    if not st.session_state.resume_text:
                        st.warning("Please upload a resume first.")
                    elif not st.session_state.rag_ready:
                        st.warning("Vector store is not ready.")
                    else:
                        context = st.session_state.vector_store.query(question)
                        answer = st.session_state.rag_qa_agent.answer_question(
                            context=context,
                            question=question,
                            resume_text=st.session_state.resume_text,
                            job_description=job_description
                        )
                        st.success(answer)
                else:
                    answer = st.session_state.status_chat_agent.answer_hr_query(
                        recruitment_data=st.session_state.store.get_full_data(),
                        question=question
                    )
                    st.session_state.store.add_chat(question, answer)
                    st.success(answer)

        if qa_mode == "HR Status Chatbot" and st.session_state.store.hr_chat_history:
            st.write("### Chat History")
            for item in st.session_state.store.hr_chat_history[-5:]:
                st.markdown(f"**Q:** {item['question']}")
                st.markdown(f"**A:** {item['answer']}")
                st.markdown("---")

        st.write("### Current Recruitment Data")
        st.json(st.session_state.store.get_full_data())


if __name__ == "__main__":
    main()