class RecruitmentDataStore:
    def __init__(self):
        self.candidate_name = ""
        self.resume_text = ""
        self.job_description = ""
        self.screening_result = None
        self.current_status = "Not Started"
        self.interview_schedule = None
        self.engagement_message = ""
        self.message_sent = False
        self.hr_chat_history = []

    def set_candidate_data(self, candidate_name, resume_text, job_description, force_reset=False):
        self.candidate_name = candidate_name
        self.resume_text = resume_text
        self.job_description = job_description

        # Only reset status when a NEW resume is uploaded
        if force_reset:
            self.screening_result = None
            self.interview_schedule = None
            self.engagement_message = ""
            self.message_sent = False
            self.hr_chat_history = []
            self.current_status = "Resume Uploaded"

    def set_screening_result(self, result):
        self.screening_result = result
        score = int(result.get("match_score", 0))

        if score >= 70:
            self.current_status = "Shortlisted"
            self.screening_result["recommendation"] = "Shortlist"
        elif score >= 45:
            self.current_status = "Hold"
            self.screening_result["recommendation"] = "Hold"
        else:
            self.current_status = "Rejected"
            self.screening_result["recommendation"] = "Reject"

    def set_interview_schedule(self, schedule):
        self.interview_schedule = schedule
        self.current_status = "Interview Scheduled"

    def set_engagement_message(self, message):
        self.engagement_message = message

    def mark_message_sent(self):
        self.message_sent = True
        if self.current_status == "Interview Scheduled":
            self.current_status = "Engagement Message Sent"
        else:
            self.current_status = "Engaged"

    def add_chat(self, question, answer):
        self.hr_chat_history.append({
            "question": question,
            "answer": answer
        })

    def get_full_data(self):
        return {
            "candidate_name": self.candidate_name,
            "resume_uploaded": bool(self.resume_text),
            "job_description_available": bool(self.job_description),
            "screening_result": self.screening_result,
            "current_status": self.current_status,
            "interview_schedule": self.interview_schedule,
            "engagement_message": self.engagement_message,
            "message_sent": self.message_sent,
            "hr_chat_history": self.hr_chat_history
        }