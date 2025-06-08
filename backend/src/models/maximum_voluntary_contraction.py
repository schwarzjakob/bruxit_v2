from src.extensions import db


class MaximumVoluntaryContraction(db.Model):
    __tablename__ = "maximum_voluntary_contraction"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, nullable=False)
    week = db.Column(db.String(50), nullable=False)
    file = db.Column(db.String(50), nullable=False)
    sensor = db.Column(db.String(50), nullable=False)
    mvc = db.Column(db.Float, nullable=False)
