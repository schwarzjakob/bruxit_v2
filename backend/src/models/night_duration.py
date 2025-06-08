from src.extensions import db


class NightDuration(db.Model):
    __tablename__ = "night_duration"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, nullable=False)
    week = db.Column(db.String(50), nullable=False)
    file = db.Column(db.String(50), unique=True, nullable=False)
    seconds = db.Column(db.Float, nullable=False)
    duration = db.Column(db.Interval, nullable=False)
    # last_index = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Patient {self.patient_id}>: week {self.week}, file: {self.file}, seconds: {self.seconds}, duration: {self.duration}"
