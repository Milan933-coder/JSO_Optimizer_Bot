# =============================================================================
# services/conversation_manager.py
# TalentScout — Conversation State & Token Manager
# =============================================================================
# This module owns ALL state transitions.
# The FastAPI route should NEVER mutate state directly — always go through here.
#
# STATE MACHINE:
#
#   [INFO_PENDING] ──(INFO_TOKEN: ENABLED)──► [INFO_COLLECTED]
#       │                                            │
#       │                               (questions generated)
#       │                                            │
#       │                                     [INTERVIEWING]
#       │                                       │        │
#       │                         (INTERVIEW_COMPLETE) (SESSION_TERMINATED)
#       │                                       │        │
#       └───────────────────────────────────────▼────────▼
#                                         [CLOSED]
# =============================================================================

from datetime import datetime, timedelta, timezone
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Any


# ─── States ──────────────────────────────────────────────────────────────────

class ConversationPhase(str, Enum):
    INFO_PENDING    = "INFO_PENDING"      # Waiting for candidate details
    INFO_COLLECTED  = "INFO_COLLECTED"    # Details received, generating questions
    INTERVIEWING    = "INTERVIEWING"      # Actively asking tech questions
    CODING_ROUND    = "CODING_ROUND"      # Timed DSA round
    CLOSED          = "CLOSED"           # Session ended (complete or terminated)


SESSION_TTL = timedelta(hours=2)


# ─── Candidate Info dataclass ────────────────────────────────────────────────

@dataclass
class CandidateInfo:
    name:             Optional[str] = None
    email:            Optional[str] = None
    phone:            Optional[str] = None
    years_experience: Optional[str] = None
    desired_position: Optional[str] = None
    location:         Optional[str] = None
    tech_stack:       Optional[str] = None

    def is_complete(self) -> bool:
        """Token becomes ENABLED only when ALL 7 fields are present."""
        return all([
            self.name,
            self.email,
            self.phone,
            self.years_experience,
            self.desired_position,
            self.location,
            self.tech_stack,
        ])

    def missing_fields(self) -> List[str]:
        """Returns list of field names still missing."""
        missing = []
        if not self.name:             missing.append("Full Name")
        if not self.email:            missing.append("Email Address")
        if not self.phone:            missing.append("Phone Number")
        if not self.years_experience: missing.append("Years of Experience")
        if not self.desired_position: missing.append("Desired Position(s)")
        if not self.location:         missing.append("Current Location")
        if not self.tech_stack:       missing.append("Tech Stack")
        return missing

    def to_dict(self) -> dict:
        return {
            "name":             self.name,
            "email":            self.email,
            "phone":            self.phone,
            "years_experience": self.years_experience,
            "desired_position": self.desired_position,
            "location":         self.location,
            "tech_stack":       self.tech_stack,
        }


# ─── Interview Question dataclass ────────────────────────────────────────────

@dataclass
class InterviewQuestion:
    id:          int
    technology:  str
    difficulty:  str
    question:    str
    focus_area:  str = ""
    evaluation_rubric: List[str] = field(default_factory=list)
    answered:    bool = False
    candidate_answer: Optional[str] = None
    review:      Optional["InterviewAnswerReview"] = None


@dataclass
class InterviewAnswerReview:
    question_id: int
    question: str
    technology: str
    focus_area: str
    technical_score: float
    explanation_score: float
    communication_score: float
    overall_score: float
    verdict: str
    review: str
    strengths: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    communication_notes: str = ""


@dataclass
class FinalInterviewAssessment:
    status: str
    readiness_score: float
    technical_depth_score: float
    communication_score: float
    summary: str
    strengths: List[str] = field(default_factory=list)
    improvement_areas: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    coverage_note: Optional[str] = None


