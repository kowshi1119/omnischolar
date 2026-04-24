"""
Creates high-quality CS education training data for OmniScholar.
Run locally then upload to Kaggle as dataset.
"""

import json
import os

CS_TOPICS = {
    "Data Structures": [
        {
            "instruction": "Explain binary search trees with a real example",
            "response": """A binary search tree (BST) is like a sorted filing cabinet.

**Definition:** A BST is a binary tree where every left child < parent < right child.

**How it works:**
Insert [5, 3, 7, 1, 4]:
```
        5
       / \\
      3   7
     / \\
    1   4
```

**Time complexity:** Search O(log n) average, O(n) worst case
**Space complexity:** O(n)

**Common exam trap:** BST search is O(n) worst case (not O(log n)) when tree is unbalanced — like inserting sorted data.

**Quick check:** What is the in-order traversal of this tree?
Answer: 1, 3, 4, 5, 7 (always sorted for BST)""",
        },
        {
            "instruction": "What is the difference between stack and queue?",
            "response": """Both are linear data structures but differ in access order.

**Stack — LIFO (Last In First Out)**
- Like a stack of plates — add/remove from top only
- Operations: push(), pop(), peek()
- Time: O(1) for all operations
- Use: function call stack, undo operations, expression evaluation

**Queue — FIFO (First In First Out)**
- Like a queue at a shop — add at back, remove from front
- Operations: enqueue(), dequeue(), front()
- Time: O(1) for all operations
- Use: BFS traversal, CPU scheduling, print spooler

**Exam trap:** Students confuse which end operations happen on.
Stack: BOTH push and pop happen at the SAME end (top).
Queue: enqueue at REAR, dequeue at FRONT.

**Memory trick:** Stack = LIFO like a pile. Queue = FIFO like a line.""",
        },
    ],
    "Operating Systems": [
        {
            "instruction": "Explain deadlock with the 4 necessary conditions",
            "response": """Deadlock occurs when processes are permanently blocked waiting for each other.

**Real analogy:** Two cars meeting on a narrow one-lane bridge. Neither can move forward or backward.

**Coffman's 4 Necessary Conditions (ALL must hold for deadlock):**

1. **Mutual Exclusion** — Only one process can use a resource at a time
2. **Hold and Wait** — A process holds resources while waiting for more
3. **No Preemption** — Resources cannot be forcibly taken from a process
4. **Circular Wait** — P1 waits for P2, P2 waits for P1 (circle)

**Prevention:** Eliminate ANY one condition.

**Detection example:**
Process A holds Resource 1, wants Resource 2
Process B holds Resource 2, wants Resource 1
→ Deadlock! Neither can proceed.

**Exam trap:** Students say 3 conditions. It is EXACTLY 4. All 4 must be present simultaneously.""",
        },
        {
            "instruction": "What is thrashing in operating systems?",
            "response": """Thrashing is when a computer spends more time swapping pages than executing processes.

**Definition:** Thrashing occurs when the working set of active processes exceeds available physical memory, causing excessive page faults.

**How it happens:**
1. System has many processes running
2. Each process needs more memory than available
3. OS constantly swaps pages in/out
4. CPU utilization drops near 0%
5. More processes added (CPU appears idle) → worse thrashing

**Graph:** CPU utilization increases with processes → peaks → suddenly collapses (thrashing point)

**Solutions:**
- Working Set Model: track pages used in last Δ time
- Page Fault Frequency: if too high → reduce processes
- Add more RAM

**Time complexity impact:** O(n) page faults instead of O(1) memory access

**Exam trap:** "Thrashing means CPU is overloaded." WRONG. CPU is actually UNDERUTILIZED during thrashing — it's waiting for I/O constantly.""",
        },
    ],
    "Algorithms": [
        {
            "instruction": "Trace through bubble sort with array [5, 3, 8, 1, 9]",
            "response": """Bubble sort repeatedly swaps adjacent elements if they are in wrong order.

**Algorithm:**
```python
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
```

**Trace with [5, 3, 8, 1, 9]:**

Pass 1: [5,3,8,1,9] → [3,5,8,1,9] → [3,5,8,1,9] → [3,5,1,8,9] → [3,5,1,8,9]
         ^swapped          ^no swap       ^swapped    ^no swap (9 bubbles up)

Pass 2: [3,5,1,8,9] → [3,5,1,8,9] → [3,1,5,8,9] → [3,1,5,8,9]
         ^no swap       ^swapped     ^no swap

Pass 3: [3,1,5,8,9] → [1,3,5,8,9] → [1,3,5,8,9]

Pass 4: [1,3,5,8,9] → no swaps → DONE

**Result: [1, 3, 5, 8, 9]**

**Time complexity:** O(n²) worst/average, O(n) best (already sorted)
**Space complexity:** O(1) in-place

**Exam trap:** Bubble sort is O(n) ONLY when array is already sorted AND early termination is implemented.""",
        },
    ],
    "OOP": [
        {
            "instruction": "Explain the 4 pillars of Object Oriented Programming",
            "response": """OOP has 4 fundamental principles that every exam tests.

**1. ENCAPSULATION**
Bundling data and methods together, hiding internal details.
```python
class BankAccount:
    def __init__(self):
        self.__balance = 0  # private

    def deposit(self, amount):  # public method
        self.__balance += amount
```
*Why:* Protects data from direct modification.

**2. INHERITANCE**
Child class inherits properties and methods from parent class.
```python
class Animal:
    def speak(self): pass

class Dog(Animal):
    def speak(self):
        return "Woof"
```
*Why:* Code reuse — write once, inherit many times.

**3. POLYMORPHISM**
Same interface, different behavior depending on object type.
```python
animals = [Dog(), Cat(), Bird()]
for a in animals:
    a.speak()  # Each calls its own speak()
```
*Why:* Flexible code that works with different object types.

**4. ABSTRACTION**
Hiding complexity, showing only essential features.
```python
from abc import ABC, abstractmethod
class Shape(ABC):
    @abstractmethod
    def area(self): pass
```
*Why:* Forces implementation of required methods.

**Exam trap:** Encapsulation ≠ Abstraction.
Encapsulation = HIDING DATA (private variables).
Abstraction = HIDING COMPLEXITY (abstract classes/interfaces).""",
        },
    ],
}

