from app import db
from datetime import datetime


class Student(db.Model):
    __tablename__ = 'students'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, unique=True)
    student_id    = db.Column(db.String(20), unique=True, nullable=False, index=True)
    full_name     = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), nullable=False)
    course        = db.Column(db.String(100), default='')
    year_level    = db.Column(db.Integer, default=1)

    # Academic metrics
    gpa           = db.Column(db.Float, default=1.0)          # Philippine scale 1.0–5.0
    attendance    = db.Column(db.Float, default=100.0)        # percentage 0–100
    failures      = db.Column(db.Integer, default=0)          # number of failed subjects
    trend         = db.Column(db.String(20), default='stable') # 'improving' | 'stable' | 'declining'

    # Subject scores (JSON string: {"Math":85,"English":90,...})
    subject_scores = db.Column(db.Text, default='{}')

    # Interests (comma-separated: "STEM,Arts,Business")
    interests      = db.Column(db.String(200), default='')

    # Computed / cached
    classification = db.Column(db.String(20), default='')     # 'Advanced'|'Average'|'At-Risk'

    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_subject_scores(self):
        import json
        try:
            return json.loads(self.subject_scores or '{}')
        except Exception:
            return {}

    def set_subject_scores(self, d: dict):
        import json
        self.subject_scores = json.dumps(d)

    def get_interests(self):
        if not self.interests:
            return []
        return [i.strip() for i in self.interests.split(',') if i.strip()]

    def set_interests(self, lst: list):
        self.interests = ','.join(lst)

    def gpa_to_percentage(self):
        """Approximate Philippine GPA → percentage for display."""
        table = {1.0: 99, 1.25: 96, 1.5: 93, 1.75: 90, 2.0: 87,
                 2.25: 84, 2.5: 81, 2.75: 78, 3.0: 75, 5.0: 65}
        # Find closest key
        closest = min(table.keys(), key=lambda k: abs(k - self.gpa))
        return table[closest]

    def __repr__(self):
        return f'<Student {self.student_id} {self.full_name}>'
