"""
virtual_teacher.py — World-Class Virtual Teacher for OmniScholar

Dr. Omni delivers lessons with:
  - Progressive section-by-section delivery
  - Mid-lesson Socratic questions (active recall, not passive reading)
  - Auto-generated Mermaid diagrams
  - Enhanced expressive avatar with emotion states
  - Web Speech API with speed/pause control
  - Hint system (3 levels)
  - Lesson memory across topics
  - Full lesson recap card
  - Related topic suggestions
"""

import concurrent.futures
import json
import re
import time
import uuid

import streamlit as st
import streamlit.components.v1 as components

from prompt import (
    VIRTUAL_TEACHER_PROMPT,
    VIRTUAL_TEACHER_EVAL_PROMPT,
    VIRTUAL_TEACHER_SOCRATIC_FOLLOWUP,
    VIRTUAL_TEACHER_RECAP_PROMPT,
)
from rag import retrieve_context, retrieve_context_hybrid


# ── Lesson memory across topics in session ────────────────────────────────────

def _get_lesson_memory() -> list:
    if "vt_lesson_memory" not in st.session_state:
        st.session_state["vt_lesson_memory"] = []
    return st.session_state["vt_lesson_memory"]


def _add_to_memory(topic: str, key_points: list):
    memory = _get_lesson_memory()
    memory.append({"topic": topic, "points": key_points})
    if len(memory) > 10:
        memory.pop(0)


# ── Lesson validation ─────────────────────────────────────────────────────────

def _validate_lesson(lesson: dict) -> tuple[bool, str]:
    """
    Validate a generated lesson dict.
    Returns (is_valid: bool, reason: str).
    """
    if not isinstance(lesson, dict):
        return False, "lesson is not a dict"

    checks = [
        ("hook",            str,  20, "hook too short"),
        ("explanation",     str,  50, "explanation too short"),
        ("worked_example",  str,  30, "worked_example too short"),
        ("exam_hook",       list,  1, "exam_hook has no items"),
        ("check_questions", list,  1, "check_questions has no items"),
    ]

    for key, typ, min_val, reason in checks:
        val = lesson.get(key)
        if val is None:
            return False, f"missing key: {key}"
        if typ == str:
            if not isinstance(val, str) or len(val.strip()) < min_val:
                return False, reason
        elif typ == list:
            if not isinstance(val, list) or len(val) < min_val:
                return False, reason

    return True, "ok"


VALID_MERMAID_STARTS = (
    "flowchart", "graph", "sequenceDiagram",
    "stateDiagram", "classDiagram", "erDiagram",
    "gantt", "pie", "gitGraph", "mindmap", "timeline",
)


def _should_use_llm_diagram(diagram: str) -> bool:
    """
    Return True only if the LLM-generated diagram is usable Mermaid.
    Falls back to _make_topic_diagram() when False.
    """
    if not diagram or len(diagram.strip()) < 50:
        return False
    stripped = diagram.strip()
    starts_valid = any(stripped.lower().startswith(k) for k in VALID_MERMAID_STARTS)
    has_artifact = "{topic}" in diagram or "{name}" in diagram
    return starts_valid and not has_artifact


def _make_topic_diagram(topic: str) -> str:
    """Return a topic-aware Mermaid fallback diagram with technical labels."""
    t = (topic or "").lower()

    if "deadlock" in t:
        return """flowchart TD
    P1[Process P1] -->|holds| R1[Resource A]
    P1 -->|waiting for| R2[Resource B]
    P2[Process P2] -->|holds| R2[Resource B]
    P2 -->|waiting for| R1[Resource A]
    style P1 fill:#1A2540,stroke:#00D4FF,color:#E8F0FF
    style P2 fill:#1A2540,stroke:#FFB800,color:#E8F0FF
    style R1 fill:#0D1B35,stroke:#EF4444,color:#E8F0FF
    style R2 fill:#0D1B35,stroke:#EF4444,color:#E8F0FF"""

    if "binary search tree" in t or "bst" in t:
        return """graph TD
    A50[50] --> A30[30]
    A50 --> A70[70]
    A30 --> A20[20]
    A30 --> A40[40]
    A70 --> A60[60]
    A70 --> A80[80]
    style A50 fill:#1A2540,stroke:#00D4FF,color:#E8F0FF
    style A30 fill:#1A2540,stroke:#00D4FF,color:#E8F0FF
    style A70 fill:#1A2540,stroke:#00D4FF,color:#E8F0FF"""

    if "bubble sort" in t or "merge sort" in t or "quick sort" in t or "sort" in t:
        return """flowchart TD
    A[Start: Unsorted Array] --> B[Compare Adjacent Elements]
    B --> C{arr[i] > arr[i+1]?}
    C -->|Yes| D[Swap Elements]
    C -->|No| E[Move to Next Pair]
    D --> E
    E --> F{End of Pass?}
    F -->|No| B
    F -->|Yes| G{Array Sorted?}
    G -->|No| B
    G -->|Yes| H[End: Sorted Array]
    style A fill:#1A2540,stroke:#00D4FF,color:#E8F0FF
    style H fill:#0D1B35,stroke:#00C850,color:#E8F0FF
    style C fill:#0D1B35,stroke:#FFB800,color:#E8F0FF"""

    if "binary search" in t:
        return """flowchart TD
    A[Sorted Array + Target] --> B[low=0, high=n-1]
    B --> C{low <= high?}
    C -->|No| G[Return -1 Not Found]
    C -->|Yes| D[mid = (low + high) // 2]
    D --> E{arr[mid] == target?}
    E -->|Yes| F[Return mid FOUND]
    E -->|arr[mid] < target| H[low = mid + 1]
    E -->|arr[mid] > target| I[high = mid - 1]
    H --> C
    I --> C
    style A fill:#1A2540,stroke:#00D4FF,color:#E8F0FF
    style F fill:#0D1B35,stroke:#00C850,color:#E8F0FF
    style G fill:#0D1B35,stroke:#EF4444,color:#E8F0FF"""

    if "oop" in t or "inherit" in t or "polymorphism" in t or "encapsulation" in t or "class" in t:
        return """classDiagram
    Animal <|-- Dog
    Animal <|-- Cat
    Animal : +String name
    Animal : +int age
    Animal : +makeSound()
    Animal : +move()
    Dog : +String breed
    Dog : +fetch()
    Dog : +makeSound() Woof
    Cat : +String color
    Cat : +purr()
    Cat : +makeSound() Meow"""

    if "linked list" in t:
        return """flowchart LR
    H[Head] --> N1[Data:10 Next]
    N1 --> N2[Data:20 Next]
    N2 --> N3[Data:30 Next]
    N3 --> T[NULL]
    style H fill:#1A2540,stroke:#00D4FF,color:#E8F0FF
    style N1 fill:#1A2540,stroke:#FFB800,color:#E8F0FF
    style N2 fill:#1A2540,stroke:#FFB800,color:#E8F0FF
    style N3 fill:#1A2540,stroke:#FFB800,color:#E8F0FF
    style T fill:#0D1B35,stroke:#EF4444,color:#E8F0FF"""

    if "stack" in t:
        return """flowchart TD
    TOP[TOP: 30 most recent] --> N2[20]
    N2 --> BOTTOM[BOTTOM: 10 first pushed]
    PUSH[push 40] -->|goes to TOP| TOP
    TOP -->|pop removes| POP[pop returns 30]
    style TOP fill:#1A2540,stroke:#00C850,color:#E8F0FF
    style BOTTOM fill:#1A2540,stroke:#00D4FF,color:#E8F0FF
    style PUSH fill:#0D1B35,stroke:#FFB800,color:#E8F0FF"""

    if "queue" in t:
        return """flowchart LR
    EN[enqueue adds here] --> REAR[REAR: 30]
    REAR --> N2[20]
    N2 --> FRONT[FRONT: 10]
    FRONT --> DE[dequeue removes here]
    style REAR fill:#1A2540,stroke:#FFB800,color:#E8F0FF
    style FRONT fill:#1A2540,stroke:#00C850,color:#E8F0FF
    style EN fill:#0D1B35,stroke:#00D4FF,color:#E8F0FF"""

    if "process state" in t or "process lifecycle" in t:
        return """stateDiagram-v2
    [*] --> New: fork()
    New --> Ready: admitted
    Ready --> Running: scheduler dispatch
    Running --> Ready: time quantum expired
    Running --> Blocked: I/O request
    Blocked --> Ready: I/O complete
    Running --> Terminated: exit()
    Terminated --> [*]"""

    if "tcp" in t or "handshake" in t or "network" in t:
        return """sequenceDiagram
    participant C as Client
    participant S as Server
    C->>S: SYN (seq=x)
    S->>C: SYN-ACK (seq=y, ack=x+1)
    C->>S: ACK (ack=y+1)
    Note over C,S: Connection Established
    C->>S: Data Transfer
    S->>C: ACK"""

    if "recursion" in t or "recursive" in t:
        return """flowchart TD
    A[factorial 5: n=5] -->|calls| B[factorial 4: n=4]
    B -->|calls| C[factorial 3: n=3]
    C -->|calls| D[factorial 2: n=2]
    D -->|calls| E[factorial 1: n=1 BASE CASE]
    E -->|returns 1| D
    D -->|returns 2| C
    C -->|returns 6| B
    B -->|returns 24| A
    A -->|returns 120| F[Result: 120]
    style A fill:#1A2540,stroke:#00D4FF,color:#E8F0FF
    style E fill:#0D1B35,stroke:#00C850,color:#E8F0FF
    style F fill:#0D1B35,stroke:#FFB800,color:#E8F0FF"""

    if t == "os" or "operating system" in t:
        return """stateDiagram-v2
    [*] --> New: fork()
    New --> Ready: admitted
    Ready --> Running: scheduler dispatch
    Running --> Ready: time quantum expired
    Running --> Blocked: I/O request
    Blocked --> Ready: I/O complete
    Running --> Terminated: exit()
    Terminated --> [*]"""

    if "hash" in t or "hashing" in t:
        return """flowchart TD
    K1[Key: apple] -->|hash mod 7| B0[Bucket 0]
    K2[Key: banana] -->|hash mod 7| B2[Bucket 2]
    K3[Key: cherry] -->|hash mod 7| B2
    B2 -->|chaining| C1[banana]
    C1 --> C2[cherry: collision]
    K4[Key: date] -->|hash mod 7| B5[Bucket 5]
    style K1 fill:#1A2540,stroke:#00D4FF,color:#E8F0FF
    style B2 fill:#0D1B35,stroke:#FFB800,color:#E8F0FF
    style C2 fill:#0D1B35,stroke:#EF4444,color:#E8F0FF"""

    if t == "graph" or ("graph" in t and "bst" not in t and "binary" not in t):
        return """flowchart LR
    A((A)) -->|edge| B((B))
    A -->|edge| C((C))
    B -->|edge| D((D))
    C -->|edge| D
    D -->|edge| E((E))
    style A fill:#1A2540,stroke:#00D4FF,color:#E8F0FF
    style E fill:#0D1B35,stroke:#00C850,color:#E8F0FF"""

    if t == "tree" or ("tree" in t and "bst" not in t and "binary search" not in t):
        return """flowchart TD
    Root[Root] --> L1A[Child A]
    Root --> L1B[Child B]
    Root --> L1C[Child C]
    L1A --> L2A[Leaf 1]
    L1A --> L2B[Leaf 2]
    L1B --> L2C[Leaf 3]
    L1C --> L2D[Leaf 4]
    style Root fill:#1A2540,stroke:#00D4FF,color:#E8F0FF
    style L2A fill:#0D1B35,stroke:#00C850,color:#E8F0FF"""

    if "pointer" in t or "memory address" in t:
        return """flowchart LR
    V[int x = 42 at 0x1000] -->|address stored in| P[int* p = 0x1000]
    P -->|dereference *p| V
    V2[int y = 99 at 0x1008]
    P2[int* q = 0x1008] -->|dereference *q| V2
    style V fill:#1A2540,stroke:#00D4FF,color:#E8F0FF
    style P fill:#0D1B35,stroke:#FFB800,color:#E8F0FF
    style P2 fill:#0D1B35,stroke:#FFB800,color:#E8F0FF"""

    if "recursion" in t or "recursive" in t:
        return """flowchart TD
    A[factorial_5 n=5] --> B[factorial_4 n=4]
    B --> C[factorial_3 n=3]
    C --> D[factorial_2 n=2]
    D --> E[factorial_1 n=1 BASE CASE returns 1]
    E --> D2[returns 1×1=1]
    D2 --> C2[returns 2×1=2]
    C2 --> B2[returns 3×2=6]
    B2 --> A2[returns 4×6=24]
    A2 --> Result[factorial_5 returns 120]
    style A fill:#1A2540,stroke:#00B4A6,color:#E8F0FF
    style E fill:#0D1B35,stroke:#39FF14,color:#E8F0FF
    style Result fill:#0D1B35,stroke:#D4A24C,color:#E8F0FF"""

    return (
        f"flowchart TD\n"
        f"    A[{topic[:35]}] --> B[Core Definition]\n"
        f"    A --> C[Key Operations]\n"
        f"    A --> D[Complexity]\n"
        f"    B --> E[Example Use Case]\n"
        f"    C --> E\n"
        f"    style A fill:#1A2540,stroke:#00D4FF,color:#E8F0FF\n"
        f"    style E fill:#0D1B35,stroke:#00C850,color:#E8F0FF\n"
        f"    style B fill:#0D1B35,stroke:#FFB800,color:#E8F0FF\n"
        f"    style C fill:#0D1B35,stroke:#FFB800,color:#E8F0FF\n"
    )