SINHALA_EXAMPLES = [
    {
        "instruction": "Binary search tree එක explain කරන්න සිංහලෙන්",
        "response": """Binary Search Tree (BST) යනු sorted data store කරන binary tree structure එකයි.

**Definition:** BST හි සෑම node එකක් සඳහාම:
- Left subtree: parent value ට වඩා SMALL values
- Right subtree: parent value ට වඩා LARGE values

**Example - Insert [5, 3, 7, 1, 4]:**
```
        5
       / \\
      3   7
     / \\
    1   4
```

**Time Complexity:**
- Search: O(log n) average case
- O(n) worst case (unbalanced tree)

**Space Complexity:** O(n)

**Common exam trap:** Sorted array insert කළොත් BST unbalanced වෙනවා → O(n) search time.

**Quick check:** In-order traversal ලබාදෙන result කුමක්ද?
Answer: 1, 3, 4, 5, 7 (always sorted for valid BST)""",
    },
    {
        "instruction": "Deadlock conditions 4ක් explain කරන්න",
        "response": """Deadlock යනු processes circular ලෙස resources wait කිරීමෙන් permanently blocked වීමයි.

**Real analogy:** Narrow bridge එකක දෙපස car 2ක් — neither can move!

**Coffman's 4 Necessary Conditions:**

1. **Mutual Exclusion (අන්‍යෝන්‍ය බැහැරවීම)**
   එකම resource එකක් single process ටම use කළ හැකිය

2. **Hold and Wait (ගෙන රැඳීම)**
   Process එකක් resources hold කරන ගමන් additional resources wait කරයි

3. **No Preemption (බලහත්කාරයෙන් ගැනීම නැත)**
   Process ට resources forcibly ගත නොහැකිය

4. **Circular Wait (කාරයිකා රෝකු)**
   P1 waits for P2, P2 waits for P1 — circle!

**Prevention:** ඕනෑම condition 1ක් eliminate කළ හැකිය.

**Exam trap:** Conditions 4 ALL present වෙනවිට ONLY deadlock occur වෙනවා — 3 conditions ලෙස ලිවීම wrong!""",
    },
]

TAMIL_EXAMPLES = [
    {
        "instruction": "Deadlock-ஐ Tamil-ல் விளக்கவும்",
        "response": """Deadlock என்பது processes ஒன்றை ஒன்று காத்திருந்து permanently blocked ஆகும் நிலை.

**உண்மை உதாரணம்:** இரண்டு கார்கள் ஒரு சிறிய பாலத்தில் எதிர் எதிரே வருகின்றன — யாரும் நகர முடியாது!

**Coffman's 4 தேவையான நிலைகள்:**

1. **Mutual Exclusion** — ஒரே resource-ஐ ஒரே நேரத்தில் ஒரு process மட்டுமே பயன்படுத்த முடியும்

2. **Hold and Wait** — ஒரு process resources வைத்திருந்தபடி மேலும் resources காக்கிறது

3. **No Preemption** — Resources-ஐ வலுக்கட்டாயமாக எடுக்க முடியாது

4. **Circular Wait** — P1 → P2 காக்கிறது, P2 → P1 காக்கிறது (வட்டம்)

**தடுப்பு முறை:** எந்த ஒரு condition-ஐயும் நீக்கினால் Deadlock தடுக்கலாம்.

**தேர்வு தவறு:** 3 conditions என எழுதுவது தவறு — சரியான விடை 4 conditions!""",
    },
]


def build_dataset() -> list:
    dataset = []

    for _, examples in CS_TOPICS.items():
        for ex in examples:
            dataset.append(
                {
                    "conversations": [
                        {"from": "human", "value": ex["instruction"]},
                        {"from": "gpt", "value": ex["response"]},
                    ]
                }
            )

    for ex in SINHALA_EXAMPLES:
        dataset.append(
            {
                "conversations": [
                    {"from": "human", "value": ex["instruction"]},
                    {"from": "gpt", "value": ex["response"]},
                ]
            }
        )

    for ex in TAMIL_EXAMPLES:
        dataset.append(
            {
                "conversations": [
                    {"from": "human", "value": ex["instruction"]},
                    {"from": "gpt", "value": ex["response"]},
                ]
            }
        )

    return dataset


def main() -> None:
    dataset = build_dataset()
    os.makedirs("data", exist_ok=True)
    out_path = os.path.join("data", "omnischolar_v2.jsonl")

    with open(out_path, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Created {len(dataset)} training examples")
    print("Upload data/omnischolar_v2.jsonl to Kaggle as a dataset")


if __name__ == "__main__":
    main()
