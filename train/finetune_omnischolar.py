#!/usr/bin/env python3
"""
train/finetune_omnischolar.py
─────────────────────────────
QLoRA fine-tune Gemma 4 on OmniScholar Sri Lankan education data.

Data sources (in priority order):
  1. omnischolar.db  — saved_lessons, quiz_history (real student interactions)
  2. Synthetic seed  — curated examples for every OmniScholar prompt mode

Usage
─────
  # Basic (uses gemma-4-2b-it, reads omnischolar.db, writes to ./checkpoints)
  python train/finetune_omnischolar.py

  # Kaggle / Unsloth (recommended — 2× faster)
  python train/finetune_omnischolar.py \\
    --model_id  unsloth/gemma-4-E2B-it \\
    --db_path   /kaggle/working/data \\
    --output    /kaggle/working/omnischolar_output \\
    --epochs    3 --batch 2 --push_to_hub \\
    --hub_repo  YOUR-HF-USERNAME/omnischolar-gemma4-e2b-edu

  # Local dev (transformers fallback)
  python train/finetune_omnischolar.py \\
    --model_id  google/gemma-4-2b-it \\
    --db_path   omnischolar/omnischolar.db \\
    --output    ./checkpoints/omnischolar-v1

--db_path accepts:
  • A .db SQLite file  (omnischolar.db — saved_lessons table)
  • A directory        (scanned for *.jsonl / *.json files)
    JSONL rows support both 'messages' and 'conversations' keys,
    and both role/content and from/value field names.

Extra requirements (not in omnischolar/requirements.txt):
  # Kaggle (Unsloth — GPU T4/A100)
  pip install "unsloth[kaggle-new]" "trl>=0.12" "datasets>=2.19"
  # Local CPU/GPU (fallback)
  pip install "transformers>=4.47" "trl>=0.12" "peft>=0.14" \\
              "bitsandbytes>=0.44" "accelerate>=0.27" "datasets>=2.19"
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

# ── Guard: heavy imports only when actually running ───────────────────────────

def _require(pkg: str) -> None:
    import importlib
    if importlib.util.find_spec(pkg) is None:
        sys.exit(
            f"[finetune] Missing package: {pkg}\n"
            f"           pip install {pkg}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# 1.  SYNTHETIC SEED DATA
#     ~30 gold-standard examples covering every OmniScholar prompt mode.
#     Format: list of {"system": str, "user": str, "assistant": str}
# ═════════════════════════════════════════════════════════════════════════════

_SYSTEM = (
    "You are OmniScholar — an offline Sri Lankan A/L and first-year university "
    "tutor built on Gemma 4. Your job is to TEACH, not to answer. Respond only "
    "with the JSON format specified in the user message. Keep technical terms in "
    "English even inside Sinhala or Tamil responses."
)

# ── Virtual Teacher lessons ───────────────────────────────────────────────────
_VT_EXAMPLES: list[dict[str, Any]] = [
    {
        "topic": "Binary Search",
        "subject": "Data Structures",
        "language": "english",
        "assistant": json.dumps({
            "hook": "You know how you find a word in a dictionary? You don't read every page — you open to the middle and decide 'too early' or 'too late'. Binary search works exactly like that on sorted arrays.",
            "explanation": "Binary search finds a target in a sorted array by repeatedly halving the search space. It compares the target to the middle element: if equal, done; if smaller, search the left half; if larger, search the right half. Time: O(log n). Space: O(1) iterative, O(log n) recursive. Sri Lankan example: finding a name in a sorted SLIIT student register. Exam trap: students apply binary search on unsorted arrays and get wrong answers — it ONLY works on sorted data.",
            "worked_example": "Array: [2, 5, 8, 12, 16, 23, 38, 56]. Find 23.\nStep 1: lo=0, hi=7, mid=3 → arr[3]=12 < 23 → search right\nStep 2: lo=4, hi=7, mid=5 → arr[5]=23 == 23 → FOUND at index 5\nComparisons: 2 (vs ~8 for linear search).",
            "exam_hook": [
                "Define binary search and state its time complexity.",
                "Compare binary search and linear search. When is each preferred?",
                "Trace binary search on [1, 3, 7, 15, 31, 63] searching for 7. Show all steps."
            ],
            "check_questions": [
                {"question": "What is the prerequisite condition for binary search to work?", "expected_key_points": "array must be sorted; fails on unsorted data"},
                {"question": "A sorted array has 1024 elements. What is the maximum number of comparisons binary search needs?", "expected_key_points": "log2(1024) = 10 comparisons maximum"}
            ]
        }, ensure_ascii=False),
    },
    {
        "topic": "Deadlock",
        "subject": "Operating Systems",
        "language": "english",
        "assistant": json.dumps({
            "hook": "Imagine two students in a library: Kamal holds the Chemistry book and needs the Physics book, while Nimal holds the Physics book and needs the Chemistry book. Neither will release what they have. They're stuck forever — that's a deadlock.",
            "explanation": "A deadlock is a state where two or more processes are permanently blocked, each waiting for a resource held by another. The four Coffman conditions (ALL must hold simultaneously): 1) Mutual Exclusion — resource can't be shared. 2) Hold and Wait — process holds one resource and waits for another. 3) No Preemption — OS can't forcibly take a resource. 4) Circular Wait — P1→P2→P3→P1 resource chain. Time/Space: not applicable (it's a state, not an algorithm). Exam trap: students list only 3 of the 4 Coffman conditions.",
            "worked_example": "P1 holds R1, requests R2.\nP2 holds R2, requests R1.\nResource Allocation Graph: P1→R2, R1→P1, P2→R1, R2→P2.\nCycle detected: P1→R2→P2→R1→P1\n→ Deadlock confirmed. Resolution: kill P2, release R2, P1 proceeds.",
            "exam_hook": [
                "State the four Coffman conditions necessary for deadlock.",
                "Distinguish between deadlock prevention and deadlock avoidance.",
                "Draw the resource allocation graph for P1 holding R1, P2 holding R2, P1 requesting R2, P2 requesting R1."
            ],
            "check_questions": [
                {"question": "Name the four conditions that must ALL be present for a deadlock to occur.", "expected_key_points": "Mutual exclusion, Hold and Wait, No Preemption, Circular Wait — all four"},
                {"question": "If the OS can preempt resources from processes, can deadlock still occur? Explain.", "expected_key_points": "No — preemption breaks the No-Preemption condition, so deadlock cannot form even if the other three conditions hold"}
            ]
        }, ensure_ascii=False),
    },
    {
        "topic": "OSI Model",
        "subject": "Computer Networks",
        "language": "english",
        "assistant": json.dumps({
            "hook": "Think of sending a WhatsApp message to a friend in Jaffna. Your message travels through 7 different 'departments', each doing one specific job — encryption, addressing, error-checking. The OSI model names those 7 departments.",
            "explanation": "The OSI (Open Systems Interconnection) model is a conceptual framework that divides network communication into 7 layers: 7-Application (HTTP, FTP), 6-Presentation (encryption, compression), 5-Session (managing connections), 4-Transport (TCP/UDP, reliability), 3-Network (IP routing), 2-Data Link (MAC, frames), 1-Physical (bits, cables). Mnemonic: 'All People Seem To Need Data Processing' (top→bottom). Exam trap: students confuse OSI layer numbers — Layer 3 is Network (not Transport).",
            "worked_example": "Sending email from Colombo to London:\nL7: SMTP formats the email\nL6: TLS encrypts content\nL5: Session established\nL4: TCP splits into segments, adds port 25\nL3: IP adds source/destination IP addresses\nL2: Ethernet adds MAC addresses (next hop only)\nL1: Electrical signals travel through fiber",
            "exam_hook": [
                "Name and state the function of each OSI layer in order.",
                "Compare OSI and TCP/IP models. Which layers map to which?",
                "At which OSI layer does a router operate? Justify your answer."
            ],
            "check_questions": [
                {"question": "What is the function of the Transport layer (Layer 4) in the OSI model?", "expected_key_points": "end-to-end communication, reliability (TCP) or speed (UDP), segmentation, port numbers"},
                {"question": "A packet is received with a corrupt checksum. At which OSI layer is this detected and how?", "expected_key_points": "Layer 2 (Data Link) using CRC/FCS in the frame trailer; the frame is discarded"}
            ]
        }, ensure_ascii=False),
    },
    {
        "topic": "Inheritance in OOP",
        "subject": "Object Oriented Programming",
        "language": "english",
        "assistant": json.dumps({
            "hook": "In Sri Lanka, a son inherits his father's property — the house, land, and car. He can use everything the father has, and also buy new things himself. In OOP, a child class inherits attributes and methods from a parent class and can add its own.",
            "explanation": "Inheritance allows a class (child/subclass) to acquire properties and behaviors of another class (parent/superclass). Types: single, multilevel, multiple (not in Java), hierarchical, hybrid. Benefits: code reuse, method overriding, polymorphism. In Java: `class Dog extends Animal`. Time/Space: no runtime overhead beyond normal method dispatch. Exam trap: students confuse method overriding (runtime polymorphism) with method overloading (compile-time) — completely different mechanisms.",
            "worked_example": "class Animal:\n    def speak(self): return 'Some sound'\n    def breathe(self): return 'Inhales oxygen'  # inherited\n\nclass Dog(Animal):\n    def speak(self): return 'Woof!'  # overrides parent\n    def fetch(self): return 'Fetches ball'  # new method\n\nd = Dog()\nd.breathe()  # → 'Inhales oxygen'  (inherited)\nd.speak()    # → 'Woof!'            (overridden)\nd.fetch()    # → 'Fetches ball'     (own method)",
            "exam_hook": [
                "Define inheritance and list its types in OOP.",
                "Distinguish method overriding from method overloading with examples.",
                "Write a Java class hierarchy: Shape → Circle and Rectangle. Circle has radius, Rectangle has width and height. Implement area() in each."
            ],
            "check_questions": [
                {"question": "What is the difference between method overriding and method overloading?", "expected_key_points": "Overriding: same signature, different class (runtime); Overloading: same name, different parameters, same class (compile-time)"},
                {"question": "If class B extends class A and both define method display(), which version runs when you call display() on a B object? Why?", "expected_key_points": "B's version — runtime polymorphism; JVM dispatches to the most-derived override"}
            ]
        }, ensure_ascii=False),
    },
    {
        "topic": "SQL JOINs",
        "subject": "Database Management Systems",
        "language": "english",
        "assistant": json.dumps({
            "hook": "You have two class lists: one with student IDs and names, another with student IDs and marks. To see 'Kamal — 85', you need to combine both lists by matching the student ID. That matching is a JOIN.",
            "explanation": "A JOIN combines rows from two tables based on a related column. INNER JOIN: only matching rows (both sides must match). LEFT JOIN: all rows from left + matching from right (NULL if no match). RIGHT JOIN: opposite. FULL OUTER JOIN: all rows from both (NULL where no match). CROSS JOIN: every combination (Cartesian product). Time: O(n×m) naive, O(n log n) with indexed join. Exam trap: LEFT JOIN and RIGHT JOIN are NOT symmetric — which table is 'left' changes the result completely.",
            "worked_example": "Students: (1,Kamal), (2,Nimal), (3,Sahan)\nMarks:    (1,85), (2,72)\n\nINNER JOIN ON id:\n→ (1,Kamal,85), (2,Nimal,72)   — Sahan excluded\n\nLEFT JOIN ON id:\n→ (1,Kamal,85), (2,Nimal,72), (3,Sahan,NULL)  — Sahan included",
            "exam_hook": [
                "Explain INNER JOIN and LEFT JOIN with an example.",
                "When would you use a LEFT JOIN instead of an INNER JOIN?",
                "Write SQL to list all students and their marks, including students with no marks yet."
            ],
            "check_questions": [
                {"question": "What does a LEFT JOIN return that an INNER JOIN does not?", "expected_key_points": "LEFT JOIN includes all rows from the left table even when there is no matching row in the right table (NULL for right-side columns)"},
                {"question": "Table A has 4 rows, Table B has 3 rows. How many rows does CROSS JOIN produce?", "expected_key_points": "12 rows (4 × 3 Cartesian product)"}
            ]
        }, ensure_ascii=False),
    },
    # Sinhala example
    {
        "topic": "Sorting Algorithms",
        "subject": "Data Structures",
        "language": "sinhala",
        "assistant": json.dumps({
            "hook": "ඔබ examination hall එකේ papers sort කරනවා හිතන්න — marks අනුව order කරනවා. ඒ sort කිරීම algorithm එකක් use කළොත් ඒකට bubble sort, merge sort, quicksort කිව්ව method use කරන්න පුළුවන්.",
            "explanation": "Sorting algorithm කියන්නේ elements collection එකක් specified order (ascending/descending) ට arrange කරන procedure. Bubble Sort: O(n²) time, O(1) space — adjacent elements compare කරලා swap කරනවා. Merge Sort: O(n log n) time, O(n) space — divide and conquer. Quick Sort: O(n log n) average, O(n²) worst — pivot use කරනවා. Exam trap: students bubble sort stable sorting algorithm කියා ලිවීලා ඒ correct, but quicksort stable නෙවෙ කියා forget කරනවා.",
            "worked_example": "Bubble Sort trace — [5, 3, 8, 1]:\nPass 1: [3,5,8,1] → [3,5,8,1] → [3,5,1,8]\nPass 2: [3,5,1,8] → [3,1,5,8]\nPass 3: [1,3,5,8] ✓ sorted\n\nComparisons: 6 (n(n-1)/2 = 4×3/2)",
            "exam_hook": [
                "Bubble sort සහ merge sort compare කරන්නේ කොහොමද? Time complexity සහ stability අනුව.",
                "Quick sort worst case O(n²) වෙන්නේ කවදාද?",
                "[4, 2, 7, 1, 9] array එක bubble sort use කරලා ascending order ට sort කරන්න. Steps show කරන්න."
            ],
            "check_questions": [
                {"question": "Merge sort stable sorting algorithm ද? ඒ concept explain කරන්නේ කොහොමද?", "expected_key_points": "ඔව් — equal elements relative order change නොවෙ; left subarray merge කරනකොට equal element left side from first taken"},
                {"question": "n=8 array එකට bubble sort worst case comparisons කීයද?", "expected_key_points": "n(n-1)/2 = 8×7/2 = 28 comparisons"}
            ]
        }, ensure_ascii=False),
    },
]

# ── Battle game MCQ examples ──────────────────────────────────────────────────
_BATTLE_EXAMPLES: list[dict[str, Any]] = [
    {
        "topic": "Data Structures", "difficulty": "medium",
        "assistant": json.dumps({
            "question": "A stack implemented using an array has a push and pop operation. What is the time complexity of both operations?",
            "options": [
                "A. O(n) push, O(1) pop",
                "B. O(1) push, O(1) pop",
                "C. O(log n) push, O(log n) pop",
                "D. O(n) push, O(n) pop"
            ],
            "correct": "B",
            "explanation": "Both push and pop on an array-backed stack are O(1) because they only modify the top element. A common misconception is thinking array operations are O(n) — that applies to insertion/deletion at arbitrary positions, not at the top."
        }, ensure_ascii=False),
    },
    {
        "topic": "Algorithms", "difficulty": "hard",
        "assistant": json.dumps({
            "question": "Dijkstra's algorithm fails to produce correct shortest paths when the graph contains:",
            "options": [
                "A. Cycles",
                "B. Negative weight edges",
                "C. Disconnected components",
                "D. Multiple edges between the same pair of nodes"
            ],
            "correct": "B",
            "explanation": "Dijkstra assumes edge weights are non-negative; negative weights can cause it to finalize a node distance before finding a cheaper path through a negative edge. For negative weights, use Bellman-Ford. Cycles alone are fine as long as weights are non-negative."
        }, ensure_ascii=False),
    },
    {
        "topic": "Operating Systems", "difficulty": "easy",
        "assistant": json.dumps({
            "question": "Which scheduling algorithm can cause starvation of low-priority processes?",
            "options": [
                "A. Round Robin",
                "B. First Come First Served",
                "C. Priority Scheduling",
                "D. Shortest Job First (non-preemptive)"
            ],
            "correct": "C",
            "explanation": "Priority Scheduling continuously favors high-priority processes; low-priority processes may never run if high-priority tasks keep arriving. Round Robin and FCFS are fair by design. SJF can cause starvation of long jobs but the question specifically asks about priority-based starvation."
        }, ensure_ascii=False),
    },
    {
        "topic": "Database Management Systems", "difficulty": "medium",
        "assistant": json.dumps({
            "question": "Which normal form eliminates transitive dependencies?",
            "options": [
                "A. 1NF",
                "B. 2NF",
                "C. 3NF",
                "D. BCNF"
            ],
            "correct": "C",
            "explanation": "3NF removes transitive dependencies (non-key attribute depending on another non-key attribute). 2NF removes partial dependencies. BCNF is stricter than 3NF and handles anomalies in multi-valued keys. Students often confuse 2NF (partial) with 3NF (transitive)."
        }, ensure_ascii=False),
    },
    {
        "topic": "Computer Networks", "difficulty": "hard",
        "assistant": json.dumps({
            "question": "TCP's three-way handshake establishes a connection with which sequence of flags?",
            "options": [
                "A. SYN → SYN-ACK → ACK",
                "B. ACK → SYN → SYN-ACK",
                "C. SYN → ACK → FIN",
                "D. SYN-ACK → SYN → ACK"
            ],
            "correct": "A",
            "explanation": "Client sends SYN, server responds SYN-ACK, client completes with ACK. This exchange synchronizes sequence numbers on both sides. The incorrect options have the wrong initiator or wrong flag order — a common exam trap."
        }, ensure_ascii=False),
    },
]

# ── Socratic follow-up examples ───────────────────────────────────────────────
_SOCRATIC_EXAMPLES: list[dict[str, Any]] = [
    {
        "topic": "Binary Search", "language": "english",
        "question": "What is the time complexity of binary search?",
        "student_answer": "O(n) because we look through the whole array",
        "expected": "O(log n) — each step halves the search space",
        "assistant": json.dumps({
            "acknowledgement": "You're right that we do look at elements — but think about HOW MANY elements we actually check compared to linear search.",
            "probing_question": "If the array has 16 elements and you eliminate half each step, how many steps does it take to get down to 1 element?",
            "nudge": "Count the halvings: 16 → 8 → 4 → 2 → 1. That number of steps is the time complexity."
        }, ensure_ascii=False),
    },
    {
        "topic": "Deadlock", "language": "english",
        "question": "Name all four Coffman conditions for deadlock.",
        "student_answer": "Mutual exclusion, hold and wait, and circular wait",
        "expected": "Mutual exclusion, hold and wait, no preemption, circular wait",
        "assistant": json.dumps({
            "acknowledgement": "You've correctly identified three of the four — mutual exclusion, hold and wait, and circular wait are all right.",
            "probing_question": "What happens if the OS can forcibly take a resource away from a process? Can deadlock still form?",
            "nudge": "Think about the condition related to whether the OS can remove a resource from a process that is currently using it."
        }, ensure_ascii=False),
    },
]

# ── Weakness ZPD diagnostic examples ─────────────────────────────────────────
_WEAKNESS_EXAMPLES: list[dict[str, Any]] = [
    {
        "student": "Kamal", "subject": "Data Structures",
        "language": "english", "weak_areas": "Binary Trees, Recursion",
        "assistant": (
            "**Binary Trees — ZPD Diagnostic**\n\n"
            "**DIAGNOSIS:** Confusion between tree traversal orders "
            "(inorder/preorder/postorder) — students apply them interchangeably "
            "without understanding what each produces.\n\n"
            "**PREREQUISITE:** Recursion must be solid. If you cannot trace a "
            "simple recursive function by hand, tree traversal will not click.\n\n"
            "**SCAFFOLD STEP 1:** Draw a tree with 3 nodes (root, left, right). "
            "Manually write the inorder sequence. Why does inorder give sorted "
            "output for a BST?\n\n"
            "**SCAFFOLD STEP 2:** Given `Tree: 4→(2,6), 2→(1,3)` — write the "
            "preorder traversal. Trace the recursive call stack step by step.\n\n"
            "**SCAFFOLD STEP 3:** Implement `inorder(node)` in Python without "
            "looking at notes. Time it and compare with iterative using a stack.\n\n"
            "**CHECK QUESTION:** For the BST `[8, 3, 10, 1, 6, 14, 4, 7]`, "
            "write the inorder traversal. What property does the result demonstrate?"
        ),
    },
]

# ── Mid-lesson probe examples ─────────────────────────────────────────────────
_MID_QUESTION_EXAMPLES: list[dict[str, Any]] = [
    {
        "topic": "Binary Search", "subject": "Data Structures",
        "language": "english",
        "just_explained": "Binary search halves the search space each step, giving O(log n) time complexity",
        "assistant": json.dumps({
            "question": "Quick check — if binary search is O(log n), why can't you use it on a linked list even if the values are sorted?",
            "expected": "Random access (arr[mid]) is O(1) on arrays but O(n) on linked lists, making binary search O(n log n) — worse than linear search",
            "hint": "Think about what 'find the middle element' costs on a linked list versus an array."
        }, ensure_ascii=False),
    },
]


def build_synthetic_dataset() -> list[dict]:
    """
    Convert all seed examples into the messages format:
    [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]
    """
    rows: list[dict] = []

    # Virtual Teacher lessons
    for ex in _VT_EXAMPLES:
        user = (
            f"Teach me {ex['topic']} in {ex['subject']}. "
            f"Language: {ex['language']}. "
            "Return the lesson as JSON with keys: hook, explanation, "
            "worked_example, exam_hook, check_questions."
        )
        rows.append(_make_row(_SYSTEM, user, ex["assistant"]))

    # Battle game MCQs
    for ex in _BATTLE_EXAMPLES:
        user = (
            f"Generate one {ex['difficulty']} MCQ for topic: {ex['topic']}. "
            "Return ONLY valid JSON with keys: question, options (array of 4 strings "
            "A./B./C./D.), correct (single letter), explanation."
        )
        rows.append(_make_row(_SYSTEM, user, ex["assistant"]))

    # Socratic follow-ups
    for ex in _SOCRATIC_EXAMPLES:
        user = (
            f"Topic: {ex['topic']}. Language: {ex['language']}.\n"
            f"Question asked: {ex['question']}\n"
            f"Student's wrong answer: {ex['student_answer']}\n"
            f"Expected: {ex['expected']}\n"
            "Apply REVOICE→PROBE→NUDGE. Return ONLY valid JSON: "
            "acknowledgement, probing_question, nudge."
        )
        rows.append(_make_row(_SYSTEM, user, ex["assistant"]))

    # Weakness ZPD diagnostics
    for ex in _WEAKNESS_EXAMPLES:
        user = (
            f"Student: {ex['student']} | Subject: {ex['subject']} | "
            f"Language: {ex['language']}\n"
            f"Weak areas: {ex['weak_areas']}\n"
            "Produce a ZPD diagnostic block: "
            "DIAGNOSIS, PREREQUISITE, SCAFFOLD STEP 1-3, CHECK QUESTION."
        )
        rows.append(_make_row(_SYSTEM, user, ex["assistant"]))

    # Mid-lesson probe questions
    for ex in _MID_QUESTION_EXAMPLES:
        user = (
            f"Subject: {ex['subject']} | Topic: {ex['topic']} | "
            f"Language: {ex['language']}\n"
            f"Just explained: {ex['just_explained']}\n"
            "Generate ONE mid-lesson probe question (WHY/HOW, Bloom 2-3). "
            "Return ONLY valid JSON: question, expected, hint."
        )
        rows.append(_make_row(_SYSTEM, user, ex["assistant"]))

    return rows


def _make_row(system: str, user: str, assistant: str) -> dict:
    return {
        "messages": [
            {"role": "system",    "content": system},
            {"role": "user",      "content": user},
            {"role": "assistant", "content": assistant},
        ]
    }


# ═════════════════════════════════════════════════════════════════════════════
# 2.  REAL DATA FROM SQLITE
# ═════════════════════════════════════════════════════════════════════════════

def load_db_examples(db_path: str) -> list[dict]:
    """
    Pull real interactions from omnischolar.db:
      - saved_lessons  → virtual teacher lesson pairs
    Returns list of message-dicts in the same format as synthetic data.
    """
    rows: list[dict] = []
    if not os.path.isfile(db_path):
        print(f"[finetune] DB not found at {db_path} — skipping real data.")
        return rows

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # saved_lessons table: (student_id, subject, topic, content, created_at)
        cur.execute(
            "SELECT subject, topic, content FROM saved_lessons "
            "WHERE content IS NOT NULL AND length(content) > 100 "
            "ORDER BY created_at DESC LIMIT 500"
        )
        for row in cur.fetchall():
            try:
                content = json.loads(row["content"])
                # Strip internal keys that aren't part of the lesson response
                lesson = {
                    k: content[k]
                    for k in ("hook", "explanation", "worked_example",
                              "exam_hook", "check_questions")
                    if k in content
                }
                if len(lesson) < 3:
                    continue
                user = (
                    f"Teach me {row['topic']} in {row['subject']}. "
                    "Return the lesson as JSON with keys: hook, explanation, "
                    "worked_example, exam_hook, check_questions."
                )
                rows.append(
                    _make_row(_SYSTEM, user, json.dumps(lesson, ensure_ascii=False))
                )
            except Exception:
                continue

        conn.close()
        print(f"[finetune] Loaded {len(rows)} examples from {db_path}")
    except Exception as exc:
        print(f"[finetune] DB read error: {exc}")

    return rows


# ═════════════════════════════════════════════════════════════════════════════
# 2b.  JSONL DIRECTORY LOADER
#      Supports conversations / messages format, role/content or from/value
# ═════════════════════════════════════════════════════════════════════════════

_ROLE_MAP = {
    "human": "user", "Human": "user",
    "gpt": "assistant", "GPT": "assistant",
    "bot": "assistant",
}


def load_jsonl_dir(data_path: str) -> list[dict]:
    """
    Load training examples from a directory (or single file) of JSONL/JSON.
    Accepted row shapes:
      {"messages": [{"role": ..., "content": ...}, ...]}
      {"conversations": [{"role": ..., "content": ...}, ...]}
      {"conversations": [{"from": "human", "value": ...}, ...]}
    """
    path = Path(data_path)
    if not path.exists():
        print(f"[finetune] Data path not found: {data_path} — skipping.")
        return []

    if path.is_file():
        files = [path]
    else:
        files = sorted(path.rglob("*.jsonl")) + sorted(path.rglob("*.json"))
        files = list(dict.fromkeys(files))  # deduplicate, preserve order

    rows: list[dict] = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    raw = obj.get("messages") or obj.get("conversations")
                    if not raw:
                        continue
                    # Normalise field names
                    msgs: list[dict] = []
                    for m in raw:
                        role    = m.get("role") or m.get("from", "user")
                        content = m.get("content") or m.get("value", "")
                        role    = _ROLE_MAP.get(role, role)
                        msgs.append({"role": role, "content": str(content)})
                    # Prepend system prompt if absent
                    if msgs and msgs[0]["role"] != "system":
                        msgs.insert(0, {"role": "system", "content": _SYSTEM})
                    if len(msgs) >= 2:
                        rows.append({"messages": msgs})
        except Exception as exc:
            print(f"[finetune] Warning: could not parse {f}: {exc}")

    print(f"[finetune] Loaded {len(rows)} examples from JSONL at {data_path}")
    return rows


# ═════════════════════════════════════════════════════════════════════════════
# 3.  TRAINING ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="QLoRA fine-tune Gemma 4 on OmniScholar data"
    )
    p.add_argument("--model_id",    default="unsloth/gemma-4-E2B-it",
                   help="HuggingFace model id (default: unsloth/gemma-4-E2B-it)")
    p.add_argument("--db_path",     default="omnischolar/omnischolar.db",
                   help="SQLite .db file OR directory of .jsonl files")
    p.add_argument("--output",      default="./checkpoints/omnischolar-lora",
                   help="Directory to save LoRA adapter")
    p.add_argument("--epochs",      type=int,   default=3)
    p.add_argument("--batch",       type=int,   default=2,
                   help="Per-device training batch size")
    p.add_argument("--grad_accum",  type=int,   default=4,
                   help="Gradient accumulation steps (effective batch = batch×grad_accum)")
    p.add_argument("--lr",          type=float, default=2e-4)
    p.add_argument("--max_seq_len", type=int,   default=2048)
    p.add_argument("--lora_r",      type=int,   default=16)
    p.add_argument("--lora_alpha",  type=int,   default=16)
    p.add_argument("--lora_dropout",type=float, default=0.05)
    p.add_argument("--push_to_hub", action="store_true",
                   help="Push LoRA adapter to HuggingFace Hub after training")
    p.add_argument("--hub_repo",    default="",
                   help="HuggingFace repo id to push to (e.g. kowshikan/omnischolar-gemma4-edu)")
    p.add_argument("--dry_run",     action="store_true",
                   help="Print dataset stats and exit without training")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # ── Collect dataset ───────────────────────────────────────────────────────
    synthetic = build_synthetic_dataset()
    # Route --db_path to the right loader based on what it points to
    db_path = Path(args.db_path)
    if db_path.is_dir() or (db_path.suffix in (".jsonl", ".json")):
        real = load_jsonl_dir(args.db_path)
    else:
        real = load_db_examples(args.db_path)
    all_rows  = synthetic + real

    print(f"[finetune] Total examples: {len(all_rows)} "
          f"({len(synthetic)} synthetic + {len(real)} from DB)")

    if args.dry_run:
        print("\n[finetune] --dry_run: first example preview:")
        print(json.dumps(all_rows[0], indent=2, ensure_ascii=False)[:800])
        print("... (truncated)\n[finetune] Exiting dry run.")
        return

    if len(all_rows) < 5:
        sys.exit("[finetune] Dataset too small (<5 examples). "
                 "Add real data or check --db_path.")

    # ── Lazy imports ──────────────────────────────────────────────────────────
    for pkg in ("datasets", "torch"):
        _require(pkg)

    import torch
    from datasets import Dataset

    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN") or ""
    if hf_token:
        try:
            from huggingface_hub import login as hf_login
            hf_login(token=hf_token, add_to_git_credential=False)
            print("[finetune] Logged in to HuggingFace Hub via token.")
        except Exception as _e:
            print(f"[finetune] HF login warning: {_e}")
    else:
        print("[finetune] WARNING: HF_TOKEN / HUGGINGFACE_TOKEN not set. "
              "Private models and Hub push will fail.\n"
              "           Set it in Kaggle Secrets → HF_TOKEN, or export it "
              "before running.")

    # ── Try Unsloth first (Kaggle / GPU), fall back to transformers + PEFT ────
    try:
        import importlib
        if importlib.util.find_spec("unsloth") is None:
            raise ImportError("unsloth not installed")
        from unsloth import FastLanguageModel
        USE_UNSLOTH = True
        print("[finetune] Backend: Unsloth (fast path)")
    except ImportError:
        USE_UNSLOTH = False
        print("[finetune] Backend: transformers + PEFT (standard path)")
        for pkg in ("transformers", "peft", "trl", "bitsandbytes", "accelerate"):
            _require(pkg)

    _LORA_TARGETS = [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ]

    # ── Load model + tokenizer ────────────────────────────────────────────────
    if USE_UNSLOTH:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=args.model_id,
            max_seq_length=args.max_seq_len,
            dtype=None,          # auto-detect bfloat16 / float16
            load_in_4bit=True,
            token=hf_token or None,
        )
        model = FastLanguageModel.get_peft_model(
            model,
            r=args.lora_r,
            target_modules=_LORA_TARGETS,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=42,
        )
    else:
        from peft import LoraConfig, TaskType, get_peft_model
        from transformers import (
            AutoModelForCausalLM, AutoTokenizer,
            BitsAndBytesConfig,
        )
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
        print(f"[finetune] Loading tokenizer: {args.model_id}")
        tokenizer = AutoTokenizer.from_pretrained(
            args.model_id, token=hf_token or None, trust_remote_code=True,
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "right"

        print(f"[finetune] Loading model: {args.model_id}  (4-bit QLoRA)")
        model = AutoModelForCausalLM.from_pretrained(
            args.model_id,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            token=hf_token or None,
            torch_dtype=torch.bfloat16,
        )
        model.config.use_cache = False
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            target_modules=_LORA_TARGETS,
            bias="none",
        )
        model = get_peft_model(model, lora_config)

    model.print_trainable_parameters()

    # ── Format dataset using the tokenizer's chat template ───────────────────
    def format_example(example: dict) -> dict:
        text = tokenizer.apply_chat_template(
            example["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )
        return {"text": text}

    dataset = Dataset.from_list(all_rows)
    dataset = dataset.map(format_example, remove_columns=["messages"])

    split    = dataset.train_test_split(test_size=0.1, seed=42)
    train_ds = split["train"]
    eval_ds  = split["test"]
    print(f"[finetune] Train: {len(train_ds)}  Eval: {len(eval_ds)}")

    # ── Training arguments ────────────────────────────────────────────────────
    from transformers import TrainingArguments
    training_args = TrainingArguments(
        output_dir=args.output,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=args.batch,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        weight_decay=0.01,
        fp16=False,
        bf16=(not USE_UNSLOTH) and torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        report_to="none",
        gradient_checkpointing=(not USE_UNSLOTH),  # unsloth handles its own
        dataloader_num_workers=0,
        optim="adamw_8bit" if USE_UNSLOTH else "adamw_torch",
    )

    # ── Trainer — handle both old (tokenizer=) and new (processing_class=) TRL ─
    from trl import SFTTrainer
    import inspect
    _sft_sig = inspect.signature(SFTTrainer.__init__).parameters
    _tokenizer_kwarg = "processing_class" if "processing_class" in _sft_sig else "tokenizer"

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        **{_tokenizer_kwarg: tokenizer},
        dataset_text_field="text",
        max_seq_length=args.max_seq_len,
        packing=False,
    )

    # ── Train ─────────────────────────────────────────────────────────────────
    print("[finetune] Starting training...")
    trainer.train()

    # ── Save ──────────────────────────────────────────────────────────────────
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(output_path))
    tokenizer.save_pretrained(str(output_path))
    print(f"[finetune] LoRA adapter saved to {output_path}")

    # ── Push to Hub ───────────────────────────────────────────────────────────
    if args.push_to_hub:
        repo = args.hub_repo or os.getenv("HUGGINGFACE_REPO", "")
        if not repo:
            print("[finetune] --push_to_hub set but no --hub_repo given. "
                  "Set --hub_repo or HUGGINGFACE_REPO env var. Skipping push.")
        else:
            if not hf_token:
                print("[finetune] WARNING: HF_TOKEN not set — push may fail.")
            print(f"[finetune] Pushing adapter to HuggingFace Hub: {repo}")
            model.push_to_hub(repo, token=hf_token or None)
            tokenizer.push_to_hub(repo, token=hf_token or None)
            print("[finetune] Push complete.")

    print("[finetune] Done.")


main()
