from src.extensions import db


class SensorThreshold(db.Model):
    __tablename__ = "sensor_threshold"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, nullable=False)
    week = db.Column(db.String(50), nullable=False)
    file = db.Column(db.String(50), nullable=False)
    sensor = db.Column(db.String(50), nullable=False)
    threshold_value = db.Column(db.Integer, nullable=False)