@dataclass
class CodingRoundState:
    problem:           Optional[dict[str, Any]] = None
    started_at:        Optional[datetime] = None
    expires_at:        Optional[datetime] = None
    max_attempts:      int = 5
    attempts_used:     int = 0
    status:            str = "idle"
    completed:         bool = False
    completion_reason: Optional[str] = None
    last_result:       Optional[dict[str, Any]] = None

    def start(self, problem: dict[str, Any], duration_minutes: int, max_attempts: int):
        now = datetime.now(timezone.utc)
        self.problem = problem
        self.started_at = now
        self.expires_at = now + timedelta(minutes=duration_minutes)
        self.max_attempts = max_attempts
        self.attempts_used = 0
        self.status = "ready"
        self.completed = False
        self.completion_reason = None
        self.last_result = None

    def attempts_left(self) -> int:
        return max(self.max_attempts - self.attempts_used, 0)

    def remaining_seconds(self) -> int:
        if not self.expires_at:
            return 0
        remaining = int((self.expires_at - datetime.now(timezone.utc)).total_seconds())
        return max(remaining, 0)

    def is_expired(self) -> bool:
        return bool(self.expires_at) and datetime.now(timezone.utc) >= self.expires_at

    def can_attempt(self) -> bool:
        return (
            self.problem is not None
            and not self.completed
            and not self.is_expired()
            and self.attempts_left() > 0
        )

    def record_attempt(self):
        self.attempts_used += 1
        self.status = "running"

    def set_last_result(self, result: dict[str, Any]):
        self.last_result = result
        self.status = result.get("mode", "run")

    def finish(self, *, status: str, reason: str):
        self.status = status
        self.completed = True
        self.completion_reason = reason


# ─── Session State ────────────────────────────────────────────────────────────

