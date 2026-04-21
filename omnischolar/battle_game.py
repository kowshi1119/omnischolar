"""
battle_game.py — CS Tug-of-War Battle Game (Mode 12) for OmniScholar

A fast-paced competitive flashcard game. The rope moves left/right
based on correct/wrong answers. Streak bonuses available.
Uses fast_chat() for <2s question generation.
"""

import random

import streamlit as st

from prompt import BATTLE_GAME_PROMPT


# ── CS topic bank ─────────────────────────────────────────────────────────────
CS_TOPICS = [
    "Data Structures", "Algorithms", "Operating Systems",
    "Computer Networks", "Database Systems", "Object-Oriented Programming",
    "Computer Architecture", "Software Engineering", "Cryptography",
    "Compilers", "Distributed Systems", "Machine Learning Basics",
]


import streamlit.components.v1 as components


def _render_rope(position: int, score: int = 0, streak: int = 0) -> None:
    """Animated tug-of-war rope. position: -5 (player wins) to +5 (AI wins)."""
    WIN = 5
    # Map position to percentage (0% = player side, 100% = AI side)
    pct = int(50 + (position / WIN) * 42)   # clamp visually to 8–92%
    pct = max(8, min(92, pct))

    streak_html = (
        '<span style="font-size:1.1rem;margin-left:6px;">🔥</span>' * min(streak, 3)
        if streak >= 3 else ""
    )
    score_html = f"""
    <div style="display:flex;justify-content:space-between;
                font-family:Orbitron,monospace;font-size:0.75rem;
                color:#A0B4D6;margin-bottom:6px;padding:0 4px;">
      <span style="color:#00D4FF;font-weight:700;">YOU &nbsp;{score}{streak_html}</span>
      <span style="color:#EF4444;font-weight:700;">AI &nbsp;–</span>
    </div>
    """

    components.html(f"""
    <style>
      @keyframes ropeWiggle {{
        0%,100% {{ transform: scaleY(1); }}
        50%      {{ transform: scaleY(1.08); }}
      }}
      @keyframes knotPulse {{
        0%,100% {{ transform: scale(1);   box-shadow: 0 0 6px #fff8; }}
        50%      {{ transform: scale(1.3); box-shadow: 0 0 16px #fffc; }}
      }}
      @keyframes pullLeft {{
        0%,100% {{ transform: translateX(0); }}
        50%      {{ transform: translateX(-4px); }}
      }}
      @keyframes pullRight {{
        0%,100% {{ transform: translateX(0); }}
        50%      {{ transform: translateX(4px); }}
      }}
    </style>
    <div style="padding:12px 8px;
                background:linear-gradient(135deg,#0D1B35,#111929);
                border-radius:12px;margin:8px 0;
                border:1px solid rgba(0,212,255,0.15);">
      {score_html}
      <div style="position:relative;height:36px;margin:0 8px;">
        <!-- rope fill: player side (cyan) -->
        <div style="position:absolute;top:50%;left:0;width:{pct}%;height:8px;
                    transform:translateY(-50%);
                    background:linear-gradient(90deg,#00D4FF,#0088AA);
                    border-radius:4px 0 0 4px;
                    animation:ropeWiggle 0.6s ease-in-out infinite;"></div>
        <!-- rope fill: AI side (amber) -->
        <div style="position:absolute;top:50%;left:{pct}%;right:0;height:8px;
                    transform:translateY(-50%);
                    background:linear-gradient(90deg,#AA5500,#EF4444);
                    border-radius:0 4px 4px 0;
                    animation:ropeWiggle 0.6s ease-in-out infinite;"></div>
        <!-- win zone markers -->
        <div style="position:absolute;top:0;left:8%;width:2px;height:100%;
                    background:rgba(0,212,255,0.5);border-radius:1px;"></div>
        <div style="position:absolute;top:0;left:92%;width:2px;height:100%;
                    background:rgba(239,68,68,0.5);border-radius:1px;"></div>
        <!-- animated knot -->
        <div style="position:absolute;top:50%;left:{pct}%;
                    transform:translate(-50%,-50%);
                    width:18px;height:18px;border-radius:50%;
                    background:white;
                    animation:knotPulse 0.5s ease-in-out infinite;
                    z-index:2;"></div>
        <!-- player puller -->
        <div style="position:absolute;top:50%;left:0;
                    transform:translateY(-50%);
                    font-size:1.4rem;
                    animation:pullLeft 0.6s ease-in-out infinite;">💪</div>
        <!-- AI puller -->
        <div style="position:absolute;top:50%;right:0;
                    transform:translateY(-50%) scaleX(-1);
                    font-size:1.4rem;
                    animation:pullRight 0.6s ease-in-out infinite;">💪</div>
      </div>
    </div>
    """, height=100)