# ── VirtualTeacher class ──────────────────────────────────────────────────────

class VirtualTeacher:
    def __init__(self, ollama_client, db, rag=None):
        self.client = ollama_client
        self.db = db

    # ── Core lesson generation ────────────────────────────────────────────────

    def teach(self, topic: str, subject: str, student_id: str,
              language: str, simple_prompt: bool = False) -> dict:
        """Single call returns lesson + diagram spec + mid-question together.
        
        simple_prompt=True uses a reduced prompt for slow hardware / complex topics.
        """
        try:
            rag_context, sources = retrieve_context_hybrid(topic, subject, n_results=3)
        except Exception:
            rag_context, sources = "", []

        if simple_prompt:
            # Bug 5: simplified prompt — fewer fields, lower token load
            combined_prompt = (
                "You are Dr. Omni teaching {topic} in {subject}.\n"
                "Student language: {language}\n\n"
                "Return ONLY this JSON (no text outside it):\n"
                "{{\n"
                "  \"hook\": \"1-2 sentences introducing {topic}. In {language}.\",\n"
                "  \"explanation\": \"2 paragraphs explaining {topic}. In {language}.\",\n"
                "  \"worked_example\": \"1 worked example with actual values. In {language}.\",\n"
                "  \"exam_hook\": [\n"
                "    \"Exam question 1 about {topic}.\",\n"
                "    \"Exam question 2 about {topic}.\"\n"
                "  ],\n"
                "  \"check_questions\": [\n"
                "    {{\"question\": \"What is {topic}?\", \"expected_key_points\": \"core definition\"}}\n"
                "  ],\n"
                "  \"diagram_spec\": {{\"mermaid_code\": \"\", \"type\": \"\", \"title\": \"\"}},\n"
                "  \"mid_question\": {{\n"
                "    \"question\": \"Explain {topic} in your own words.\",\n"
                "    \"expected\": \"basic definition and one example\",\n"
                "    \"hint\": \"Focus on the core concept first.\"\n"
                "  }}\n"
                "}}"
            ).format(topic=topic, subject=subject, language=language)
        else:
            combined_prompt = (
                "You are Dr. Omni teaching {topic} in {subject}.\n"
                "Student language: {language}\n\n"
                "Study materials:\n"
                "{rag_context}\n\n"
                "Return ONLY this JSON (no text outside it):\n"
                "{{\n"
                "  \"hook\": \"2-3 sentences. Real-world analogy from Sri Lankan daily life. In {language}.\",\n"
                "  \"explanation\": \"150 words max. Definition \u2192 mechanism \u2192 complexity (if CS) \u2192 Sri Lankan example \u2192 exam trap. In {language}.\",\n"
                "  \"worked_example\": \"Step-by-step trace with ACTUAL VALUES, not placeholders. Every step annotated. In {language}.\",\n"
                "  \"exam_hook\": [\n"
                "    \"Examiner Q1: Define/State \u2014 In {language}.\",\n"
                "    \"Examiner Q2: Compare/Distinguish \u2014 In {language}.\",\n"
                "    \"Examiner Q3: Apply/Trace \u2014 In {language}.\"\n"
                "  ],\n"
                "  \"check_questions\": [\n"
                "    {{\"question\": \"Recall question in {language}.\", \"expected_key_points\": \"2-3 specific technical points\"}},\n"
                "    {{\"question\": \"Application scenario question in {language}.\", \"expected_key_points\": \"specific steps expected\"}}\n"
                "  ],\n"
                "  \"diagram_spec\": {{\n"
                "    \"type\": \"flowchart TD or classDiagram or sequenceDiagram or stateDiagram-v2\",\n"
                "    \"mermaid_code\": \"REQUIRED: Real Mermaid diagram. Use ACTUAL technical terms for {topic}.\",\n"
                "    \"title\": \"Visual: {topic}\"\n"
                "  }},\n"
                "  \"mid_question\": {{\n"
                "    \"question\": \"Quick check \u2014 one probe question testing core mechanism. In {language}.\",\n"
                "    \"expected\": \"2-3 specific points the answer must contain\",\n"
                "    \"hint\": \"One directional hint without giving the answer. In {language}.\"\n"
                "  }}\n"
                "}}"
            ).format(
                topic=topic,
                subject=subject,
                language=language,
                rag_context=rag_context or "No materials uploaded \u2014 use curriculum knowledge.",
            )

        try:
            from telemetry import timed as _timed
            _ctx = _timed("teach_latency", metadata=f"topic={topic[:30]}")
        except Exception:
            from contextlib import nullcontext
            _ctx = nullcontext()

        # Bug 1: hard 90-second timeout on lesson call; num_predict capped at 1024
        raw = None
        _timed_out = False
        try:
            with _ctx:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _pool:
                    _future = _pool.submit(
                        self.client.chat,
                        messages=[{"role": "user", "content": combined_prompt}],
                        system_prompt="",
                        temperature=0.9,
                        num_ctx=3072,
                        num_predict=1024,
                    )
                    try:
                        raw = _future.result(timeout=90)
                    except concurrent.futures.TimeoutError:
                        _timed_out = True
                        raw = None
        except Exception as exc:
            raw = None

        if _timed_out or raw is None:
            # Return a sentinel so the UI can detect the timeout
            return {"_timeout": True, "_topic": topic, "_subject": subject, "_language": language}

        lesson = self._parse_lesson(raw, topic)
        lesson["_sources"] = sources
        lesson["_topic"] = topic
        lesson["_subject"] = subject
        lesson["_language"] = language

        # Bug 3: validate diagram from LLM before using it
        _valid_mermaid_starts = (
            "flowchart", "graph", "sequenceDiagram", "stateDiagram",
            "classDiagram", "erDiagram", "gantt", "pie", "gitGraph",
        )
        diagram_spec = lesson.pop("diagram_spec", {})
        mermaid_code = diagram_spec.get("mermaid_code", "").strip() if diagram_spec else ""
        _use_llm_diagram = (
            len(mermaid_code) > 50
            and any(mermaid_code.startswith(kw) for kw in _valid_mermaid_starts)
            and "{topic}" not in mermaid_code
            and "{" not in mermaid_code.split("\n")[0]  # no f-string artifacts in first line
        )
        lesson["_diagram"] = mermaid_code if _use_llm_diagram else _make_topic_diagram(topic)
        lesson["_mid_question"] = lesson.pop("mid_question", {})

        return lesson

    # ── Socratic follow-up ────────────────────────────────────────────────────

    def get_socratic_followup(self, topic: str, question: str,
                              student_answer: str, expected: str) -> dict:
        """After wrong answer: don't correct, ask probing question."""
        prompt = VIRTUAL_TEACHER_SOCRATIC_FOLLOWUP.format(
            topic=topic, question=question,
            student_answer=student_answer, expected=expected,
        )
        try:
            raw = self.client.fast_chat(
                message=prompt,
                system="Return only valid JSON. No markdown.",
                max_tokens=200,
            )
            raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            return json.loads(raw)
        except Exception:
            return {
                "acknowledgement": "Not quite.",
                "probing_question": f"Think about what {topic} means fundamentally.",
                "nudge": "Focus on the core definition first.",
            }

    # ── Lesson recap ──────────────────────────────────────────────────────────

    def generate_recap(self, topic: str, subject: str) -> dict:
        """Generate a 5-point recap card at end of lesson."""
        prompt = VIRTUAL_TEACHER_RECAP_PROMPT.format(
            topic=topic, subject=subject
        )
        try:
            raw = self.client.fast_chat(
                message=prompt,
                system="Return only valid JSON. No markdown.",
                max_tokens=600,
            )
            raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            return json.loads(raw)
        except Exception:
            return {
                "title": f"Lesson Recap: {topic}",
                "points": [f"Key concept {i+1} of {topic}" for i in range(5)],
                "exam_one_liner": f"{topic} is a fundamental concept in {subject}.",
                "related_topics": [],
                "memory_trick": f"Remember {topic} as a core building block.",
            }

    # ── Answer evaluation ─────────────────────────────────────────────────────

    def evaluate_check_answer(self, question: str, student_answer: str,
                              topic: str, student_id: str, language: str,
                              expected_key_points: str = "",
                              subject: str = "") -> dict:
        """Evaluate answer. Writes weakness to DB if detected."""
        eval_prompt = VIRTUAL_TEACHER_EVAL_PROMPT.format(
            question=question,
            expected_key_points=expected_key_points or "basic understanding",
            student_answer=student_answer,
            language=language,
            subject=subject or "the subject",
            topic=topic,
        )
        try:
            raw = self.client.fast_chat(
                message=eval_prompt,
                system="Return only valid JSON. No markdown.",
                max_tokens=150,
            )
        except Exception as exc:
            return {"correct": False,
                    "feedback": f"Evaluation unavailable ({exc})",
                    "weakness": None}

        try:
            result = json.loads(raw)
        except Exception:
            m = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
            result = json.loads(m.group()) if m else {}

        correct = bool(result.get("correct", False))
        feedback = str(result.get("feedback", raw[:200]))
        weakness = result.get("weakness") or None

        if weakness and student_id and self.db:
            try:
                self.db.upsert_weak_concept(
                    student_id=student_id, concept=weakness,
                    topic=topic, error_type="comprehension_error",
                )
            except Exception:
                pass

        # ── Safety eval + telemetry ─────────────────────────────────────
        try:
            from tutor_eval import score_tutor_response
            from telemetry import log_event
            eval_result = score_tutor_response(student_answer, feedback)
            if self.db:
                self.db.log_tutor_quality(
                    student_id=student_id,
                    topic=topic,
                    harm_flags=eval_result["harm_flags"],
                    scaffolding_score=eval_result["scaffolding_score"],
                    grounding_score=eval_result["grounding_score"],
                    overall_quality=eval_result["overall_quality"],
                )
            log_event("tutor_eval", metadata=f"quality={eval_result['overall_quality']}")
            # Expose for sidebar quality badge
            import streamlit as _st
            _st.session_state["_last_tutor_quality"] = eval_result
        except Exception:
            pass

        return {"correct": correct, "feedback": feedback, "weakness": weakness}

    def detect_zpd_level(self, topic: str, student_id: str,
                          correct_streak: int, wrong_streak: int) -> str:
        """
        Detect Vygotsky ZPD floor and ceiling.
        Returns: 'too_easy' | 'in_zpd' | 'too_hard' | 'mastered'
        Based on last 5 answers pattern.
        """
        if correct_streak >= 3:
            return "mastered"
        elif correct_streak >= 2 and wrong_streak == 0:
            return "in_zpd"
        elif wrong_streak >= 2:
            return "too_hard"
        elif wrong_streak == 0 and correct_streak == 1:
            return "in_zpd"
        else:
            return "too_hard"

    def get_next_topic_recommendation(self, topic: str, subject: str,
                                       zpd_status: str) -> str:
        """Based on ZPD status, recommend what to study next."""
        if zpd_status == "mastered":
            return f"Ready to advance beyond {topic}"
        elif zpd_status == "too_hard":
            return f"Review prerequisites of {topic} first"
        else:
            return f"Continue practicing {topic} — you're in the learning zone"

    def _generate_mid_question_fast(
        self,
        topic: str,
        subject: str,
        language: str,
    ) -> dict:
        """Fast mid-lesson check question using the quick model. Runs in parallel with teach()."""
        prompt = (
            f"Generate ONE mid-lesson check question about "
            f"'{topic}' for a {subject} student studying in "
            f"{language}. The question should test the CORE concept, "
            f"not trivial details.\n\n"
            f"Respond ONLY with valid JSON, no markdown:\n"
            f'{{"question": "...", '
            f'"expected_key_points": "...key points the answer must cover...", '
            f'"difficulty": "medium"}}'
        )
        result = self.client.fast_chat(
            message=prompt,
            system=(
                "You are an exam question generator. "
                "Return ONLY valid JSON. No preamble. "
                "No markdown. No backticks."
            ),
            max_tokens=256,
        )
        try:
            clean = re.sub(r'```json|```|\n', '', result).strip()
            match = re.search(r'\{.*\}', clean, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(clean)
        except Exception:
            return {
                "question": (
                    f"In your own words, explain the core concept "
                    f"of {topic} and give one real-world example."
                ),
                "expected_key_points": (
                    f"Should cover: definition of {topic}, "
                    f"key mechanism, practical application"
                ),
                "difficulty": "medium",
            }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _parse_lesson(self, raw: str, topic: str) -> dict:
        """Parse lesson JSON from model response. Handles all fence variants."""
        if not raw or not raw.strip():
            return self._fallback_lesson(topic, "empty response")

        # Strip ALL markdown fence variants before parsing
        text = raw.strip()
        for fence in ["```json", "```JSON", "```", "~~~json", "~~~"]:
            if text.startswith(fence):
                text = text[len(fence):].strip()
                break
        for fence in ["```", "~~~"]:
            if text.endswith(fence):
                text = text[:-len(fence)].strip()
                break

        # Try direct JSON parse
        try:
            result = json.loads(text)
            if isinstance(result, dict) and "explanation" in result:
                return result
        except Exception:
            pass

        # Try finding outermost { ... } object
        brace_start = text.find("{")
        brace_end   = text.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            try:
                result = json.loads(text[brace_start:brace_end + 1])
                if isinstance(result, dict):
                    return result
            except Exception:
                pass

        # All parsing failed — model returned plain text (not JSON)
        # Build a structured lesson from the plain text; NEVER put raw JSON in explanation
        return self._fallback_lesson(topic, plain_text=text[:600])

    def _fallback_lesson(self, topic: str, error=None, plain_text: str = "") -> dict:
        """Safe fallback lesson when JSON parsing fails."""
        explanation = plain_text if plain_text else (
            f"The model could not generate a structured lesson for {topic}. "
            f"Try asking: 'Explain {topic} in simple terms.'"
        )
        return {
            "hook": f"Let's explore {topic} together.",
            "explanation": explanation,
            "worked_example": f"Try asking: 'Give me a step-by-step example of {topic}'",
            "exam_hook": [
                f"Define {topic} and state its key properties.",
                f"Compare {topic} with a related concept.",
                f"Give a practical example of {topic} in action.",
            ],
            "check_questions": [
                {"question": f"In your own words, what is {topic}?",
                 "expected_key_points": "basic definition and purpose"},
                {"question": f"Give one real-world example of {topic}.",
                 "expected_key_points": "concrete, accurate example"},
            ],
            "diagram_spec": {
                "mermaid_code": _make_topic_diagram(topic),
                "type": "flowchart TD",
                "title": f"Visual: {topic}",
            },
            "mid_question": {
                "question": f"Quick check — can you explain {topic} in one sentence?",
                "expected": "basic definition in own words",
                "hint": f"Think about what {topic} does and why it exists.",
            },
        }


# ── Enhanced Avatar ───────────────────────────────────────────────────────────

def render_avatar_teacher(text: str = "", phase: str = "greeting",
                          emotion: str = "neutral",
                          show_speech_controls: bool = True,
                          student_name: str = "") -> None:
    """
    V3 Dr. Omni avatar — 3D-style emotional face with:
    - Emotions: neutral / happy / angry / thinking / excited / encouraging
    - Eyebrow paths, cheek blush, hair highlight, forehead shine
    - float + glow + blink CSS animations (UID-scoped)
    - Web Speech API with speed slider, pause/resume/stop
    - Phase-based color themes, DR. OMNI badge
    - Auto-emotion mapping from phase when emotion='neutral'
    """
    # Auto-map emotion from phase when not explicitly set
    phase_emotion_map = {
        "correct":     "happy",
        "wrong":       "angry",
        "questioning": "thinking",
        "recap":       "excited",
        "teaching":    "encouraging",
        "greeting":    "neutral",
    }
    if emotion == "neutral" and phase in phase_emotion_map:
        emotion = phase_emotion_map[phase]

    phase_config = {
        "greeting":    {"color": "#00D4FF", "label": "Ready to Teach",    "bg": "#001D35"},
        "teaching":    {"color": "#FFB800", "label": "Teaching",           "bg": "#1D1400"},
        "questioning": {"color": "#00C850", "label": "Question Time",      "bg": "#001D0D"},
        "waiting":     {"color": "#A0B4D6", "label": "Waiting",            "bg": "#0D1426"},
        "correct":     {"color": "#00C850", "label": "Excellent!",         "bg": "#001D0D"},
        "wrong":       {"color": "#EF4444", "label": "Let me guide you",   "bg": "#1D0000"},
        "recap":       {"color": "#9B59B6", "label": "Lesson Complete",    "bg": "#0D0020"},
    }
    cfg = phase_config.get(phase, phase_config["greeting"])
    color = cfg["color"]
    raw_label = cfg["label"]
    label = f"Hi {student_name}! · {raw_label}" if student_name else raw_label
    bg = cfg["bg"]

    # V3 emotion config: brow paths, mouth, eye height, cheek color, extra SVG
    emotions = {
        "neutral": {
            "brow_l": "M 26 24 Q 33 21 38 23",
            "brow_r": "M 52 23 Q 57 21 64 24",
            "mouth":  "M 27 38 Q 35 44 43 38",
            "eye_ry": "3.5",
            "cheek":  "transparent",
            "extra":  "",
        },
        "happy": {
            "brow_l": "M 26 22 Q 33 19 38 21",
            "brow_r": "M 52 21 Q 57 19 64 22",
            "mouth":  "M 24 37 Q 35 50 46 37",
            "eye_ry": "2.8",
            "cheek":  "#FF8888",
            "extra":  (
                '<text x="60" y="15" font-size="10" opacity="0.8">✨</text>'
                '<text x="6"  y="18" font-size="8"  opacity="0.7">⭐</text>'
            ),
        },
        "angry": {
            "brow_l": "M 26 26 Q 33 22 38 25",
            "brow_r": "M 52 25 Q 57 22 64 26",
            "mouth":  "M 27 42 Q 35 37 43 42",
            "eye_ry": "2.2",
            "cheek":  "#FF4444",
            "extra":  (
                '<line x1="28" y1="19" x2="32" y2="22" stroke="#EF4444" stroke-width="1.5"/>'
                '<line x1="52" y1="22" x2="56" y2="19" stroke="#EF4444" stroke-width="1.5"/>'
            ),
        },
        "thinking": {
            "brow_l": "M 26 24 Q 33 22 38 24",
            "brow_r": "M 52 22 Q 57 24 64 23",
            "mouth":  "M 30 40 Q 35 40 40 40",
            "eye_ry": "4.0",
            "cheek":  "transparent",
            "extra":  (
                '<circle cx="64" cy="18" r="3" fill="' + color + '" opacity="0.6">'
                '<animate attributeName="r" values="3;5;3" dur="1s" repeatCount="indefinite"/>'
                '</circle>'
                '<circle cx="70" cy="11" r="4" fill="' + color + '" opacity="0.4">'
                '<animate attributeName="r" values="4;6;4" dur="1s" begin="0.3s" repeatCount="indefinite"/>'
                '</circle>'
                '<circle cx="75" cy="5"  r="5" fill="' + color + '22" stroke="' + color + '" stroke-width="1">'
                '<animate attributeName="r" values="5;7;5" dur="1s" begin="0.6s" repeatCount="indefinite"/>'
                '</circle>'
            ),
        },
        "excited": {
            "brow_l": "M 26 21 Q 33 17 38 20",
            "brow_r": "M 52 20 Q 57 17 64 21",
            "mouth":  "M 23 36 Q 35 52 47 36",
            "eye_ry": "2.5",
            "cheek":  "#FFB800",
            "extra":  (
                '<text x="58" y="14" font-size="11" opacity="0.9">🎉</text>'
                '<text x="5"  y="20" font-size="9"  opacity="0.8">⭐</text>'
                '<text x="60" y="70" font-size="8"  opacity="0.6">✨</text>'
            ),
        },
        "encouraging": {
            "brow_l": "M 26 22 Q 33 20 38 22",
            "brow_r": "M 52 22 Q 57 20 64 22",
            "mouth":  "M 25 37 Q 35 47 45 37",
            "eye_ry": "3.8",
            "cheek":  "#88DDFF",
            "extra":  (
                '<text x="60" y="16" font-size="10" opacity="0.8">💡</text>'
            ),
        },
    }
    em = emotions.get(emotion, emotions["neutral"])
    mouth_d  = em["mouth"]
    eye_ry   = em["eye_ry"]
    brow_l   = em["brow_l"]
    brow_r   = em["brow_r"]
    cheek_c  = em["cheek"]
    extra_svg = em["extra"]

    safe = (text.replace("'", "\\'")
               .replace("\n", " ")
               .replace('"', '\\"')
               .replace("`", "'"))[:500]
    display = (text[:160] + "..." if len(text) > 160
               else text or "Enter a topic to begin your lesson.")
    uid = f"omni_{phase}_{hash(text) % 10000}"
    auto_speak = f"setTimeout(()=>speak_{uid}(),600);" if (phase in ("teaching", "questioning", "correct", "wrong") and text) else ""

    controls_html = ""
    if show_speech_controls and text:
        controls_html = f"""
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          <button onclick="speak_{uid}()" id="btn_speak_{uid}"
                  style="padding:5px 14px;background:{color}22;color:{color};
                         border:1px solid {color}55;border-radius:8px;
                         cursor:pointer;font-size:0.75rem;font-weight:600;">
            🔊 Listen
          </button>
          <button onclick="pause_{uid}()" id="btn_pause_{uid}"
                  style="padding:5px 10px;background:rgba(255,184,0,0.12);
                         color:#FFB800;border:1px solid rgba(255,184,0,0.3);
                         border-radius:8px;cursor:pointer;font-size:0.75rem;">
            ⏸
          </button>
          <button onclick="stopSpeech_{uid}()"
                  style="padding:5px 10px;background:rgba(239,68,68,0.1);
                         color:#EF4444;border:1px solid rgba(239,68,68,0.3);
                         border-radius:8px;cursor:pointer;font-size:0.75rem;">
            ⏹
          </button>
          <div style="display:flex;align-items:center;gap:6px;">
            <span style="font-size:0.65rem;color:#4A6080;">Speed:</span>
            <input type="range" id="speed_{uid}" min="0.5" max="1.8"
                   step="0.1" value="0.95"
                   style="width:70px;accent-color:{color};"
                   oninput="document.getElementById('spd_lbl_{uid}').innerText=this.value+'x'"/>
            <span id="spd_lbl_{uid}" style="font-size:0.65rem;color:{color};
                                             min-width:28px;">0.95x</span>
          </div>
        </div>
        """

    cheek_html = (
        f'<ellipse cx="28" cy="38" rx="6" ry="4" fill="{cheek_c}" opacity="0.35"/>'
        f'<ellipse cx="62" cy="38" rx="6" ry="4" fill="{cheek_c}" opacity="0.35"/>'
    ) if cheek_c not in ("transparent", "") else ""

    components.html(f"""
    <style>
      @keyframes float_{uid} {{
        0%,100% {{ transform: translateY(0px); }}
        50%      {{ transform: translateY(-5px); }}
      }}
      @keyframes glow_{uid} {{
        0%,100% {{ filter: drop-shadow(0 0 4px {color}55); }}
        50%      {{ filter: drop-shadow(0 0 12px {color}CC); }}
      }}
    </style>

    <div id="av_{uid}" style="display:flex;align-items:flex-start;gap:20px;
                padding:20px 24px;
                background:linear-gradient(135deg,{bg},{bg}dd);
                border:1px solid {color}55;border-radius:16px;margin:10px 0;
                font-family:'Segoe UI',sans-serif;
                box-shadow:0 0 24px {color}22;">

      <div style="flex-shrink:0;position:relative;
                  animation:float_{uid} 4s ease-in-out infinite,
                             glow_{uid} 3s ease-in-out infinite;">
        <svg id="svg_{uid}" width="90" height="115" viewBox="0 0 90 115">
          <defs>
            <radialGradient id="faceGrad_{uid}" cx="45%" cy="40%" r="55%">
              <stop offset="0%"   stop-color="#2A3F6A"/>
              <stop offset="100%" stop-color="#111929"/>
            </radialGradient>
            <radialGradient id="bodyGrad_{uid}" cx="50%" cy="30%" r="60%">
              <stop offset="0%"   stop-color="{color}44"/>
              <stop offset="100%" stop-color="{color}11"/>
            </radialGradient>
          </defs>

          <!-- glow ring -->
          <circle cx="45" cy="36" r="30" fill="none"
                  stroke="{color}" stroke-width="0.5" opacity="0.2">
            <animate attributeName="r"       values="30;35;30" dur="3s" repeatCount="indefinite"/>
            <animate attributeName="opacity" values="0.2;0.05;0.2" dur="3s" repeatCount="indefinite"/>
          </circle>

          <!-- body -->
          <ellipse cx="45" cy="86" rx="24" ry="20"
                   fill="url(#bodyGrad_{uid})" stroke="{color}" stroke-width="1.2">
            <animate attributeName="ry" values="20;22;20" dur="4s" repeatCount="indefinite"/>
          </ellipse>
          <path d="M 32 68 Q 45 75 58 68" fill="none"
                stroke="{color}" stroke-width="1.5" opacity="0.6"/>

          <!-- 3D face -->
          <circle cx="45" cy="36" r="26"
                  fill="url(#faceGrad_{uid})"
                  stroke="{color}" stroke-width="2"/>
          <!-- forehead shine -->
          <ellipse cx="40" cy="22" rx="8" ry="4"
                   fill="white" opacity="0.06"/>

          <!-- hair -->
          <path d="M 22 30 Q 20 12 45 10 Q 70 12 68 30"
                fill="{color}33" stroke="{color}" stroke-width="1.2"/>
          <path d="M 28 18 Q 35 12 45 11"
                fill="none" stroke="{color}99" stroke-width="2"
                stroke-linecap="round"/>

          <!-- cheeks -->
          {cheek_html}

          <!-- eyebrows -->
          <path d="{brow_l}" fill="none" stroke="{color}" stroke-width="2"
                stroke-linecap="round"/>
          <path d="{brow_r}" fill="none" stroke="{color}" stroke-width="2"
                stroke-linecap="round"/>

          <!-- eyes with blink -->
          <ellipse id="eye_L_{uid}" cx="34" cy="32"
                   rx="3.5" ry="{eye_ry}" fill="{color}">
            <animate attributeName="ry" values="{eye_ry};0.2;{eye_ry}"
                     dur="4s" begin="0s" repeatCount="indefinite"/>
          </ellipse>
          <ellipse id="eye_R_{uid}" cx="56" cy="32"
                   rx="3.5" ry="{eye_ry}" fill="{color}">
            <animate attributeName="ry" values="{eye_ry};0.2;{eye_ry}"
                     dur="4s" begin="0.05s" repeatCount="indefinite"/>
          </ellipse>
          <circle cx="35.5" cy="33" r="1.8" fill="#0A0F1E"/>
          <circle cx="57.5" cy="33" r="1.8" fill="#0A0F1E"/>
          <circle cx="36.5" cy="31.5" r="0.8" fill="white" opacity="0.85"/>
          <circle cx="58.5" cy="31.5" r="0.8" fill="white" opacity="0.85"/>

          <!-- nose bridge -->
          <path d="M 43 38 Q 45 42 47 38"
                fill="none" stroke="{color}55" stroke-width="1"
                stroke-linecap="round"/>

          <!-- mouth -->
          <path id="mouth_{uid}" d="{mouth_d}"
                stroke="{color}" stroke-width="2.5" fill="none"
                stroke-linecap="round"/>

          <!-- emotion extras (sparkles, bubbles, anger lines, etc.) -->
          {extra_svg}

          <!-- speaking dots -->
          <g id="dots_{uid}" opacity="0">
            <circle cx="62" cy="20" r="3" fill="{color}">
              <animate attributeName="opacity" values="0;1;0" dur="0.6s"
                       begin="0s" repeatCount="indefinite"/>
            </circle>
            <circle cx="68" cy="14" r="3" fill="{color}">
              <animate attributeName="opacity" values="0;1;0" dur="0.6s"
                       begin="0.2s" repeatCount="indefinite"/>
            </circle>
            <circle cx="74" cy="8" r="3" fill="{color}">
              <animate attributeName="opacity" values="0;1;0" dur="0.6s"
                       begin="0.4s" repeatCount="indefinite"/>
            </circle>
          </g>

          <!-- DR. OMNI badge -->
          <rect x="18" y="103" width="54" height="10" rx="5"
                fill="{color}22" stroke="{color}66" stroke-width="0.8"/>
          <text x="45" y="111" text-anchor="middle"
                font-family="monospace" font-size="5.5"
                fill="{color}" font-weight="bold">DR. OMNI</text>
        </svg>
      </div>

      <div style="flex:1;min-width:0;">
        <div style="font-size:0.6rem;color:{color};letter-spacing:0.2em;
                    text-transform:uppercase;margin-bottom:6px;font-weight:700;">
          ⬡ {label.upper()}
        </div>

        <div style="font-size:0.92rem;color:#C8D8F0;line-height:1.65;
                    background:{color}0A;border-left:3px solid {color}44;
                    padding:10px 14px;border-radius:0 8px 8px 0;
                    margin-bottom:10px;">
          {display}
        </div>

        {controls_html}
      </div>
    </div>

    <script>
    (function() {{
      const TXT = '{safe}';
      const synth = window.speechSynthesis;
      let going = false;
      let paused = false;

      const dots  = document.getElementById('dots_{uid}');
      const mouth = document.getElementById('mouth_{uid}');
      const defaultMouth = '{mouth_d}';
      let mouthIv = null;

      function startMouth() {{
        if (mouthIv) clearInterval(mouthIv);
        let t = true;
        mouthIv = setInterval(() => {{
          if (!going || !mouth) {{ clearInterval(mouthIv); return; }}
          mouth.setAttribute('d', t
            ? 'M 27 38 Q 35 48 43 38'
            : 'M 27 38 Q 35 43 43 38');
          t = !t;
        }}, 150);
      }}

      function stopMouth() {{
        if (mouthIv) {{ clearInterval(mouthIv); mouthIv = null; }}
        if (mouth) mouth.setAttribute('d', defaultMouth);
      }}

      window['speak_{uid}'] = function() {{
        if (synth.speaking) synth.cancel();
        if (!TXT) return;
        const speedEl = document.getElementById('speed_{uid}');
        const speed = speedEl ? parseFloat(speedEl.value) : 0.95;
        const u = new SpeechSynthesisUtterance(TXT);
        u.rate  = speed;
        u.pitch = 1.05;
        u.lang  = 'en-US';
        const voices = synth.getVoices();
        const preferred = voices.find(v =>
          v.name.includes('Google') || v.name.includes('Natural') ||
          v.name.includes('Daniel') || v.name.includes('Samantha')
        );
        if (preferred) u.voice = preferred;
        u.onstart = () => {{
          going = true; paused = false;
          if (dots) dots.setAttribute('opacity','1');
          startMouth();
        }};
        u.onend = () => {{
          going = false; paused = false;
          if (dots) dots.setAttribute('opacity','0');
          stopMouth();
        }};
        u.onerror = () => {{
          going = false;
          if (dots) dots.setAttribute('opacity','0');
          stopMouth();
        }};
        synth.speak(u);
      }};

      window['pause_{uid}'] = function() {{
        if (synth.speaking && !paused) {{
          synth.pause(); paused = true; going = false;
          stopMouth();
          if (dots) dots.setAttribute('opacity','0.3');
        }} else if (paused) {{
          synth.resume(); paused = false; going = true;
          if (dots) dots.setAttribute('opacity','1');
          startMouth();
        }}
      }};

      window['stopSpeech_{uid}'] = function() {{
        synth.cancel();
        going = false; paused = false;
        if (dots) dots.setAttribute('opacity','0');
        stopMouth();
      }};

      {auto_speak}
    }})();
    </script>
    """, height=210)


# ── Mermaid diagram renderer ─────────────────────────────────────────────────

def render_mermaid_diagram(mermaid_code: str, title: str = "") -> None:
    """
    Render Mermaid diagram with v11 neo look + 3D depth shadows.
    Uses explicit mermaid.render() — never relies on startOnLoad class detection.
    Always renders — never silently fails.
    """
    if not mermaid_code or not mermaid_code.strip():
        return

    code = mermaid_code.strip()
    for fence in ["```mermaid", "```", "~~~"]:
        code = code.replace(fence, "").strip()

    escaped = (
        code
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("$", "\\$")
    )

    title_html = (
        f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;'
        f'color:rgba(0,212,255,0.7);letter-spacing:0.2em;text-transform:uppercase;'
        f'margin-bottom:12px;">📊 {title}</div>'
        if title else ""
    )

    components.html(f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ background: transparent; margin: 0; padding: 0; }}
        .diagram-wrapper {{
            background: linear-gradient(145deg, #0A1628, #0E1E3C);
            border: 1px solid rgba(0,212,255,0.2);
            border-radius: 12px;
            padding: 20px;
            margin: 8px 0;
            position: relative;
            overflow: hidden;
            box-shadow:
                0 4px 6px rgba(0,0,0,0.4),
                0 8px 15px rgba(0,0,0,0.3),
                0 20px 40px rgba(0,0,0,0.25),
                0 0 0 1px rgba(0,212,255,0.05),
                inset 0 1px 0 rgba(255,255,255,0.06);
            animation: diagramFadeIn 0.6s cubic-bezier(0.16,1,0.3,1) forwards;
            opacity: 0;
            transform: translateY(8px);
        }}
        .diagram-wrapper::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg,
                transparent 0%,
                rgba(0,212,255,0.6) 30%,
                rgba(0,212,255,0.9) 50%,
                rgba(0,212,255,0.6) 70%,
                transparent 100%
            );
        }}
        @keyframes diagramFadeIn {{
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        #mermaid-container svg {{
            filter:
                drop-shadow(0 4px 8px rgba(0,0,0,0.5))
                drop-shadow(0 0 20px rgba(0,212,255,0.08));
            transition: filter 0.3s ease;
            max-width: 100%;
            height: auto;
        }}
        #mermaid-container svg:hover {{
            filter:
                drop-shadow(0 8px 16px rgba(0,0,0,0.6))
                drop-shadow(0 0 30px rgba(0,212,255,0.15));
        }}
    </style>
    </head>
    <body>
    <div class="diagram-wrapper">
        {title_html}
        <div id="mermaid-container"></div>
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';

        mermaid.initialize({{
            startOnLoad: false,
            look: 'neo',
            theme: 'base',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 13,
            themeVariables: {{
                primaryColor:        '#1A3050',
                primaryBorderColor:  '#00D4FF',
                primaryTextColor:    '#E8F4FF',
                secondaryColor:      '#0D1E35',
                secondaryBorderColor:'#00A0C0',
                secondaryTextColor:  '#C0D8F0',
                tertiaryColor:       '#0A1628',
                tertiaryBorderColor: '#4A7090',
                lineColor:           '#00D4FF',
                textColor:           '#E8F4FF',
                mainBkg:             '#1A3050',
                clusterBkg:          '#0D1E35',
                edgeLabelBackground: '#0E1E3C',
                nodeBorder:          '#00D4FF',
                titleColor:          '#00D4FF',
                attributeBackgroundColorEven: '#0A1628',
                attributeBackgroundColorOdd:  '#0D1E35',
            }},
            flowchart: {{
                htmlLabels: true,
                curve: 'basis',
                padding: 20,
                nodeSpacing: 50,
                rankSpacing: 60,
                useMaxWidth: true,
            }},
            sequence: {{
                useMaxWidth: true,
                boxMargin: 10,
                mirrorActors: false,
                messageMargin: 40,
            }},
            classDiagram: {{ useMaxWidth: true }},
        }});

        const code = `{escaped}`;
        const container = document.getElementById('mermaid-container');

        (async () => {{
            try {{
                const id = 'mermaid-' + Math.random().toString(36).slice(2, 9);
                const {{ svg }} = await mermaid.render(id, code);
                container.innerHTML = svg;
            }} catch (err) {{
                container.innerHTML = `
                  <div style="color:#EF4444;font-size:0.8rem;padding:10px;
                              font-family:monospace;background:rgba(239,68,68,0.1);
                              border:1px solid rgba(239,68,68,0.2);border-radius:6px;">
                    Diagram render error: ${{err.message}}<br>
                    <pre style="font-size:0.7rem;color:#A0B4D6;margin-top:8px;
                                white-space:pre-wrap;">${{code}}</pre>
                  </div>
                `;
            }}
        }})();
    </script>
    </body>
    </html>
    """, height=420, scrolling=True)



def render_confidence_badge(source_type: str = "model", has_rag: bool = False) -> None:
    """
    3-band confidence badge:
      grounded  → green  ✅  "Based on your notes"
      model     → amber  ⚠   "Model knowledge (verify in textbook)"
      uncertain → red    📘  "Not in your notes — treat as a guide only"
    """
    if source_type == "grounded" or has_rag:
        color, icon, label = "#2ECC71", "✅", "Based on your uploaded notes"
    elif source_type == "uncertain":
        color, icon, label = "#E74C3C", "📘", "Not in your notes — verify in textbook"
    else:
        color, icon, label = "#F39C12", "⚠", "Model knowledge — verify key facts"

    st.markdown(
        f'<div style="display:inline-block;background:rgba(255,255,255,0.05);'
        f'border:1px solid {color};border-radius:8px;padding:4px 12px;'
        f'font-size:0.75rem;color:{color};margin:4px 0;">'
        f'{icon} {label}</div>',
        unsafe_allow_html=True,
    )


# ── Lesson recap card ─────────────────────────────────────────────────────────

def render_lesson_recap(recap: dict, color: str = "#00D4FF") -> None:
    """Render the 5-point lesson recap card."""
    points_html = "".join([
        f'<div style="display:flex;gap:10px;margin:6px 0;align-items:flex-start;">'
        f'<span style="color:{color};font-weight:700;flex-shrink:0;">{i+1}.</span>'
        f'<span style="color:#C8D8F0;font-size:0.88rem;line-height:1.5;">{p}</span>'
        f'</div>'
        for i, p in enumerate(recap.get("points", []))
    ])
    related = recap.get("related_topics", [])
    related_html = " &nbsp;·&nbsp; ".join(
        f'<span style="color:{color};cursor:pointer;">📌 {t}</span>'
        for t in related
    )
    memory_trick = recap.get("memory_trick", "")
    memory_html = ('<div style="margin-top:12px;padding:8px 12px;background:rgba(255,184,0,0.08);border-radius:8px;"><span style="font-size:0.7rem;color:#FFB800;letter-spacing:0.1em;text-transform:uppercase;">MEMORY TRICK · </span><span style="font-size:0.85rem;color:#C8D8F0;">' + memory_trick + '</span></div>') if memory_trick else ''
    related_block = ('<div style="margin-top:12px;font-size:0.72rem;color:#4A6080;">Study next: ' + related_html + '</div>') if related else ''
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0D1B35,#111929);
                border:1px solid {color}44;border-radius:16px;
                padding:24px 28px;margin:12px 0;position:relative;overflow:hidden;">
      <div style="position:absolute;top:0;left:0;right:0;height:3px;
                  background:linear-gradient(90deg,transparent,{color},transparent);">
      </div>
      <div style="font-family:Orbitron,monospace;font-size:0.65rem;color:{color};
                  letter-spacing:0.2em;text-transform:uppercase;margin-bottom:14px;">
        📋 {recap.get("title","Lesson Recap")}
      </div>
      {points_html}
      <div style="margin-top:14px;background:{color}11;border-radius:8px;
                  padding:10px 14px;border-left:3px solid {color};">
        <div style="font-size:0.65rem;color:{color};letter-spacing:0.1em;
                    text-transform:uppercase;margin-bottom:4px;">EXAM ANSWER</div>
        <div style="font-size:0.88rem;color:#E8F0FF;font-style:italic;">
          "{recap.get("exam_one_liner","")}"
        </div>
      </div>
      {memory_html}
      {related_block}
    </div>
    """, unsafe_allow_html=True)


