"""
algorithms/decision_tree.py
============================
Decision Tree – Student Academic Performance Classification

Classifies each student into one of three categories:
  • Advanced  – High GPA, good attendance, no failures, positive/stable trend
  • Average   – Mid-range GPA, some attendance issues, ≤1 failure
  • At-Risk   – Low GPA, poor attendance, multiple failures, declining trend

Philippine GPA Scale (lower = better):
  1.0 = Excellent (≈99%)   2.0 = Good (≈87%)
  3.0 = Passing  (≈75%)   5.0 = Fail (≈65%)

Time Complexity:  O(1) per student (fixed depth tree)
Space Complexity: O(1)
"""


def classify_student(gpa: float, attendance: float,
                      failures: int, trend: str) -> str:
    """
    Decision tree classification.

    Parameters
    ----------
    gpa        : float  – Philippine scale 1.0 (best) to 5.0 (fail)
    attendance : float  – Percentage 0–100
    failures   : int    – Number of failed subjects this term
    trend      : str    – 'improving' | 'stable' | 'declining'

    Returns
    -------
    str  – 'Advanced' | 'Average' | 'At-Risk'
    """
    # ── Node 1: Is GPA failing? ───────────────────────────────────────────────
    if gpa >= 3.0:
        # GPA is 3.0–5.0 (poor range)
        if failures >= 2:
            return 'At-Risk'
        if attendance < 75.0:
            return 'At-Risk'
        if trend == 'declining':
            return 'At-Risk'
        return 'Average'   # marginal pass — not yet at-risk

    # ── Node 2: GPA is 1.0–2.99 (passing to good) ────────────────────────────
    if gpa <= 1.75:
        # Excellent GPA range
        if attendance >= 90.0 and failures == 0:
            return 'Advanced'
        if attendance >= 80.0 and failures <= 1 and trend != 'declining':
            return 'Advanced'
        # Good GPA but attendance or trend drags them down
        return 'Average'

    # ── Node 3: GPA 1.76–2.99 (average range) ────────────────────────────────
    if failures >= 2:
        return 'At-Risk'
    if attendance < 75.0 and trend == 'declining':
        return 'At-Risk'
    if attendance < 75.0 or trend == 'declining':
        return 'Average'
    return 'Average'


def classify_all(students: list) -> list:
    """
    Classify a list of Student model objects in-place and return them.
    Updates the .classification attribute on each student.
    """
    for s in students:
        s.classification = classify_student(
            gpa=s.gpa,
            attendance=s.attendance,
            failures=s.failures,
            trend=s.trend,
        )
    return students


def get_classification_reasons(gpa: float, attendance: float,
                                failures: int, trend: str) -> list[str]:
    """Return human-readable reasons for the classification decision."""
    reasons = []
    if gpa >= 3.0:
        reasons.append(f'GPA of {gpa:.2f} is in the poor/failing range (≥3.0).')
    elif gpa <= 1.75:
        reasons.append(f'GPA of {gpa:.2f} is in the excellent range (≤1.75).')
    else:
        reasons.append(f'GPA of {gpa:.2f} is in the average range.')

    if attendance >= 90:
        reasons.append(f'Attendance of {attendance:.1f}% is excellent.')
    elif attendance >= 75:
        reasons.append(f'Attendance of {attendance:.1f}% is acceptable.')
    else:
        reasons.append(f'Attendance of {attendance:.1f}% is below the 75% threshold.')

    if failures == 0:
        reasons.append('No failed subjects this term.')
    elif failures == 1:
        reasons.append('1 failed subject this term.')
    else:
        reasons.append(f'{failures} failed subjects this term — high risk indicator.')

    trend_map = {'improving': 'improving ↑', 'stable': 'stable →', 'declining': 'declining ↓'}
    reasons.append(f'Academic trend is {trend_map.get(trend, trend)}.')
    return reasons