def _fetch_question(topic: str, difficulty: str, llm) -> dict | None:
    """Fetch a single MCQ. Falls back to local question bank if LLM fails."""
    # Try LLM first
    prompt = BATTLE_GAME_PROMPT.format(topic=topic, difficulty=difficulty)
    try:
        import json
        raw = llm.fast_chat(
            message=prompt,
            system="Return ONLY valid JSON array. No markdown. No prose.",
            max_tokens=300,
        )
        raw = raw.strip()
        # Strip markdown fences
        for fence in ["```json", "```"]:
            raw = raw.replace(fence, "").strip()

        q = json.loads(raw)

        # Normalize options format
        opts = q.get("options", [])
        if isinstance(opts, dict):
            q["options"] = [f"{k}. {v}" for k, v in opts.items()]
        elif isinstance(opts, list):
            normalized = []
            for i, opt in enumerate(opts):
                letter = chr(65 + i)
                s = str(opt)
                if not s.startswith(f"{letter}.") and not s.startswith(f"{letter} "):
                    normalized.append(f"{letter}. {s}")
                else:
                    normalized.append(s)
            q["options"] = normalized

        # Validate
        if q.get("question") and len(q.get("options", [])) == 4 and q.get("correct"):
            return q
    except Exception:
        pass

    # Fallback: return from local question bank
    return _get_fallback_question(topic, difficulty)


