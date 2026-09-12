"""
Profile completion scoring for students.

Kept as a pure function (Student in, float out) rather than a stored/synced
column so there's no drift risk between the stored value and the actual
row contents -- it's cheap to compute on every read.
"""

# Each entry: (weight, predicate). Weights sum to 100.
_CHECKS = [
    (10, lambda s: bool(s.name)),
    (10, lambda s: bool(s.branch)),
    (5, lambda s: bool(s.cgpa and s.cgpa > 0)),
    (10, lambda s: bool(s.skills)),
    (10, lambda s: bool(s.projects)),
    (5, lambda s: bool(s.certifications)),
    (5, lambda s: bool(s.internship_history)),
    (5, lambda s: bool(s.hackathons)),
    (5, lambda s: bool(s.resume_url)),
    (5, lambda s: bool(s.profile_photo_url)),
    (5, lambda s: bool(s.github_url)),
    (5, lambda s: bool(s.linkedin_url)),
    (5, lambda s: bool(s.coding_profiles)),
    (5, lambda s: bool(s.preferred_roles)),
    (5, lambda s: bool(s.expected_salary)),
    (5, lambda s: bool(s.location_preference)),
]


def compute_profile_completion_pct(student) -> float:
    earned = sum(weight for weight, check in _CHECKS if check(student))
    return round(earned, 1)
