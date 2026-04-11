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
    answered:    bool = False


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

    # Candidate data
    candidate:         CandidateInfo = field(default_factory=CandidateInfo)

    # Token
    info_token_enabled: bool = False          # True = Phase 1 unlocked

    # Interview tracking
    questions:         List[InterviewQuestion] = field(default_factory=list)
    current_question_index: int = 0
    deviation_count:   int = 0                # Max 3 before termination
    coding_round:      CodingRoundState = field(default_factory=CodingRoundState)

    # Message history (for LLM context window)
    history:           List[dict] = field(default_factory=list)

    # Termination reason
    terminated_reason: Optional[str] = None   # "completed" | "deviation_limit" | "voluntary_exit"

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
                question=q["question"],
            )
            for q in questions
        ]
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


def get_or_create_session(session_id: str) -> SessionState:
    """Retrieve existing session or create a fresh one."""
    if session_id not in _sessions:
        _sessions[session_id] = SessionState(session_id=session_id)
    return _sessions[session_id]


def delete_session(session_id: str):
    """Clean up session data (GDPR compliance — call after session closes)."""
    _sessions.pop(session_id, None)