def _get_fallback_question(topic: str, difficulty: str) -> dict:
    """Local question bank — always works, no Ollama needed."""
    import random
    bank = {
        "Data Structures": [
            {"question": "Which data structure uses LIFO (Last In, First Out)?",
             "options": ["A. Queue", "B. Stack", "C. Heap", "D. Tree"],
             "correct": "B",
             "explanation": "A Stack uses LIFO — the last element pushed is the first popped."},
            {"question": "What is the time complexity of binary search?",
             "options": ["A. O(n)", "B. O(n²)", "C. O(log n)", "D. O(1)"],
             "correct": "C",
             "explanation": "Binary search halves the search space each step, giving O(log n)."},
            {"question": "Which structure gives O(1) average-case lookup?",
             "options": ["A. Linked List", "B. Binary Tree", "C. Hash Table", "D. Stack"],
             "correct": "C",
             "explanation": "Hash tables use a hash function for O(1) average lookup."},
        ],
        "Algorithms": [
            {"question": "What is the worst-case time complexity of quicksort?",
             "options": ["A. O(n log n)", "B. O(n)", "C. O(n²)", "D. O(log n)"],
             "correct": "C",
             "explanation": "Quicksort degrades to O(n²) when pivot selection is poor (sorted input)."},
            {"question": "Which algorithm finds shortest path in a weighted graph?",
             "options": ["A. DFS", "B. BFS", "C. Dijkstra's", "D. Kruskal's"],
             "correct": "C",
             "explanation": "Dijkstra's algorithm finds the shortest path using a priority queue."},
        ],
        "Operating Systems": [
            {"question": "What are the four necessary conditions for deadlock?",
             "options": ["A. Mutex, Hold&Wait, No preemption, Circular wait",
                         "B. Starvation, Aging, Priority, Scheduling",
                         "C. Paging, Segmentation, Swapping, Thrashing",
                         "D. Fork, Join, Signal, Wait"],
             "correct": "A",
             "explanation": "Coffman's four conditions: Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait."},
            {"question": "What is thrashing in OS memory management?",
             "options": ["A. CPU overheating", "B. Excessive paging causing low CPU utilization",
                         "C. Memory fragmentation", "D. Cache miss rate increasing"],
             "correct": "B",
             "explanation": "Thrashing occurs when a process spends more time paging than executing."},
        ],
        "Computer Networks": [
            {"question": "Which layer of OSI handles IP addressing?",
             "options": ["A. Physical", "B. Data Link", "C. Network", "D. Transport"],
             "correct": "C",
             "explanation": "The Network layer (Layer 3) handles logical addressing and routing via IP."},
            {"question": "TCP vs UDP — which is connection-oriented?",
             "options": ["A. UDP", "B. Both", "C. Neither", "D. TCP"],
             "correct": "D",
             "explanation": "TCP establishes a connection via 3-way handshake. UDP is connectionless."},
        ],
        "Database Systems": [
            {"question": "What does ACID stand for in database transactions?",
             "options": ["A. Atomicity, Consistency, Isolation, Durability",
                         "B. Access, Control, Index, Data",
                         "C. Abstraction, Concurrency, Integrity, Design",
                         "D. Authentication, Consistency, Integration, Distribution"],
             "correct": "A",
             "explanation": "ACID ensures reliable database transactions: Atomic, Consistent, Isolated, Durable."},
        ],
        "Object-Oriented Programming": [
            {"question": "What is polymorphism in OOP?",
             "options": ["A. A class with multiple constructors",
                         "B. Same interface, different implementations",
                         "C. A class inheriting from multiple parents",
                         "D. Hiding internal data from outside"],
             "correct": "B",
             "explanation": "Polymorphism allows objects of different types to be treated as a common type."},
            {"question": "What is encapsulation?",
             "options": ["A. Extending a class", "B. Overriding methods",
                         "C. Bundling data and methods, hiding internal state",
                         "D. Creating multiple objects"],
             "correct": "C",
             "explanation": "Encapsulation bundles data and behavior together and restricts direct access."},
        ],
    }

    # Get questions for this topic, fall back to Data Structures
    questions = bank.get(topic, bank.get("Data Structures", []))
    if not questions:
        questions = bank["Data Structures"]

    return random.choice(questions)




