#!/usr/bin/env python3
"""
Lumina Cognitive Talent Discovery Engine
Synthesizes student game performance into standardized cognitive domains:
1. Motor Cadence & Processing Speed (Typing WPM, consistency, reaction baseline)
2. Quantitative Agility (Mental arithmetic, accuracy under time pressure)
3. Working Memory & Sequence Span (Pattern recall, sequence length)
4. Perceptual Reflexes (Reaction latency in milliseconds)
5. Inductive Logic & Spatial Reasoning (Pattern matching, visual logic)
6. Strategic Foresight & Game Theory (Chess & Checkers ELO, win ratios)
7. Verbal Processing & Lexical Fluency (Word Blitz vocabulary volume, typing accuracy)
"""
import math
import hashlib
from datetime import datetime
from db import db_fetchone, db_fetchall

COGNITIVE_ARCHETYPES = {
    "algorithmic_architect": {
        "title": "Algorithmic Architect",
        "badge": "⚡",
        "tagline": "Exceptional mathematical agility, inductive logic, and structured problem-solving.",
        "domains": ["Quantitative Agility", "Inductive Logic", "Strategic Foresight"],
        "careers": [
            {"field": "Distributed Systems & Algorithms", "majors": "EECS / Computer Science", "sample_role": "High-Performance Systems Architect"},
            {"field": "Machine Learning & Neural Architecture", "majors": "Artificial Intelligence / Applied Math", "sample_role": "Foundational Model Researcher"},
            {"field": "Quantitative Finance & Trading Systems", "majors": "Mathematical Finance / Statistics", "sample_role": "Algorithmic Quantitative Strategist"}
        ]
    },
    "strategic_grandmaster": {
        "title": "Strategic Grandmaster",
        "badge": "♟️",
        "tagline": "Deep forward planning, positional evaluation, and complex working memory.",
        "domains": ["Strategic Foresight", "Working Memory", "Inductive Logic"],
        "careers": [
            {"field": "Autonomous Robotics & Control", "majors": "Robotics / Mechanical Engineering", "sample_role": "Autonomous Navigation Architect"},
            {"field": "Game Theory & Economics", "majors": "Economics & Computation", "sample_role": "Mechanism Design & Policy Strategist"},
            {"field": "Cybersecurity & Threat Defense", "majors": "Cybersecurity / Information Assurance", "sample_role": "Red-Team Systems Strategist"}
        ]
    },
    "rapid_response_operator": {
        "title": "Rapid Response Operator",
        "badge": "🎯",
        "tagline": "Sub-200ms perceptual latency, hyper-fast motor cadence, and high accuracy under pressure.",
        "domains": ["Perceptual Reflexes", "Processing Speed", "Quantitative Agility"],
        "careers": [
            {"field": "Real-Time Critical Infrastructure", "majors": "Aerospace / Computer Engineering", "sample_role": "Flight Avionics Operations Engineer"},
            {"field": "High-Frequency Tech Operations", "majors": "Network Systems / Cloud Infrastructure", "sample_role": "Site Reliability Operations Commander"},
            {"field": "Esports & Human-Machine Interfaces", "majors": "Human-Computer Interaction (HCI)", "sample_role": "Next-Gen Interface Systems Designer"}
        ]
    },
    "lexical_polymath": {
        "title": "Lexical Polymath",
        "badge": "📚",
        "tagline": "High verbal retrieval velocity, vocabulary breadth, and typing precision.",
        "domains": ["Verbal Processing", "Processing Speed", "Working Memory"],
        "careers": [
            {"field": "Computational Linguistics & NLP", "majors": "Linguistics & Computer Science", "sample_role": "Large Language Model Prompt & Evaluator"},
            {"field": "Technical Communications & Law", "majors": "Science, Technology & Society (STS)", "sample_role": "Tech Patent Strategist & Policy Lead"},
            {"field": "Bioinformatics & Genomic Sequences", "majors": "Computational Biology", "sample_role": "Genomic Sequence Analyst"}
        ]
    },
    "computational_polymath": {
        "title": "Computational Polymath",
        "badge": "🌟",
        "tagline": "Balanced excellence across quantitative, spatial, strategic, and motor disciplines.",
        "domains": ["All Cognitive Domains"],
        "careers": [
            {"field": "Advanced Systems Engineering", "majors": "EECS / Physics", "sample_role": "Principal Systems Architect"},
            {"field": "Cognitive Neuroscience & AI", "majors": "Brain & Cognitive Sciences (Course 9)", "sample_role": "Neural-Interface Computational Scientist"},
            {"field": "Space Systems Engineering", "majors": "Aeronautics & Astronautics (Course 16)", "sample_role": "Interplanetary Mission Systems Engineer"}
        ]
    },
    "emerging_scholar": {
        "title": "Emerging Talent",
        "badge": "🌱",
        "tagline": "Active exploration phase with rapidly developing cognitive baseline.",
        "domains": ["Foundational Growth"],
        "careers": [
            {"field": "STEM Explorations", "majors": "General Engineering / Applied Sciences", "sample_role": "Research Lab Junior Fellow"},
            {"field": "Software Engineering Fundamentals", "majors": "Computer Science", "sample_role": "Junior Software Engineer"}
        ]
    }
}

