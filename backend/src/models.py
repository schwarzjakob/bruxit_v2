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
    
"""    
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
"""    


class NightDuration(db.Model):
    __tablename__ = 'night_duration'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, nullable=False)
    week = db.Column(db.String(50), nullable=False)
    file = db.Column(db.String(50), unique=True, nullable=False)
    seconds = db.Column(db.Float, nullable=False)
    duration = db.Column(db.Interval, nullable = False)
    #last_index = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Patient {self.patient_id}>: week {self.week}, file: {self.file}, seconds: {self.seconds}, duration: {self.duration}'


class SSD(db.Model):
    __tablename__ = 'ssd'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, nullable=False)
    week = db.Column(db.String(50), nullable=False)
    file = db.Column(db.String(50), nullable=False)
    x = db.Column(db.Integer, nullable=False)
    y = db.Column(db.Integer, nullable=False)
    HRV_LFHF = db.Column(db.Float, nullable=False)
    HRV_SDNN = db.Column(db.Float, nullable=False)
    stage = db.Column(db.String(50), nullable=False)
    selected = db.Column(db.Boolean, unique=False, default=False)


class MVC(db.Model):
    __tablename__ = 'mvc'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, nullable=False)
    week = db.Column(db.String(50), nullable=False)
    file = db.Column(db.String(50), nullable=False)
    sensor = db.Column(db.String(50), nullable=False)
    mvc = db.Column(db.Float, nullable=False)

"""
class Feautres(db.Model):
    __tablename__ = 'features'
    start_time = db.Column(db.Float, nullable=False)
    end_time  = db.Column(db.Float, nullable=False)
    std_mr  = db.Column(db.Float, nullable=True)
    std_ml = db.Column(db.Float, nullable=True)
    var_mr  = db.Column(db.Float, nullable=True)
    var_ml  = db.Column(db.Float, nullable=True)
    rms_mr  = db.Column(db.Float, nullable=True)
    rms_ml = db.Column(db.Float, nullable=True)
    mav_mr = db.Column(db.Float, nullable=True)
    mav_ml = db.Column(db.Float, nullable=True)
    log_det_mr = db.Column(db.Float, nullable=True)
    log_det_ml = db.Column(db.Float, nullable=True)
    wl_mr = db.Column(db.Float, nullable=True)
    wl_ml = db.Column(db.Float, nullable=True)
    aac_mr = db.Column(db.Float, nullable=True)
    aac_ml  = db.Column(db.Float, nullable=True)
    dasdv_mr = db.Column(db.Float, nullable=True)
    dasdv_ml = db.Column(db.Float, nullable=True)
    zc_mr = db.Column(db.Float, nullable=True)
    zc_ml = db.Column(db.Float, nullable=True)
    wamp_mr = db.Column(db.Float, nullable=True)
    wamp_ml = db.Column(db.Float, nullable=True)
    fr_mr = db.Column(db.Float, nullable=True)
    fr_ml = db.Column(db.Float, nullable=True)
    mnp_mr = db.Column(db.Float, nullable=True) 
    mnp_ml = db.Column(db.Float, nullable=True)
    tot_mr = db.Column(db.Float, nullable=True)
    tot_ml = db.Column(db.Float, nullable=True)
    mnf_mr = db.Column(db.Float, nullable=True)
    mnf_ml = db.Column(db.Float, nullable=True)
    mdf_mr = db.Column(db.Float, nullable=True)
    mdf_ml = db.Column(db.Float, nullable=True)
    pkf_mr = db.Column(db.Float, nullable=True)
    pkf_ml = db.Column(db.Float, nullable=True)
    HRV_mean = db.Column(db.Float, nullable=True)
    HRV_median = db.Column(db.Float, nullable=True) 
    HRV_sdnn = db.Column(db.Float, nullable=True)
    HRV_min = db.Column(db.Float, nullable=True)
    HRV_max = db.Column(db.Float, nullable=True)
    HRV_vlf = db.Column(db.Float, nullable=True)
    HRV_vhf = db.Column(db.Float, nullable=True)
    HRV_lf = db.Column(db.Float, nullable=True)
    HRV_hf = db.Column(db.Float, nullable=True)
    HRV_lf_hf = db.Column(db.Float, nullable=True)


"""

    