def render_battle_game_mode(student: dict, ollama_client, db) -> None:
    """Render the CS Battle Game mode."""
    st.markdown("## ⚔ CS Battle Mode")
    st.caption(
        "Answer faster than the AI. Every correct answer pulls the rope your way. "
        "3 wrong answers in a row and the AI wins."
    )

    # ── State init ─────────────────────────────────────────────────────────────
    if "battle_rope"     not in st.session_state: st.session_state["battle_rope"]     = 0
    if "battle_streak"   not in st.session_state: st.session_state["battle_streak"]   = 0
    if "battle_wrongs"   not in st.session_state: st.session_state["battle_wrongs"]   = 0
    if "battle_q"        not in st.session_state: st.session_state["battle_q"]        = None
    if "battle_answered" not in st.session_state: st.session_state["battle_answered"] = False
    if "battle_score"    not in st.session_state: st.session_state["battle_score"]    = 0
    if "battle_active"   not in st.session_state: st.session_state["battle_active"]   = False

    rope   = st.session_state["battle_rope"]
    streak = st.session_state["battle_streak"]
    wrongs = st.session_state["battle_wrongs"]
    score  = st.session_state["battle_score"]

    # ── Game over check ────────────────────────────────────────────────────────
    if rope >= 5:
        st.success(f"🏆 You won! Score: {score} | Streak peak: {streak}")
        if st.button("🔄 Play Again"):
            for k in ("battle_rope","battle_streak","battle_wrongs","battle_q",
                      "battle_answered","battle_score","battle_active"):
                st.session_state.pop(k, None)
            st.rerun()
        return

    if rope <= -5 or wrongs >= 3:
        st.error(f"💀 AI wins! Score: {score} | Keep practising!")
        if st.button("🔄 Try Again"):
            for k in ("battle_rope","battle_streak","battle_wrongs","battle_q",
                      "battle_answered","battle_score","battle_active"):
                st.session_state.pop(k, None)
            st.rerun()
        return

    # ── Start / scoreboard ─────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric("Score",  score)
    col2.metric("Streak", f"🔥 {streak}")
    col3.metric("Lives",  "❤" * max(0, 3 - wrongs))

    _render_rope(rope, score=score, streak=streak)

    # ── Topic selector ─────────────────────────────────────────────────────────
    topic = st.selectbox("Topic", CS_TOPICS, key="battle_topic")
    diff  = st.radio("Difficulty", ["easy", "medium", "hard"],
                     horizontal=True, key="battle_diff")

    # ── Bloom ladder: auto-adapt difficulty based on streak/wrongs ─────────────
    auto_diff = diff
    if streak >= 5 and diff in ("easy", "medium"):
        auto_diff = "hard"
    elif streak >= 3 and diff == "easy":
        auto_diff = "medium"
    elif wrongs >= 2 and diff == "hard":
        auto_diff = "medium"
    elif wrongs >= 2 and diff == "medium":
        auto_diff = "easy"
    if auto_diff != diff:
        st.caption(f"⚡ Auto-difficulty adjusted to **{auto_diff}** based on your performance.")

    # ── Fetch new question ─────────────────────────────────────────────────────
    if not st.session_state["battle_active"]:
        if st.button("⚔ Start Battle", type="primary"):
            st.session_state["battle_active"]   = True
            st.session_state["battle_q"]        = None
            st.session_state["battle_answered"] = False
            st.rerun()
        return

    if st.session_state["battle_q"] is None or st.session_state["battle_answered"]:
        with st.spinner("Loading next question..."):
            q = _fetch_question(topic, auto_diff, ollama_client)
        if q is None:
            st.warning("Could not load question — make sure Ollama is running.")
            return
        st.session_state["battle_q"]        = q
        st.session_state["battle_answered"] = False
        st.rerun()

    q = st.session_state["battle_q"]
    if not isinstance(q, dict):
        st.session_state["battle_q"] = None
        st.rerun()
        return

    # ── Render question ────────────────────────────────────────────────────────
    st.markdown(f"**Q: {q.get('question', '')}**")
    options = q.get("options", [])
    if not options:
        st.session_state["battle_q"] = None
        st.rerun()
        return

    answer = st.radio("Choose:", options, key=f"battle_ans_{score}")
    if st.button("✓ Submit Answer"):
        correct_key = q.get("correct", "")
        # Accept full match or leading letter match (e.g. "A" matches "A. description")
        player_key = answer.split(".")[0].strip().upper() if answer else ""
        if player_key == correct_key.upper() or answer == correct_key:
            st.session_state["battle_streak"] += 1
            bonus = 2 if st.session_state["battle_streak"] >= 3 else 1
            st.session_state["battle_score"] += bonus
            st.session_state["battle_rope"]  += bonus
            st.session_state["battle_wrongs"]  = 0
            st.success(f"✓ Correct! {'+2 STREAK BONUS' if bonus == 2 else '+1'}")
        else:
            st.session_state["battle_streak"] = 0
            st.session_state["battle_rope"]  -= 1
            st.session_state["battle_wrongs"] += 1
            st.error(f"✗ Wrong. Correct answer: {correct_key}")
            exp = q.get("explanation", "")
            if exp:
                st.caption(f"💡 {exp}")

        st.session_state["battle_q"]        = None
        st.session_state["battle_answered"] = True
        st.rerun()
