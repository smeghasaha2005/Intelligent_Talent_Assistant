import os
import json
from dotenv import load_dotenv
from openai import OpenAI

from prompts import SCREENING_PROMPT, ENGAGEMENT_PROMPT, STATUS_CHAT_PROMPT, RAG_QA_PROMPT
from utils import parse_skills_from_text

load_dotenv()


class BaseAgent:
    def __init__(self, system_prompt, model="llama-3.3-70b-versatile", temperature=0.3):
        self.system_prompt = system_prompt
        self.model = model
        self.temperature = temperature
        self.api_key = os.getenv("GROQ_API_KEY")
        self.use_fallback = not bool(self.api_key)
        self.client = None

        if self.api_key:
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.groq.com/openai/v1"
                )
            except Exception:
                self.use_fallback = True

    def chat(self, user_prompt):
        if self.use_fallback:
            return None

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.temperature
        )
        return response.choices[0].message.content.strip()


class ScreeningAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system_prompt="You are an expert screening assistant. Return only valid JSON.",
            temperature=0.2
        )

    def screen_resume(self, resume_text, job_description):
        if self.use_fallback:
            return self._fallback_screen(resume_text, job_description)

        prompt = SCREENING_PROMPT.format(
            resume_text=resume_text,
            job_description=job_description
        )

        try:
            result = self.chat(prompt)
            result = self._clean_json(result)
            parsed = json.loads(result)
            return self._normalize_screening_result(parsed, resume_text, job_description)
        except Exception:
            return self._fallback_screen(resume_text, job_description)

    def _clean_json(self, text):
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _normalize_screening_result(self, result, resume_text, job_description):
        resume_skills = parse_skills_from_text(resume_text)
        jd_skills = parse_skills_from_text(job_description)

        ai_score = int(result.get("match_score", 0))

        matched_skills = result.get("matched_skills", [])
        if not isinstance(matched_skills, list):
            matched_skills = []

        missing_skills = result.get("missing_skills", [])
        if not isinstance(missing_skills, list):
            missing_skills = []

        strengths = result.get("strengths", [])
        if not isinstance(strengths, list):
            strengths = []

        weaknesses = result.get("weaknesses", [])
        if not isinstance(weaknesses, list):
            weaknesses = []

        if jd_skills:
            real_matched = [skill for skill in jd_skills if skill in resume_skills]
            skill_score = (len(real_matched) / len(jd_skills)) * 70
        else:
            real_matched = resume_skills[:4]
            skill_score = 50

        resume_lower = resume_text.lower()

        exp_score = 0
        if "5 years" in resume_lower or "4 years" in resume_lower:
            exp_score = 20
        elif "3 years" in resume_lower:
            exp_score = 18
        elif "2 years" in resume_lower or "2 year" in resume_lower:
            exp_score = 15
        elif "1 year" in resume_lower or "1 years" in resume_lower or "intern" in resume_lower or "project" in resume_lower:
            exp_score = 10

        edu_score = 0
        education_keywords = [
            "b.tech", "btech", "b.e", "be", "m.tech", "mtech",
            "b.sc", "bsc", "m.sc", "msc", "bca", "mca",
            "degree", "college", "university"
        ]
        if any(word in resume_lower for word in education_keywords):
            edu_score = 10

        recalculated_score = int(min(100, skill_score + exp_score + edu_score))
        score = max(ai_score, recalculated_score)

        if score >= 70:
            recommendation = "Shortlist"
        elif score >= 45:
            recommendation = "Hold"
        else:
            recommendation = "Reject"

        if not matched_skills:
            matched_skills = real_matched

        if not missing_skills and jd_skills:
            missing_skills = [skill for skill in jd_skills if skill not in resume_skills]

        if not strengths:
            strengths = []
            if matched_skills:
                strengths.append(f"Matched skills: {', '.join(matched_skills[:4])}")
            if exp_score > 0:
                strengths.append("Relevant experience or project exposure found")
            if edu_score > 0:
                strengths.append("Educational qualification present")

        if not weaknesses:
            weaknesses = []
            if missing_skills:
                weaknesses.append(f"Missing skills: {', '.join(missing_skills[:4])}")
            if score < 50:
                weaknesses.append("Low overall job fit")

        if not strengths:
            strengths = ["Basic profile information identified"]
        if not weaknesses:
            weaknesses = ["No major weaknesses detected from analysis"]

        short_reason = result.get("short_reason", "")
        if not short_reason:
            short_reason = "Recommendation derived from weighted score using skills, experience, and education."

        return {
            "match_score": score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "strengths": strengths[:3],
            "weaknesses": weaknesses[:3],
            "recommendation": recommendation,
            "short_reason": short_reason
        }

    def _fallback_screen(self, resume_text, job_description):
        resume_skills = parse_skills_from_text(resume_text)
        jd_skills = parse_skills_from_text(job_description)

        matched = [skill for skill in jd_skills if skill in resume_skills]
        missing = [skill for skill in jd_skills if skill not in resume_skills]

        if jd_skills:
            skill_score = (len(matched) / len(jd_skills)) * 70
        else:
            skill_score = 50

        resume_lower = resume_text.lower()

        exp_score = 0
        if "5 years" in resume_lower or "4 years" in resume_lower:
            exp_score = 20
        elif "3 years" in resume_lower:
            exp_score = 18
        elif "2 years" in resume_lower or "2 year" in resume_lower:
            exp_score = 15
        elif "1 year" in resume_lower or "1 years" in resume_lower or "intern" in resume_lower or "project" in resume_lower:
            exp_score = 10

        edu_score = 0
        education_keywords = [
            "b.tech", "btech", "b.e", "be", "m.tech", "mtech",
            "b.sc", "bsc", "m.sc", "msc", "bca", "mca",
            "degree", "college", "university"
        ]
        if any(word in resume_lower for word in education_keywords):
            edu_score = 10

        score = int(min(100, skill_score + exp_score + edu_score))

        if score >= 70:
            recommendation = "Shortlist"
        elif score >= 45:
            recommendation = "Hold"
        else:
            recommendation = "Reject"

        strengths = []
        weaknesses = []

        if matched:
            strengths.append(f"Matched skills: {', '.join(matched[:4])}")
        if exp_score > 0:
            strengths.append("Relevant experience or project exposure found")
        if edu_score > 0:
            strengths.append("Educational qualification present")

        if missing:
            weaknesses.append(f"Missing skills: {', '.join(missing[:4])}")
        if score < 50:
            weaknesses.append("Low overall job fit")

        if not strengths:
            strengths = ["Basic profile information identified"]
        if not weaknesses:
            weaknesses = ["No major weaknesses detected from fallback analysis"]

        return {
            "match_score": score,
            "matched_skills": matched,
            "missing_skills": missing,
            "strengths": strengths[:3],
            "weaknesses": weaknesses[:3],
            "recommendation": recommendation,
            "short_reason": "Score calculated using weighted skills, experience, and education."
        }


