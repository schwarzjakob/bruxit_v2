from . import db

class Patient(db.Model):
    __tablename__ = 'patient'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(80), unique=True, nullable=False)
    night_id = db.Column(db.String(50), unique=True, nullable=False)
    week = db.Column(db.String(50), unique=True, nullable=False)
    night_id = db.Column(db.String(50), unique=True, nullable=False)
    recorder = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'
    
class PatientData(db.Model):
    __tablename__ = 'patient_data'

    id = db.Column(db.Integer, primary_key=True)
    data_point= db.Column(db.Integer, unique=True, nullable=False)
    patient_id = db.Column(db.Integer, unique=True, nullable=False)
    week = db.Column(db.String(50), unique=True, nullable=False)
    night_id = db.Column(db.String(50), unique=True, nullable=False)
    recorder = db.Column(db.String(50), unique=True, nullable=False)

    mr = db.Column(db.Float, unique=True, nullable=False)
    ml = db.Column(db.Float, unique=True, nullable=False)
    ecg = db.Column(db.Float, unique=True, nullable=False)

    def __repr__(self):
        return f'<Patient {self.patient_id}>: <Night {self.night_id}>, <Week {self.week}>, <Recorder {self.recorder}>\n, <Data Point {self.data_point}>, <MR {self.mr}>, <ML {self.ml}>, <ECG {self.ecg}>'


    