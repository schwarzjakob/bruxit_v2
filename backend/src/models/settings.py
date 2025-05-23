from src.extensions import db


class Settings(db.Model):
    __tablename__ = "settings"
    id = db.Column(db.Integer, primary_key=True)
    emg_right_name = db.Column(db.String(50), nullable=False)
    emg_left_name = db.Column(db.String(50), nullable=False)
    ecg_name = db.Column(db.String(50), nullable=False)
    model_file_name = db.Column(db.String(100), nullable=False)
    original_data_path = db.Column(db.String(100), nullable=False)
    downsampled_data_path = db.Column(db.String(100), nullable=False)
    model_path = db.Column(db.String(100), nullable=False)
    original_sampling_rate = db.Column(db.Integer, nullable=False)
    minimum_sampling_rate = db.Column(db.Integer, nullable=False)