class SchedulingAgent:
    def schedule_interview(self, candidate_name, recruiter_name, date, time):
        return {
            "candidate_name": candidate_name,
            "recruiter_name": recruiter_name,
            "date": str(date),
            "time": time,
            "status": "Interview Scheduled"
        }


class EngagementAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system_prompt="You are a professional HR communication assistant.",
            temperature=0.4
        )

    def generate_message(self, candidate_name, job_title, company_name, interview_date, interview_time, current_status):
        if self.use_fallback:
            return (
                f"Hello {candidate_name},\n\n"
                f"You have been shortlisted for the {job_title} role at {company_name}. "
                f"Your current status is {current_status}. "
                f"Your interview is scheduled on {interview_date} at {interview_time}.\n\n"
                f"Regards,\nHR Team"
            )

        prompt = ENGAGEMENT_PROMPT.format(
            candidate_name=candidate_name,
            job_title=job_title,
            company_name=company_name,
            interview_date=interview_date,
            interview_time=interview_time,
            current_status=current_status
        )

        try:
            return self.chat(prompt)
        except Exception:
            return (
                f"Hello {candidate_name},\n\n"
                f"You have been shortlisted for the {job_title} role. "
                f"Interview is scheduled on {interview_date} at {interview_time}.\n\n"
                f"Regards,\nHR Team"
            )


class StatusChatAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system_prompt="You are a recruitment status assistant for HR managers.",
            temperature=0.2
        )

    def answer_hr_query(self, recruitment_data, question):
        if self.use_fallback:
            return self._fallback_answer(recruitment_data, question)

        prompt = STATUS_CHAT_PROMPT.format(
            recruitment_data=json.dumps(recruitment_data, indent=2),
            question=question
        )

        try:
            result = self.chat(prompt)
            return result if result else self._fallback_answer(recruitment_data, question)
        except Exception:
            return self._fallback_answer(recruitment_data, question)

    def _fallback_answer(self, recruitment_data, question):
        q = question.lower()
        screening = recruitment_data.get("screening_result")
        schedule = recruitment_data.get("interview_schedule")
        status = recruitment_data.get("current_status", "Unknown")

        if "status" in q:
            return f"The current recruitment status is: {status}."

        if "score" in q or "match" in q:
            if screening:
                return f"The candidate match score is {screening.get('match_score', 0)}%."
            return "I could not find that information in the current recruitment process."

        if "missing skill" in q or "missing skills" in q:
            if screening:
                skills = screening.get("missing_skills", [])
                if skills:
                    return "Missing skills are: " + ", ".join(skills) + "."
                return "No major missing skills were identified."
            return "I could not find that information in the current recruitment process."

        if "interview" in q or "schedule" in q:
            if schedule:
                return (
                    f"The interview is scheduled on {schedule.get('date')} "
                    f"at {schedule.get('time')} with {schedule.get('recruiter_name')}."
                )
            return "Interview has not been scheduled yet."

        if "recommendation" in q or "selected" in q or "shortlist" in q:
            if screening:
                return f"The screening recommendation is: {screening.get('recommendation', 'Not available')}."
            return "I could not find that information in the current recruitment process."

        return "I could not find that information in the current recruitment process."


class RAGQAAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system_prompt="You are a resume Q&A assistant. Answer only from the given context.",
            temperature=0.2
        )

    def answer_question(self, context, question, resume_text, job_description):
        if self.use_fallback:
            return self._fallback_answer(context, question, resume_text)

        prompt = RAG_QA_PROMPT.format(
            context=context,
            question=question,
            resume_text=resume_text,
            job_description=job_description
        )

        try:
            answer = self.chat(prompt)
            return answer if answer else self._fallback_answer(context, question, resume_text)
        except Exception:
            return self._fallback_answer(context, question, resume_text)

    def _fallback_answer(self, context, question, resume_text):
        q = question.lower()
        text = f"{context}\n{resume_text}".lower()

        if "skill" in q:
            skills = parse_skills_from_text(text)
            if skills:
                return "Detected skills include: " + ", ".join(skills[:8]) + "."
            return "I could not find that information in the provided resume."

        if "experience" in q:
            if "year" in text or "intern" in text or "project" in text:
                return "The resume indicates experience or project exposure."
            return "I could not find that information in the provided resume."

        if "education" in q or "qualification" in q:
            for word in ["b.tech", "btech", "m.tech", "bca", "mca", "degree", "college", "university"]:
                if word in text:
                    return "The resume contains educational qualification details."
            return "I could not find that information in the provided resume."

        return "Based on the retrieved resume context, a precise answer could not be extracted."