@dataclass
class SessionState:
    session_id:        str
    phase:             ConversationPhase = ConversationPhase.INFO_PENDING
    created_at:        datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed_at:  datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Candidate data
    candidate:         CandidateInfo = field(default_factory=CandidateInfo)

    # Token
    info_token_enabled: bool = False          # True = Phase 1 unlocked

    # Interview tracking
    questions:         List[InterviewQuestion] = field(default_factory=list)
    current_question_index: int = 0
    deviation_count:   int = 0                # Max 3 before termination
    final_interview_assessment: Optional[FinalInterviewAssessment] = None
    coding_round:      CodingRoundState = field(default_factory=CodingRoundState)

    # Message history (for LLM context window)
    history:           List[dict] = field(default_factory=list)

    # Termination reason
    terminated_reason: Optional[str] = None   # "completed" | "deviation_limit" | "voluntary_exit"

    def touch(self):
        self.last_accessed_at = datetime.now(timezone.utc)

    def is_expired(self, now: datetime | None = None) -> bool:
        current_time = now or datetime.now(timezone.utc)
        return (current_time - self.last_accessed_at) >= SESSION_TTL

    # ── Token Management ─────────────────────────────────────────────────────

    def enable_info_token(self):
        """
        Called when the LLM confirms all candidate info is collected.
        Transitions: INFO_PENDING → INFO_COLLECTED
        """
        if not self.info_token_enabled:
            self.info_token_enabled = True
            self.phase = ConversationPhase.INFO_COLLECTED

    def start_interview(self, questions: List[dict]):
        """
        Called after questions are generated.
        Transitions: INFO_COLLECTED → INTERVIEWING
        """
        self.questions = [
            InterviewQuestion(
                id=q["id"],
                technology=q["technology"],
                difficulty=q["difficulty"],
                focus_area=q.get("focus_area", q["technology"]),
                question=q["question"],
                evaluation_rubric=q.get("evaluation_rubric", []),
            )
            for q in questions
        ]
        self.current_question_index = 0
        self.final_interview_assessment = None
        self.phase = ConversationPhase.INTERVIEWING

    # ── Deviation Management ─────────────────────────────────────────────────

    def record_deviation(self) -> int:
        """
        Increments deviation counter.
        Returns the new deviation count.
        """
        self.deviation_count += 1
        return self.deviation_count

    def is_deviation_limit_reached(self) -> bool:
        return self.deviation_count >= 3

    # ── Question Flow ────────────────────────────────────────────────────────

    def get_current_question(self) -> Optional[InterviewQuestion]:
        if self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None

    def advance_question(self):
        """Mark current question answered and move to next."""
        if self.current_question_index < len(self.questions):
            self.questions[self.current_question_index].answered = True
            self.current_question_index += 1

    def record_answer_review(self, answer: str, review_data: dict) -> Optional[InterviewAnswerReview]:
        question = self.get_current_question()
        if not question:
            return None

        question.candidate_answer = answer.strip()
        question.review = InterviewAnswerReview(
            question_id=question.id,
            question=question.question,
            technology=question.technology,
            focus_area=question.focus_area,
            technical_score=float(review_data.get("technical_score", 0)),
            explanation_score=float(review_data.get("explanation_score", 0)),
            communication_score=float(review_data.get("communication_score", 0)),
            overall_score=float(review_data.get("overall_score", 0)),
            verdict=str(review_data.get("verdict", "Needs improvement")).strip() or "Needs improvement",
            review=str(review_data.get("review", "")).strip(),
            strengths=list(review_data.get("strengths", [])),
            improvements=list(review_data.get("improvements", [])),
            communication_notes=str(review_data.get("communication_notes", "")).strip(),
        )
        return question.review

    def get_answer_reviews(self) -> List[InterviewAnswerReview]:
        return [question.review for question in self.questions if question.review]

    def set_final_interview_assessment(self, assessment_data: dict):
        self.final_interview_assessment = FinalInterviewAssessment(
            status=str(assessment_data.get("status", "Assessment pending")).strip() or "Assessment pending",
            readiness_score=float(assessment_data.get("readiness_score", 0)),
            technical_depth_score=float(assessment_data.get("technical_depth_score", 0)),
            communication_score=float(assessment_data.get("communication_score", 0)),
            summary=str(assessment_data.get("summary", "")).strip(),
            strengths=list(assessment_data.get("strengths", [])),
            improvement_areas=list(assessment_data.get("improvement_areas", [])),
            recommended_actions=list(assessment_data.get("recommended_actions", [])),
            coverage_note=str(assessment_data.get("coverage_note", "")).strip() or None,
        )

    def all_questions_answered(self) -> bool:
        return (
            len(self.questions) > 0
            and self.current_question_index >= len(self.questions)
        )

    def start_coding_round(self, problem: dict[str, Any], duration_minutes: int, max_attempts: int):
        self.coding_round.start(problem, duration_minutes, max_attempts)
        self.phase = ConversationPhase.CODING_ROUND

    def finish_coding_round(self, *, status: str, reason: str, close_session: bool = False):
        self.coding_round.finish(status=status, reason=reason)
        if close_session:
            self.close(reason)

    # ── Session Close ────────────────────────────────────────────────────────

    def close(self, reason: str):
        """
        Transitions to CLOSED phase.
        reason: "completed" | "deviation_limit" | "voluntary_exit"
        """
        self.phase = ConversationPhase.CLOSED
        self.terminated_reason = reason

    # ── History Management ───────────────────────────────────────────────────

    def add_message(self, role: str, content: str):
        """Append a message to the conversation history."""
        self.history.append({"role": role, "content": content})

    def get_history(self) -> List[dict]:
        return self.history

    # ── LLM Marker Parsing ───────────────────────────────────────────────────

    @staticmethod
    def parse_markers(llm_response: str) -> dict:
        """
        Scans the LLM output for control markers and returns what was found.

        Markers:
          [INFO_TOKEN: ENABLED]         → candidate info complete
          [DEVIATION_COUNT: N]          → deviation occurred, count=N
          [SESSION_TERMINATED]          → boot the user
          [INTERVIEW_COMPLETE]          → all questions done
        """
        import re
        found = {
            "info_token_enabled":  False,
            "deviation_count":     None,
            "session_terminated":  False,
            "interview_complete":  False,
        }

        if "[INFO_TOKEN: ENABLED]" in llm_response:
            found["info_token_enabled"] = True

        match = re.search(r"\[DEVIATION_COUNT:\s*(\d+)\]", llm_response)
        if match:
            found["deviation_count"] = int(match.group(1))

        if "[SESSION_TERMINATED]" in llm_response:
            found["session_terminated"] = True

        if "[INTERVIEW_COMPLETE]" in llm_response:
            found["interview_complete"] = True

        return found

    @staticmethod
    def strip_markers(text: str) -> str:
        """Remove internal control markers before sending reply to user."""
        import re
        text = re.sub(r"\[INFO_TOKEN:\s*ENABLED\]", "", text)
        text = re.sub(r"\[DEVIATION_COUNT:\s*\d+\]", "", text)
        text = re.sub(r"\[SESSION_TERMINATED\]", "", text)
        text = re.sub(r"\[INTERVIEW_COMPLETE\]", "", text)
        return text.strip()


# ─── In-memory session store (replace with Redis/DB in production) ───────────

_sessions: dict[str, SessionState] = {}


def _purge_expired_sessions(now: datetime | None = None):
    current_time = now or datetime.now(timezone.utc)
    expired_session_ids = [
        session_id
        for session_id, session in _sessions.items()
        if session.is_expired(current_time)
    ]
    for session_id in expired_session_ids:
        _sessions.pop(session_id, None)


def create_session(session_id: str) -> SessionState:
    """Create a brand-new session."""
    _purge_expired_sessions()
    session = SessionState(session_id=session_id)
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[SessionState]:
    """Retrieve an existing session if it is still active."""
    _purge_expired_sessions()
    session = _sessions.get(session_id)
    if session is None:
        return None
    session.touch()
    return session


def delete_session(session_id: str):
    """Clean up session data (GDPR compliance — call after session closes)."""
    _sessions.pop(session_id, None)
