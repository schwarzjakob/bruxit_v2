from src.extensions import db


class SleepStageSegment(db.Model):
    __tablename__ = "sleep_stage_segment"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, nullable=False)
    week = db.Column(db.String(50), nullable=False)
    file = db.Column(db.String(50), nullable=False)
    x = db.Column(db.Integer, nullable=False)
    y = db.Column(db.Integer, nullable=False)
    HRV_LFHF = db.Column(db.Float, nullable=False)
    HRV_SDNN = db.Column(db.Float, nullable=False)
    stage = db.Column(db.String(50), nullable=False)