# ── Session Summary ──────────────────────────────────────────────────────────

def render_session_summary(student_name: str, db, student_id: str,
                           subject: str) -> None:
    """Render a post-session performance summary card."""
    color = "#9B59B6"
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0D0020,#111929);
                border:1px solid {color}55;border-radius:16px;
                padding:24px 28px;margin:16px 0;position:relative;overflow:hidden;">
      <div style="position:absolute;top:0;left:0;right:0;height:3px;
                  background:linear-gradient(90deg,transparent,{color},transparent);"></div>
      <div style="font-family:Orbitron,monospace;font-size:0.65rem;color:{color};
                  letter-spacing:0.2em;text-transform:uppercase;margin-bottom:16px;">
        📊 SESSION SUMMARY · {student_name.upper() if student_name else "YOUR PROGRESS"}
      </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    # Topics covered this session
    memory = _get_lesson_memory()
    topics_today = [m["topic"] for m in memory] if memory else []

    # Weak concepts
    weak_items: list = []
    if db:
        try:
            weak_items = db.get_weak_concepts(student_id, resolved=False) or []
        except Exception:
            weak_items = []

    # Chapter scores
    scores: dict = {}
    if db:
        try:
            raw = db.get_chapter_scores_by_subject(student_id, subject) or {}
            scores = raw if isinstance(raw, dict) else {}
        except Exception:
            scores = {}

    strong_chapters = [ch for ch, sc in scores.items() if sc >= 70]
    weak_chapters   = [ch for ch, sc in scores.items() if sc < 50]

    with col1:
        st.markdown(f"""
        <div style="background:rgba(0,200,80,0.08);border:1px solid rgba(0,200,80,0.3);
                    border-radius:10px;padding:14px;min-height:120px;">
          <div style="font-size:0.6rem;color:#00C850;letter-spacing:0.15em;
                      text-transform:uppercase;margin-bottom:8px;">💪 Strong Areas</div>
        """, unsafe_allow_html=True)
        if strong_chapters:
            for ch in strong_chapters[:4]:
                st.markdown(f'<span style="display:inline-block;background:rgba(0,200,80,0.15);'
                            f'color:#00C850;border-radius:6px;padding:2px 8px;'
                            f'font-size:0.75rem;margin:2px;">{ch}</span>',
                            unsafe_allow_html=True)
        else:
            st.markdown('<span style="color:#4A6080;font-size:0.78rem;">Keep studying!</span>',
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.3);
                    border-radius:10px;padding:14px;min-height:120px;">
          <div style="font-size:0.6rem;color:#EF4444;letter-spacing:0.15em;
                      text-transform:uppercase;margin-bottom:8px;">⚠️ Needs Work</div>
        """, unsafe_allow_html=True)
        items_shown = 0
        for wc in weak_items[:4]:
            concept = wc.get("concept", "") if isinstance(wc, dict) else str(wc)
            if concept:
                st.markdown(f'<span style="display:inline-block;background:rgba(239,68,68,0.12);'
                            f'color:#EF4444;border-radius:6px;padding:2px 8px;'
                            f'font-size:0.75rem;margin:2px;">{concept}</span>',
                            unsafe_allow_html=True)
                items_shown += 1
        for ch in weak_chapters[:max(0, 4 - items_shown)]:
            st.markdown(f'<span style="display:inline-block;background:rgba(239,68,68,0.1);'
                        f'color:#FF8888;border-radius:6px;padding:2px 8px;'
                        f'font-size:0.75rem;margin:2px;">{ch}</span>',
                        unsafe_allow_html=True)
        if not weak_items and not weak_chapters:
            st.markdown('<span style="color:#4A6080;font-size:0.78rem;">No weak areas found!</span>',
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background:rgba(155,89,182,0.08);border:1px solid rgba(155,89,182,0.3);
                    border-radius:10px;padding:14px;min-height:120px;">
          <div style="font-size:0.6rem;color:{color};letter-spacing:0.15em;
                      text-transform:uppercase;margin-bottom:8px;">📚 Topics Today</div>
        """, unsafe_allow_html=True)
        if topics_today:
            for t in topics_today[-4:]:
                st.markdown(f'<span style="display:inline-block;background:rgba(155,89,182,0.15);'
                            f'color:#C39BD3;border-radius:6px;padding:2px 8px;'
                            f'font-size:0.75rem;margin:2px;">{t}</span>',
                            unsafe_allow_html=True)
        else:
            st.markdown('<span style="color:#4A6080;font-size:0.78rem;">No topics yet.</span>',
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ── Image Explainer (Gemma 4 Vision) ─────────────────────────────────────────

def render_image_explainer(student: dict, ollama_client) -> None:
    """Upload image of diagram/textbook page → explanation + exam questions via Gemma 4 vision."""
    st.markdown("### 📸 Explain This Diagram")
    st.caption("Point your camera at any diagram, textbook page, or handwritten notes")

    uploaded_img = st.file_uploader(
        "Upload image",
        type=["jpg", "jpeg", "png", "webp"],
        key="vt_image_upload",
        label_visibility="collapsed",
    )

    if uploaded_img:
        import base64
        import io

        try:
            from PIL import Image
        except ImportError:
            st.error("Install Pillow: pip install Pillow")
            return

        col1, col2 = st.columns([1, 2])
        with col1:
            img = Image.open(uploaded_img)
            max_size = 1024
            ratio = min(max_size / img.width, max_size / img.height)
            if ratio < 1:
                img = img.resize(
                    (int(img.width * ratio), int(img.height * ratio)),
                    Image.LANCZOS,
                )
            st.image(img, use_container_width=True)

        with col2:
            if st.button("🔍 Explain This", type="primary", key="btn_explain_image"):
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                img_b64 = base64.b64encode(buf.getvalue()).decode()

                with st.spinner("Dr. Omni is analysing the image..."):
                    import ollama as _ollama_lib
                    try:
                        resp = _ollama_lib.chat(
                            model="gemma4:e4b",
                            messages=[{
                                "role": "user",
                                "content": (
                                    f"You are a {student.get('subject', 'Computer Science')} lecturer. "
                                    f"Explain this diagram/image to a student. "
                                    f"Structure your response as:\n"
                                    f"WHAT THIS SHOWS: [one sentence]\n"
                                    f"KEY PARTS:\n1. [part]: [what it does]\n"
                                    f"2. [part]: [what it does]\n"
                                    f"3. [part]: [what it does]\n"
                                    f"THE PROCESS: [step by step]\n"
                                    f"EXAMINER WILL ASK:\n"
                                    f"1. [likely exam question]\n"
                                    f"2. [likely exam question]\n"
                                    f"MEMORY TIP: [one mnemonic]"
                                ),
                                "images": [img_b64],
                            }],
                            options={"num_ctx": 4096},
                        )
                        explanation = (
                            resp["message"]["content"]
                            if isinstance(resp, dict)
                            else resp.message.content
                        )
                        st.session_state["vt_img_explanation"] = explanation
                        st.rerun()
                    except Exception as e:
                        st.error(f"Image analysis failed: {e}")

        if "vt_img_explanation" in st.session_state:
            st.markdown("""
            <div style="background:rgba(0,212,255,0.05);
                        border:1px solid rgba(0,212,255,0.15);
                        border-radius:10px;padding:16px;margin-top:12px;">
            """, unsafe_allow_html=True)
            st.markdown(st.session_state["vt_img_explanation"])
            st.markdown("</div>", unsafe_allow_html=True)
            if st.button("🗑️ Clear", key="btn_clear_img"):
                del st.session_state["vt_img_explanation"]
                st.rerun()
    else:
        st.markdown("""
        <div style="text-align:center;padding:40px 20px;
                    background:rgba(0,212,255,0.04);border:1px dashed rgba(0,212,255,0.2);
                    border-radius:12px;margin:16px 0;">
          <div style="font-size:2rem;margin-bottom:8px;">📸</div>
          <div style="color:#4A6080;font-size:0.85rem;">
            Upload a photo of any diagram, textbook page, or handwritten notes<br>
            Gemma 4's vision will explain it and generate exam questions
          </div>
        </div>
        """, unsafe_allow_html=True)


# ── Main render function ──────────────────────────────────────────────────────

def render_virtual_teacher_mode(student: dict, ollama_client, db, rag=None):
    """
    World-class Virtual Teacher mode.
    Progressive delivery + mid-lesson questions + diagrams + memory + recap.
    """
    subject    = student.get("subject", "Computer Science")
    student_id = student.get("student_id", "demo_001")
    language   = student.get("language",
                             student.get("preferred_language", "english"))
    name       = student.get("name", "Student")

    teacher = VirtualTeacher(ollama_client, db, rag)


    tab_teach, tab_image = st.tabs(["📖 Full Lesson", "📸 Explain Image"])
    with tab_image:
        render_image_explainer(student, ollama_client)
    with tab_teach:
        st.markdown("## 👩‍🏫 Virtual Teacher — Dr. Omni")
        st.caption(
            "World-class AI lecturer · Progressive lessons · Diagrams · "
            "Mid-lesson questions · Voice narration · Lesson memory"
        )

        memory = _get_lesson_memory()
        if memory:
            with st.expander(f"📚 Topics covered this session ({len(memory)})",
                             expanded=False):
                for m in reversed(memory):
                    st.markdown(f"**{m['topic']}**")
                    for pt in m.get("points", [])[:2]:
                        st.caption(f"• {pt}")

        render_avatar_teacher("", phase="greeting", emotion="neutral",
                              show_speech_controls=False)

        col1, col2 = st.columns([4, 1])
        with col1:
            topic = st.text_input(
                "What topic shall we cover today?",
                placeholder="e.g. Deadlock in Operating Systems",
                key="vt_topic_input",
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            start = st.button("🎓 Teach Me", type="primary",
                              disabled=not bool(topic.strip()),
                              use_container_width=True)

        if start:
            saved_topic_input = topic.strip()
            with st.status(
                "🦉 Dr. Omni is preparing your lesson...",
                expanded=True,
            ) as _status:
                _status.write("📖 Searching your study materials...")

                rag_context = ""
                try:
                    rag_context, _ = retrieve_context_hybrid(
                        saved_topic_input,
                        subject=subject,
                    )
                except Exception:
                    rag_context = ""

                _status.write(
                    "🧠 Generating lesson + comprehension check in parallel..."
                )

                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as _executor:
                    _f_lesson = _executor.submit(
                        teacher.teach,
                        saved_topic_input,
                        subject,
                        student_id,
                        language,
                    )
                    _f_mid = _executor.submit(
                        teacher._generate_mid_question_fast,
                        topic=saved_topic_input,
                        subject=subject,
                        language=language,
                    )

                    _lesson = None
                    try:
                        _lesson = _f_lesson.result(timeout=90)
                    except concurrent.futures.TimeoutError:
                        _lesson = None
                    except Exception:
                        _lesson = None

                    _mid_q_fast = None
                    try:
                        _mid_q_fast = _f_mid.result(timeout=30)
                    except Exception:
                        _mid_q_fast = None

                _status.write("✅ Lesson ready — loading...")
                _status.update(
                    label="Lesson ready!",
                    state="complete",
                    expanded=False,
                )

            if _lesson is not None:
                _valid, _reason = _validate_lesson(_lesson)
                if not _valid:
                    _lesson = None

            if _lesson is None:
                st.markdown("""
                <div class="omni-card fade-in" style="
                  border-color:rgba(255,71,87,0.3);
                  padding:20px 24px;">
                  <div class="omni-chip omni-chip-red">
                    ⚠️ Incomplete Response
                  </div>
                  <p style="color:#8899AA; margin:12px 0 0;
                            font-family:'DM Sans',sans-serif;
                            font-size:0.9rem;">
                    The lesson response was incomplete or timed out.
                    This usually means Ollama is processing slowly
                    or the topic was very complex.
                  </p>
                </div>
                """, unsafe_allow_html=True)
                _c1, _c2 = st.columns(2)
                with _c1:
                    if st.button(
                        "🔄 Retry (simpler prompt)",
                        type="primary",
                        use_container_width=True,
                    ):
                        st.session_state.pop("vt_lesson", None)
                        st.session_state["vt_use_simple_prompt"] = True
                        st.rerun()
                with _c2:
                    if st.button(
                        "📖 Try different topic",
                        use_container_width=True,
                    ):
                        for _k in [
                            "vt_lesson", "vt_topic", "vt_phase",
                            "vt_use_simple_prompt", "vt_mid_answered",
                            "vt_mid_result", "vt_answers", "vt_recap",
                        ]:
                            st.session_state.pop(_k, None)
                        st.rerun()
                return

            if _mid_q_fast and isinstance(_mid_q_fast, dict):
                if not _lesson.get("mid_question") and not _lesson.get("_mid_question"):
                    _lesson["_mid_question"] = _mid_q_fast

            st.session_state["vt_lesson"]       = _lesson
            st.session_state["vt_topic"]        = saved_topic_input
            st.session_state["vt_phase"]        = "hook"
            st.session_state["vt_mid_answered"] = False
            st.session_state["vt_mid_result"]   = None
            st.session_state["vt_answers"]      = {}
            st.session_state["vt_recap"]        = None
            st.session_state["vt_socratic"]     = None
            st.session_state.pop("vt_hint_level", None)
            st.rerun()

        lesson = st.session_state.get("vt_lesson")
        if not lesson:
            st.info("Enter a topic above and click **Teach Me** to begin.")
            return

        # Validate lesson — show error UI if incomplete
        _valid, _reason = _validate_lesson(lesson)
        if not _valid:
            st.error(
                f"⚠️ The lesson response was incomplete ({_reason}). "
                "This usually means Ollama is slow or the topic was too complex."
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Retry with simpler prompt", type="primary",
                             key="btn_vt_retry_simple"):
                    st.session_state.pop("vt_lesson", None)
                    st.session_state["vt_use_simple_prompt"] = True
                    st.rerun()
            with col2:
                if st.button("📖 Try a different topic", key="btn_vt_diff_topic"):
                    for k in ["vt_lesson", "vt_topic", "vt_phase", "vt_use_simple_prompt"]:
                        st.session_state.pop(k, None)
                    st.rerun()
            return

        saved_topic = st.session_state.get("vt_topic", "")
        phase       = st.session_state.get("vt_phase", "hook")
        color       = "#00D4FF"

        st.markdown(f"### 📖 Lesson: **{saved_topic}**")
        st.markdown("---")

        # ── PHASE 1 — HOOK ──────────────────────────────────────────────────────
        hook = lesson.get("hook", "")
        render_avatar_teacher(hook, phase="teaching", emotion="encouraging")

        with st.expander("📖 Hook — Real-World Analogy", expanded=True):
            st.markdown(hook)

        if phase == "hook":
            if st.button("➡️ I understand — continue to explanation",
                         key="btn_hook_next"):
                st.session_state["vt_phase"] = "explanation"
                st.rerun()
            return

        # ── PHASE 2 — CORE EXPLANATION + DIAGRAM ────────────────────────────────
        explanation = lesson.get("explanation", "")

        with st.expander("🧠 Core Explanation", expanded=True):
            st.markdown(explanation)
            sources = lesson.get("_sources", [])
            if sources:
                st.caption("📎 From your notes: " + " | ".join(sources))

        has_rag = bool(lesson.get("_sources"))
        render_confidence_badge(
            source_type="grounded" if has_rag else "model",
            has_rag=has_rag,
        )

        _llm_diagram = lesson.get("_diagram", "").strip()
        if _should_use_llm_diagram(_llm_diagram):
            diagram_code = _llm_diagram
        else:
            diagram_code = _make_topic_diagram(saved_topic)
        if diagram_code:
            render_mermaid_diagram(diagram_code,
                                   title=f"Visual Diagram: {saved_topic}")

        # ── MID-LESSON QUESTION ──────────────────────────────────────────────────
        mid_q = lesson.get("_mid_question", {})

        if mid_q and not st.session_state.get("vt_mid_answered"):
            st.markdown("---")
            mid_text = mid_q.get("question", "")
            render_avatar_teacher(mid_text, phase="questioning",
                                  emotion="thinking")

            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#001D0D,#0D1B35);
                        border:2px solid #00C85044;border-radius:12px;
                        padding:18px 22px;margin:8px 0;">
              <div style="font-size:0.6rem;color:#00C850;letter-spacing:0.15em;
                          text-transform:uppercase;margin-bottom:8px;">
                🛑 MID-LESSON CHECK — Answer before continuing
              </div>
              <div style="font-size:1rem;color:#E8F0FF;font-weight:600;">
                {mid_text}
              </div>
            </div>
            """, unsafe_allow_html=True)

            mid_answer = st.text_area(
                "Your answer",
                key="vt_mid_input",
                placeholder="Type your answer...",
                label_visibility="collapsed",
                height=80,
            )

            hint_level = st.session_state.get("vt_hint_level", 0)

            col_a, col_b, col_c = st.columns([2, 1, 1])
            with col_a:
                if st.button("✅ Submit Answer", key="btn_mid_submit",
                             type="primary"):
                    if mid_answer.strip():
                        with st.spinner("Dr. Omni is evaluating..."):
                            result = teacher.evaluate_check_answer(
                                question=mid_text,
                                student_answer=mid_answer,
                                topic=saved_topic,
                                student_id=student_id,
                                language=language,
                                expected_key_points=mid_q.get("expected", ""),
                                subject=subject,
                            )
                            if not result["correct"]:
                                socratic = teacher.get_socratic_followup(
                                    topic=saved_topic,
                                    question=mid_text,
                                    student_answer=mid_answer,
                                    expected=mid_q.get("expected", ""),
                                )
                            else:
                                socratic = None
                        st.session_state["vt_mid_result"]  = result
                        st.session_state["vt_socratic"]    = socratic
                        if result["correct"]:
                            st.session_state["vt_mid_answered"] = True
                        st.rerun()
                    else:
                        st.warning("Please write an answer first.")

            with col_b:
                if st.button("💡 Hint", key="btn_mid_hint"):
                    st.session_state["vt_hint_level"] = min(hint_level + 1, 3)
                    st.rerun()

            with col_c:
                if st.button("⏭ Skip", key="btn_mid_skip"):
                    st.session_state["vt_mid_answered"] = True
                    st.rerun()

            if hint_level >= 1:
                st.info(f"💡 Hint: {mid_q.get('hint','Think about the core concept.')}")
            if hint_level >= 2:
                st.info(f"💡 Bigger hint: Focus on: {mid_q.get('expected','the key points')}")

            mid_result = st.session_state.get("vt_mid_result")
            if mid_result:
                if mid_result["correct"]:
                    render_avatar_teacher(
                        f"Excellent! {mid_result['feedback']}",
                        phase="correct", emotion="happy",
                        student_name=name
                    )
                else:
                    socratic = st.session_state.get("vt_socratic", {}) or {}
                    render_avatar_teacher(
                        socratic.get("probing_question",
                                     mid_result["feedback"]),
                        phase="wrong", emotion="angry",
                        student_name=name
                    )
                    st.warning(
                        f"**{socratic.get('acknowledgement','')}**  \n"
                        f"🔍 {socratic.get('probing_question','')}  \n"
                        f"💭 *{socratic.get('nudge','')}*"
                    )

                    if st.button("✅ I understand now — continue",
                                 key="btn_mid_override"):
                        st.session_state["vt_mid_answered"] = True
                        st.rerun()
            return

        if mid_q and st.session_state.get("vt_mid_answered"):
            mid_result = st.session_state.get("vt_mid_result")
            if mid_result and mid_result.get("correct"):
                st.success(f"✅ Mid-lesson check passed! {mid_result.get('feedback','')}")
            elif mid_result:
                st.info("✅ Continuing lesson...")

        if phase in ("hook", "explanation"):
            st.session_state["vt_phase"] = "worked_example"

        # ── PHASE 3 — WORKED EXAMPLE ────────────────────────────────────────────
        with st.expander("⚙️ Worked Example — Step by Step", expanded=True):
            st.markdown(lesson.get("worked_example",
                                   "_No worked example generated._"))

        # ── PHASE 4 — EXAM HOOK ──────────────────────────────────────────────────
        with st.expander("🎯 What the Examiner Will Ask", expanded=False):
            render_avatar_teacher(
                "These are the most likely exam questions on this topic.",
                phase="teaching", emotion="encouraging",
                student_name=name
            )
            exam_hooks = lesson.get("exam_hook", [])
            if isinstance(exam_hooks, list):
                for i, item in enumerate(exam_hooks, 1):
                    st.markdown(f"""
                    <div style="display:flex;gap:12px;padding:8px 0;
                                border-bottom:1px solid rgba(0,212,255,0.1);">
                      <span style="color:#00D4FF;font-family:Orbitron,monospace;
                                   font-weight:700;flex-shrink:0;">Q{i}</span>
                      <span style="color:#C8D8F0;font-size:0.9rem;">{item}</span>
                    </div>
                    """, unsafe_allow_html=True)

        # ── PHASE 5 — COMPREHENSION CHECK ────────────────────────────────────────
        st.markdown("---")
        render_avatar_teacher(
            "Final check — answer these questions to complete the lesson.",
            phase="questioning", emotion="thinking",
            student_name=name
        )
        st.markdown("### ✅ Final Comprehension Check")

        check_qs = lesson.get("check_questions", [])
        if "vt_answers" not in st.session_state:
            st.session_state["vt_answers"] = {}
        if "vt_correct_streak" not in st.session_state:
            st.session_state["vt_correct_streak"] = 0
        if "vt_wrong_streak" not in st.session_state:
            st.session_state["vt_wrong_streak"] = 0

        all_done = True
        for i, cq in enumerate(check_qs):
            q_text   = cq.get("question", f"Question {i+1}")
            expected = cq.get("expected_key_points", "")
            key      = f"vt_final_{i}"

            # Late reply detector — mark when question was first shown
            ts_key = f"vt_q{i}_start"
            if ts_key not in st.session_state:
                st.session_state[ts_key] = time.time()

            st.markdown(f"""
            <div style="background:rgba(0,212,255,0.04);border-left:3px solid #00D4FF44;
                        padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;">
              <span style="color:#00D4FF;font-weight:700;">Q{i+1}. </span>
              <span style="color:#E8F0FF;">{q_text}</span>
            </div>
            """, unsafe_allow_html=True)

            if key not in st.session_state["vt_answers"]:
                all_done = False
                # Show nudge if student has been idle >120 s on this question
                elapsed = time.time() - st.session_state.get(ts_key, time.time())
                if elapsed > 120:
                    render_avatar_teacher(
                        "Still there? Take your time, but give it a try — even a rough answer helps!",
                        phase="wrong", emotion="angry",
                        student_name=name,
                    )
                answer = st.text_area(
                    "Answer", key=f"{key}_input",
                    label_visibility="collapsed",
                    placeholder="Type your answer here...",
                    height=80,
                )
                if st.button(f"Submit", key=f"{key}_btn", type="primary"):
                    if answer.strip():
                        with st.spinner("Marking..."):
                            result = teacher.evaluate_check_answer(
                                question=q_text,
                                student_answer=answer,
                                topic=saved_topic,
                                student_id=student_id,
                                language=language,
                                expected_key_points=expected,
                                subject=subject,
                            )
                        # Update streaks
                        if result.get("correct"):
                            st.session_state["vt_correct_streak"] += 1
                            st.session_state["vt_wrong_streak"] = 0
                        else:
                            st.session_state["vt_wrong_streak"] += 1
                            st.session_state["vt_correct_streak"] = 0
                        st.session_state["vt_answers"][key] = result
                        st.rerun()
                    else:
                        st.warning("Write your answer before submitting.")
            else:
                result = st.session_state["vt_answers"][key]
                if result.get("correct"):
                    render_avatar_teacher(
                        f"Correct! {result['feedback']}",
                        phase="correct", emotion="happy",
                        student_name=name
                    )
                    st.success(f"✅ {result['feedback']}")
                else:
                    render_avatar_teacher(
                        result["feedback"],
                        phase="wrong", emotion="angry",
                        student_name=name
                    )
                    st.error(f"❌ {result['feedback']}")
                    if result.get("weakness"):
                        st.warning(
                            f"⚠️ Added to weak areas: **{result['weakness']}**"
                        )

        # ── LESSON COMPLETE — RECAP + MEMORY ─────────────────────────────────────
        if all_done and check_qs:
            st.markdown("---")

            if not st.session_state.get("vt_recap"):
                if st.button("📋 Generate Lesson Recap", type="primary",
                             key="btn_recap"):
                    with st.spinner("Generating lesson recap..."):
                        recap = teacher.generate_recap(saved_topic, subject)
                    st.session_state["vt_recap"] = recap
                    _add_to_memory(saved_topic,
                                   recap.get("points", [])[:3])
                    st.rerun()
            else:
                recap = st.session_state["vt_recap"]
                render_avatar_teacher(
                    f"Excellent work! You've completed the lesson on {saved_topic}. "
                    f"Here's your recap card.",
                    phase="recap", emotion="excited",
                    student_name=name
                )
                render_lesson_recap(recap, color="#9B59B6")

                if db and st.button("💾 Save Lesson", key="btn_save"):
                    try:
                        lesson_data = {**lesson, "_recap": recap}
                        lid = db.save_lesson(
                            student_id=student_id,
                            topic=saved_topic,
                            subject=subject,
                            lesson_json=json.dumps(lesson_data,
                                                   ensure_ascii=False),
                        )
                        st.success(f"✅ Lesson saved! (ID: {lid[:8]})")
                    except Exception as e:
                        st.error(f"Could not save: {e}")

                if st.button("📖 Teach Me Another Topic", key="btn_new"):
                    for k in ["vt_lesson", "vt_topic", "vt_phase", "vt_mid_answered",
                              "vt_mid_result", "vt_answers", "vt_recap", "vt_socratic"]:
                        st.session_state.pop(k, None)
                    st.rerun()

                if st.button("📊 View Session Summary", key="btn_session_summary"):
                    render_session_summary(name, db, student_id, subject)
