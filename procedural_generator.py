import random
import math

def generate_procedural_math(tier=1):
    tier = max(1, min(3, int(tier)))
    problem_type = random.choice(["arithmetic", "algebra", "modular", "percentage", "powers"] if tier >= 2 else ["arithmetic", "percentage"])

    if problem_type == "arithmetic":
        if tier == 1:
            op = random.choice(["+", "-", "*"])
            if op == "+":
                a = random.randint(15, 99)
                b = random.randint(12, 89)
                ans = a + b
                q = str(a) + " + " + str(b) + " = ?"
            elif op == "-":
                a = random.randint(40, 150)
                b = random.randint(11, a - 5)
                ans = a - b
                q = str(a) + " - " + str(b) + " = ?"
            else:
                a = random.randint(6, 18)
                b = random.randint(4, 15)
                ans = a * b
                q = str(a) + " × " + str(b) + " = ?"
        elif tier == 2:
            a = random.randint(5, 15)
            b = random.randint(4, 12)
            c = random.randint(10, 50)
            ans = a * b + c
            q = "(" + str(a) + " × " + str(b) + ") + " + str(c) + " = ?"
        else:
            a = random.randint(13, 35)
            b = random.randint(12, 30)
            c = random.randint(25, 90)
            ans = a * b - c
            q = "(" + str(a) + " × " + str(b) + ") - " + str(c) + " = ?"

        exp = "Calculated directly: " + q.replace(" = ?", "") + " = " + str(ans) + "."

    elif problem_type == "algebra":
        x_val = random.randint(2, 16)
        a = random.randint(2, 9)
        b = random.randint(3, 35) * random.choice([1, -1])
        c = a * x_val + b
        sign_str = ("+ " + str(b)) if b > 0 else ("- " + str(abs(b)))
        q = "Solve for x:  " + str(a) + "x " + sign_str + " = " + str(c)
        ans = x_val
        exp = "Subtract " + str(b) + " from both sides: " + str(a) + "x = " + str(c - b) + ". Divide by " + str(a) + ": x = " + str(ans) + "."

    elif problem_type == "modular":
        m = random.randint(5, 13)
        mult = random.randint(3, 15)
        rem = random.randint(1, m - 1)
        val = m * mult + rem
        q = "Evaluate:  " + str(val) + " mod " + str(m) + " = ?"
        ans = rem
        exp = str(val) + " = (" + str(mult) + " × " + str(m) + ") + " + str(rem) + ". Remainder is " + str(rem) + "."

    elif problem_type == "percentage":
        pct = random.choice([10, 15, 20, 25, 30, 40, 50, 75])
        base = random.randint(4, 40) * (100 // math.gcd(100, pct))
        ans = int(base * (pct / 100.0))
        q = "What is " + str(pct) + "% of " + str(base) + "?"
        exp = str(pct) + "% of " + str(base) + " = " + str(ans) + "."

    else:
        base = random.choice([2, 3, 4, 5, 10])
        p = 3 if base > 3 else random.choice([3, 4, 5, 6])
        ans = base ** p
        q = "Evaluate:  " + str(base) + "^" + str(p) + " = ?"
        exp = str(base) + "^" + str(p) + " = " + str(ans) + "."

    distractors = set()
    for off in [-1, 1, -2, 2, -10, 10, -5, 5, -3, 3]:
        cand = ans + off
        if cand != ans and cand > 0:
            distractors.add(cand)
        if len(distractors) == 3:
            break
    while len(distractors) < 3:
        cand = ans + random.randint(4, 20) * random.choice([1, -1])
        if cand != ans and cand > 0:
            distractors.add(cand)

    options = [ans] + list(distractors)
    random.shuffle(options)
    correct_idx = options.index(ans)

    return {
        "question": q,
        "options": [str(o) for o in options],
        "ans": correct_idx,
        "correct_val": str(ans),
        "explanation": exp,
        "category": "Quantitative Agility (Procedural)",
        "tier": tier
    }

def generate_procedural_code(tier=1):
    templates = [
        {
            "lang": "python",
            "snippet": "def get_last_item(items):\n    return items[len(items)]",
            "q": "What error occurs when calling get_last_item([10, 20, 30])?",
            "options": [
                "IndexError: list index out of range",
                "TypeError: unhashable type",
                "ValueError: empty sequence",
                "Returns 30 without error"
            ],
            "ans": 0,
            "exp": "Lists are 0-indexed in Python. For length 3, valid indices are 0, 1, 2. Accessing items[3] raises IndexError."
        },
        {
            "lang": "python",
            "snippet": "def append_item(val, target=[]):\n    target.append(val)\n    return target\n\nprint(append_item(1))\nprint(append_item(2))",
            "q": "What will the second print statement output?",
            "options": [
                "[1, 2]",
                "[2]",
                "[[1], 2]",
                "TypeError: default argument error"
            ],
            "ans": 0,
            "exp": "Default list arguments are created once when the function is defined, causing state to persist between calls."
        },
        {
            "lang": "javascript",
            "snippet": "const arr = [10, 20, 30];\nfor (var i = 0; i <= arr.length; i++) {\n    console.log(arr[i]);\n}",
            "q": "What is logged on the final iteration of the loop?",
            "options": [
                "undefined",
                "30",
                "ReferenceError: out of bounds",
                "null"
            ],
            "ans": 0,
            "exp": "The loop condition i <= arr.length executes for i = 3. Since arr[3] does not exist, it prints undefined."
        },
        {
            "lang": "python",
            "snippet": "count = 0\nfor x in range(1, 5):\n    if x % 2 == 0:\n        count += x\nprint(count)",
            "q": "What is the value printed by this code?",
            "options": [
                "6",
                "10",
                "4",
                "2"
            ],
            "ans": 0,
            "exp": "range(1, 5) produces 1, 2, 3, 4. Even numbers are 2 and 4. Sum = 2 + 4 = 6."
        },
        {
            "lang": "javascript",
            "snippet": "const a = \"42\";\nconst b = 8;\nconsole.log(a + b);",
            "q": "What is logged to the console?",
            "options": [
                "\"428\"",
                "50",
                "NaN",
                "TypeError"
            ],
            "ans": 0,
            "exp": "In JavaScript, the + operator concatenates when one operand is a string. \"42\" + 8 produces \"428\"."
        },
        {
            "lang": "python",
            "snippet": "numbers = [5, 2, 8, 1, 9]\nnumbers.sort()\nresult = numbers.reverse()",
            "q": "What is the value of variable result?",
            "options": [
                "None",
                "[9, 8, 5, 2, 1]",
                "[1, 2, 5, 8, 9]",
                "AttributeError"
            ],
            "ans": 0,
            "exp": "In Python, list.reverse() modifies the list in place and returns None."
        },
        {
            "lang": "python",
            "snippet": "def calculate_average(nums):\n    total = sum(nums)\n    return total / len(nums)",
            "q": "What edge case causes this function to crash?",
            "options": [
                "Calling with an empty list: calculate_average([])",
                "Calling with negative numbers",
                "Calling with floating point numbers",
                "Calling with a single element list"
            ],
            "ans": 0,
            "exp": "If nums is empty, len(nums) is 0, raising ZeroDivisionError."
        }
    ]

    item = random.choice(templates)
    return {
        "question": item["q"],
        "snippet": item["snippet"],
        "lang": item["lang"],
        "options": item["options"],
        "ans": item["ans"],
        "correct_val": item["options"][item["ans"]],
        "explanation": item["exp"],
        "category": "Algorithmic Logic (Procedural)",
        "tier": tier
    }

def generate_procedural_pattern(tier=1):
    rule = random.choice(["arithmetic_seq", "geometric_seq", "fibonacci_shift", "square_seq", "grid_sum"])

    if rule == "arithmetic_seq":
        start = random.randint(3, 20)
        diff = random.randint(3, 12)
        seq = [start + i * diff for i in range(5)]
        ans = seq[-1]
        display_seq = [str(s) for s in seq[:-1]] + ["?"]
        q = "Identify the missing number: " + ", ".join(display_seq)
        exp = "Arithmetic sequence with common difference +" + str(diff) + ". Next term is " + str(seq[-2]) + " + " + str(diff) + " = " + str(ans) + "."

    elif rule == "geometric_seq":
        ratio = random.choice([2, 3])
        start = random.randint(2, 6)
        seq = [start * (ratio ** i) for i in range(5)]
        ans = seq[-1]
        display_seq = [str(s) for s in seq[:-1]] + ["?"]
        q = "Identify the missing number: " + ", ".join(display_seq)
        exp = "Geometric progression multiplying by ×" + str(ratio) + ". Next term is " + str(seq[-2]) + " × " + str(ratio) + " = " + str(ans) + "."

    elif rule == "square_seq":
        offset = random.randint(1, 5)
        seq = [(i + offset) ** 2 for i in range(5)]
        ans = seq[-1]
        display_seq = [str(s) for s in seq[:-1]] + ["?"]
        q = "Identify the missing square: " + ", ".join(display_seq)
        exp = "Sequence of perfect squares (" + str(offset) + "², " + str(offset+1) + "², ...). Missing term is " + str(offset+4) + "² = " + str(ans) + "."

    elif rule == "fibonacci_shift":
        a, b = random.randint(2, 6), random.randint(3, 7)
        seq = [a, b]
        for _ in range(4):
            seq.append(seq[-1] + seq[-2])
        ans = seq[-1]
        display_seq = [str(s) for s in seq[:-1]] + ["?"]
        q = "Identify the Fibonacci sequence term: " + ", ".join(display_seq)
        exp = "Each term is the sum of the preceding two terms. " + str(seq[-3]) + " + " + str(seq[-2]) + " = " + str(ans) + "."

    else:
        target = random.randint(25, 60)
        r1_a = random.randint(5, target - 10)
        r1_b = target - r1_a
        r2_a = random.randint(4, target - 8)
        ans = target - r2_a
        q = "Row sums are constant: [ " + str(r1_a) + " , " + str(r1_b) + " ] and [ " + str(r2_a) + " , ? ]. Find ?"
        exp = "Row 1 sum = " + str(r1_a) + " + " + str(r1_b) + " = " + str(target) + ". Therefore Row 2 sum must equal " + str(target) + ": " + str(target) + " - " + str(r2_a) + " = " + str(ans) + "."

    distractors = set()
    for off in [-2, 2, -1, 1, -4, 4, -10, 10]:
        cand = ans + off
        if cand != ans and cand > 0:
            distractors.add(cand)
        if len(distractors) == 3:
            break
    while len(distractors) < 3:
        cand = ans + random.randint(3, 15) * random.choice([1, -1])
        if cand != ans and cand > 0:
            distractors.add(cand)

    options = [ans] + list(distractors)
    random.shuffle(options)
    correct_idx = options.index(ans)

    return {
        "question": q,
        "options": [str(o) for o in options],
        "ans": correct_idx,
        "correct_val": str(ans),
        "explanation": exp,
        "category": "Inductive Logic (Procedural)",
        "tier": tier
    }