def _clamp(val, low=0.0, high=100.0):
    return max(low, min(high, float(val)))

def _percentile_approx(score_0_to_100):
    """Sigmoid-based percentile approximation centered around 50."""
    if score_0_to_100 <= 0:
        return 5.0
    x = (score_0_to_100 - 50.0) / 18.0
    sig = 1.0 / (1.0 + math.exp(-x))
    return round(_clamp(sig * 100.0, 1.0, 99.9), 1)

def compute_cognitive_profile(user_id):
    """
    Synthesizes all games and drills into a standardized cognitive profile.
    Returns a dict with domains, percentile scores, LTI, archetype, career paths, and adaptive drills.
    """
    user_row = db_fetchone("SELECT id, username, fullname, level, xp, streak, created_at FROM users WHERE id=?", (user_id,))
    if not user_row:
        return None

    # 1. Processing Speed & Motor Cadence (Typing)
    scores = db_fetchall("SELECT wpm, accuracy, net_wpm FROM scores WHERE user_id=? ORDER BY created_at DESC LIMIT 50", (user_id,))
    if scores:
        best_wpm = max(s[0] or 0 for s in scores)
        avg_wpm = sum(s[0] or 0 for s in scores) / len(scores)
        best_net = max(s[2] or s[0] or 0 for s in scores)
        avg_acc = sum(s[1] or 100 for s in scores) / len(scores)
        # Scaled: 100 WPM = 85 pts, 130 WPM = 100 pts
        motor_speed_raw = (best_wpm * 0.45 + avg_wpm * 0.25 + best_net * 0.30)
        motor_score = _clamp((motor_speed_raw / 120.0) * 100.0)
        precision_score = _clamp(avg_acc)
    else:
        best_wpm, avg_wpm, best_net, avg_acc = 0, 0, 0, 100
        motor_score, precision_score = 15.0, 50.0

    # 2. Quantitative Agility (Math Sprint)
    math_rows = db_fetchall("SELECT score, correct, total FROM math_sprints WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (user_id,))
    if math_rows:
        math_best = max(m[0] or 0 for m in math_rows)
        math_avg = sum(m[0] or 0 for m in math_rows) / len(math_rows)
        # Score 120+ in 60s math sprint is exceptional
        quantitative_score = _clamp((math_best * 0.65 + math_avg * 0.35) / 1.2)
    else:
        math_best, quantitative_score = 0, 20.0

    # 3. Working Memory & Sequence Span (Memory Palace)
    mem_rows = db_fetchall("SELECT level_reached, max_pattern_length FROM memory_tests WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (user_id,))
    if mem_rows:
        mem_best_lvl = max(m[0] or 0 for m in mem_rows)
        mem_best_len = max(m[1] or 0 for m in mem_rows)
        memory_score = _clamp((mem_best_lvl * 5.0 + mem_best_len * 3.5))
    else:
        mem_best_lvl, memory_score = 0, 20.0

    # 4. Perceptual Reflexes (Reaction Test)
    react_rows = db_fetchall("SELECT best_ms, avg_ms FROM reaction_tests WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (user_id,))
    if react_rows:
        react_best = min(r[0] or 999 for r in react_rows if r[0])
        if react_best < 50:
            react_best = 180
        reflex_score = _clamp(100.0 - ((react_best - 150.0) / 2.8))
    else:
        react_best, reflex_score = 350, 25.0

    # 5. Inductive Logic & Pattern Recognition (Pattern Tests)
    pattern_rows = db_fetchall("SELECT puzzles_solved, avg_time_ms FROM pattern_tests WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (user_id,))
    if pattern_rows:
        pattern_best = max(p[0] or 0 for p in pattern_rows)
        pattern_score = _clamp(pattern_best * 10.0)
    else:
        pattern_best, pattern_score = 0, 20.0

    # 6. Strategic Foresight & Game Theory (Chess & Checkers)
    chess_rating = db_fetchone("SELECT rating, games_played FROM user_ratings WHERE user_id=? AND game_type='chess'", (user_id,))
    checkers_rating = db_fetchone("SELECT rating, games_played FROM user_ratings WHERE user_id=? AND game_type='checkers'", (user_id,))
    c_rat = chess_rating[0] if chess_rating else 1200
    chk_rat = checkers_rating[0] if checkers_rating else 1200
    strat_val = max(c_rat, chk_rat)
    strategic_score = _clamp(((strat_val - 800.0) / 1200.0) * 100.0)

    # 7. Verbal Processing & Lexical Fluency (Word Blitz)
    word_rows = db_fetchall("SELECT score FROM word_blitz_scores WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (user_id,))
    if word_rows:
        word_best = max(w[0] or 0 for w in word_rows)
        verbal_score = _clamp((word_best / 30.0) * 80.0 + (precision_score * 0.2))
    else:
        word_best, verbal_score = 0, 25.0

    domains = [
        {
            "id": "motor",
            "name": "Processing Speed & Cadence",
            "score": round(motor_score, 1),
            "percentile": _percentile_approx(motor_score),
            "metric_label": f"{round(best_wpm, 1)} WPM Best",
            "icon": "⚡"
        },
        {
            "id": "quantitative",
            "name": "Quantitative Agility",
            "score": round(quantitative_score, 1),
            "percentile": _percentile_approx(quantitative_score),
            "metric_label": f"{math_best} pts (Math Sprint)",
            "icon": "➗"
        },
        {
            "id": "memory",
            "name": "Working Memory Span",
            "score": round(memory_score, 1),
            "percentile": _percentile_approx(memory_score),
            "metric_label": f"Lvl {mem_best_lvl} Sequence",
            "icon": "🧠"
        },
        {
            "id": "reflexes",
            "name": "Perceptual Reflexes",
            "score": round(reflex_score, 1),
            "percentile": _percentile_approx(reflex_score),
            "metric_label": f"{react_best}ms Latency",
            "icon": "🎯"
        },
        {
            "id": "inductive",
            "name": "Inductive Pattern Logic",
            "score": round(pattern_score, 1),
            "percentile": _percentile_approx(pattern_score),
            "metric_label": f"{pattern_best} Puzzles Solved",
            "icon": "🧩"
        },
        {
            "id": "strategic",
            "name": "Strategic Foresight",
            "score": round(strategic_score, 1),
            "percentile": _percentile_approx(strategic_score),
            "metric_label": f"{strat_val} Peak ELO",
            "icon": "♟️"
        },
        {
            "id": "verbal",
            "name": "Lexical Processing",
            "score": round(verbal_score, 1),
            "percentile": _percentile_approx(verbal_score),
            "metric_label": f"{word_best} Word Blitz",
            "icon": "📖"
        }
    ]

    avg_domain_score = sum(d["score"] for d in domains) / len(domains)
    lti = int(round(200.0 + (avg_domain_score / 100.0) * 800.0))
    overall_percentile = _percentile_approx(avg_domain_score)

    top_domains = sorted(domains, key=lambda x: x["score"], reverse=True)
    top1 = top_domains[0]
    top2 = top_domains[1]

    high_count = sum(1 for d in domains if d["score"] >= 65.0)
    if high_count >= 4:
        archetype_key = "computational_polymath"
    elif top1["id"] in ("quantitative", "inductive") and top2["id"] in ("quantitative", "inductive", "strategic"):
        archetype_key = "algorithmic_architect"
    elif top1["id"] in ("strategic", "memory") and top2["id"] in ("strategic", "memory", "inductive"):
        archetype_key = "strategic_grandmaster"
    elif top1["id"] in ("reflexes", "motor"):
        archetype_key = "rapid_response_operator"
    elif top1["id"] in ("verbal", "motor") and verbal_score >= 50:
        archetype_key = "lexical_polymath"
    elif avg_domain_score < 35:
        archetype_key = "emerging_scholar"
    else:
        archetype_key = "algorithmic_architect"

    archetype_info = COGNITIVE_ARCHETYPES[archetype_key]

    lowest_domain = sorted(domains, key=lambda x: x["score"])[0]
    adaptive_drills = []
    if lowest_domain["id"] == "quantitative":
        adaptive_drills.append({
            "title": "Rapid Mental Arithmetic Sprint",
            "reason": f"Quantitative agility is currently at {lowest_domain['percentile']}th percentile.",
            "prescription": "Play 3 sessions of Math Sprint daily (60s speed drills) to improve automatic number retrieval.",
            "action_url": "/games/math",
            "action_label": "Start Math Sprint"
        })
    elif lowest_domain["id"] == "reflexes":
        adaptive_drills.append({
            "title": "Visual Stimulus Reaction Drills",
            "reason": f"Reaction latency averages {react_best}ms ({lowest_domain['percentile']}th percentile).",
            "prescription": "Perform 5 reaction test rounds before typing races to calibrate neural alertness.",
            "action_url": "/games/reaction",
            "action_label": "Test Reflexes"
        })
    elif lowest_domain["id"] == "memory":
        adaptive_drills.append({
            "title": "Sequence Expansion in Memory Palace",
            "reason": f"Working memory span is currently at {lowest_domain['percentile']}th percentile.",
            "prescription": f"Push past Level {mem_best_lvl} by chunking colors/patterns into pairs of two.",
            "action_url": "/games/memory",
            "action_label": "Enter Memory Palace"
        })
    elif lowest_domain["id"] == "strategic":
        adaptive_drills.append({
            "title": "Tactical Endgame Practice in Chess Arena",
            "reason": f"Strategic ELO is currently {strat_val}.",
            "prescription": "Play 2 rated matches against the Grandmaster Bot to develop positional depth.",
            "action_url": "/competitions",
            "action_label": "Challenge Chess Arena"
        })
    elif lowest_domain["id"] == "inductive":
        adaptive_drills.append({
            "title": "Visual Pattern Induction",
            "reason": f"Pattern logic solved count is {pattern_best}.",
            "prescription": "Solve 5 pattern matrices to train rule identification and abstract matrix deduction.",
            "action_url": "/games/pattern",
            "action_label": "Solve Patterns"
        })
    else:
        adaptive_drills.append({
            "title": "Cadence & Precision Typing Drills",
            "reason": f"Motor cadence is currently at {round(best_wpm, 1)} WPM.",
            "prescription": "Practice Code & Science passages to eliminate error spikes on symbols and syntax.",
            "action_url": "/typing?category=code",
            "action_label": "Practice Code Typing"
        })

    # Keyboard Heatmap Weakness Drill
    kb_rows = db_fetchall("SELECT error_map FROM scores WHERE user_id=? AND error_map IS NOT NULL ORDER BY created_at DESC LIMIT 20", (user_id,))
    kb_errors = {}
    for r in kb_rows:
        try:
            em = __import__("json").loads(r[0])
            for k, v in em.items():
                kb_errors[k] = kb_errors.get(k, 0) + v
        except Exception:
            pass
    if kb_errors:
        worst_keys = sorted(kb_errors.items(), key=lambda x: x[1], reverse=True)[:3]
        key_list_str = ", ".join(f"'{k}' ({cnt} miss)" for k, cnt in worst_keys)
        adaptive_drills.append({
            "title": "Targeted Finger Stroke Remediation",
            "reason": f"High error frequency detected on keycaps: {key_list_str}.",
            "prescription": "Focus on deliberate finger placement and rhythm rather than raw burst speed.",
            "action_url": "/analytics",
            "action_label": "View Error Heatmap"
        })

    raw_hash_data = f"{user_id}:{user_row[1]}:{lti}:{overall_percentile}:{datetime.utcnow().strftime('%Y-%m-%d')}"
    dossier_hash = hashlib.sha256(raw_hash_data.encode()).hexdigest()[:16].upper()

    return {
        "user_id": user_id,
        "username": user_row[1],
        "fullname": user_row[2],
        "level": user_row[3] or 1,
        "xp": user_row[4] or 0,
        "streak": user_row[5] or 0,
        "member_since": user_row[6],
        "lti": lti,
        "overall_percentile": overall_percentile,
        "domains": domains,
        "radar_labels": [d["name"].split("&")[0].strip() for d in domains],
        "radar_values": [d["score"] for d in domains],
        "archetype": archetype_info,
        "top_strengths": top_domains[:3],
        "adaptive_drills": adaptive_drills,
        "dossier_hash": dossier_hash,
        "generated_date": datetime.utcnow().strftime("%B %d, %Y")
    }
