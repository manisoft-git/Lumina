#!/usr/bin/env python3
"""
Lumina Anti-Cheat & Keystroke Biometrics Engine
Verifies human typing dynamics, inter-keystroke intervals (IKI),
entropy variance, and input velocity to protect competitive integrity.
"""
import math

class AntiCheatEngine:
    # Physical human biomechanical limits
    MAX_HUMAN_WPM = 260.0
    MIN_FLIGHT_TIME_MS = 12.0  # Biomechanical lower bound for independent finger motions
    MIN_IKI_STD_DEV_MS = 8.0   # True human typing has natural neuromuscular jitter

    @classmethod
    def verify_submission(cls, wpm, accuracy, duration_sec, keystrokes=None, timings=None, passage_len=0):
        """
        Evaluates the integrity of a typing submission.
        Returns: {
            'verified': bool,
            'integrity_score': float (0.0 to 1.0),
            'flags': list of strings,
            'reason': str
        }
        """
        flags = []
        confidence = 1.0

        # Check 1: Absolute WPM threshold
        if wpm > cls.MAX_HUMAN_WPM:
            flags.append(f"Improbable WPM: {wpm} exceeds human physiological threshold ({cls.MAX_HUMAN_WPM})")
            confidence -= 0.85

        # Check 2: Accuracy vs speed sanity
        if wpm > 180 and accuracy < 50:
            flags.append("Erratic high-speed spamming detected")
            confidence -= 0.40

        # Check 3: Duration vs typed volume physical check
        if duration_sec is not None and duration_sec > 0 and passage_len > 0:
            expected_cpm = (passage_len / duration_sec) * 60.0
            expected_wpm = expected_cpm / 5.0
            # Allow +-30% tolerance for countdown and network latency
            if wpm > expected_wpm * 2.5 and expected_wpm > 10:
                flags.append("Time-elapsed to word-volume physical mismatch")
                confidence -= 0.50

        # Check 4: Biometric Keystroke Timings Analysis (if client sent per-key timestamps)
        # timings format: list of relative ms offsets e.g. [45, 110, 192, 280, ...]
        if timings and len(timings) >= 10:
            intervals = []
            for i in range(1, len(timings)):
                dt = timings[i] - timings[i-1]
                if dt >= 0:
                    intervals.append(dt)

            if intervals:
                avg_iki = sum(intervals) / len(intervals)
                variance = sum((x - avg_iki) ** 2 for x in intervals) / len(intervals)
                std_dev = math.sqrt(variance)

                # 4a: Macro/Autoclicker detection (fixed interval delay, e.g. setInterval(f, 40))
                if std_dev < cls.MIN_IKI_STD_DEV_MS and len(intervals) > 20:
                    flags.append(f"Synthetic interval uniformity detected (std dev {std_dev:.1f}ms < {cls.MIN_IKI_STD_DEV_MS}ms)")
                    confidence -= 0.70

                # 4b: Bulk paste / script injection (< 10ms bulk dumping)
                micro_intervals = sum(1 for x in intervals if x < cls.MIN_FLIGHT_TIME_MS)
                micro_ratio = micro_intervals / len(intervals)
                if micro_ratio > 0.15:
                    flags.append(f"Unnatural burst clustering ({micro_ratio*100:.1f}% intervals < {cls.MIN_FLIGHT_TIME_MS}ms)")
                    confidence -= 0.75

        confidence = max(0.0, min(1.0, round(confidence, 2)))
        verified = (confidence >= 0.60) and (wpm <= cls.MAX_HUMAN_WPM)

        reason = "Biometrics verified" if verified else ("; ".join(flags) if flags else "Failed integrity threshold")

        return {
            "verified": verified,
            "integrity_score": confidence,
            "flags": flags,
            "reason": reason
        }
