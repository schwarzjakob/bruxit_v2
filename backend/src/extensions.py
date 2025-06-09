from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
import duckdb

# TODO: create schema with settings emg_right, emg_left, ecg


db = SQLAlchemy()
migrate = Migrate()
cors = CORS()


class DuckDB:
    def __init__(self):
        self.conn = None

    def init_app(self, app):
        db_path = app.config["DUCKDB_FILE"]
        # open the file exactly once
        self.conn = duckdb.connect(database=db_path, read_only=False)
        # one‐time DDL for both raw & feature schemas
        self.conn.execute(
            """
            -- raw schema holds the original Fnorm recordings + location bites
            CREATE SCHEMA IF NOT EXISTS raw;

            CREATE TABLE IF NOT EXISTS raw.Fnorm (
                patient_id BIGINT,
                week              VARCHAR,
                file              VARCHAR,
                MR                DOUBLE,
                ML                DOUBLE,
                SU                DOUBLE,
                Microphone        DOUBLE,
                Eye               DOUBLE,
                ECG               DOUBLE,
                Pressure_Sensor   DOUBLE,
            );

            CREATE TABLE IF NOT EXISTS raw.location_bites (
                patient_id   BIGINT,
                week         VARCHAR,
                file         VARCHAR,
                begin_idx    BIGINT,
                end_idx      BIGINT,
                duration_s   DOUBLE,
                PRIMARY KEY (patient_id, week, file, begin_idx, end_idx)
            );

            -- downsampled schema holds the exact 200 Hz versions of each
            CREATE SCHEMA IF NOT EXISTS downsampled;

            CREATE TABLE IF NOT EXISTS downsampled.Fnorm (
                patient_id BIGINT,
                week       VARCHAR,
                file       VARCHAR,
                sample_idx INTEGER,       -- 0-based index into the downsampled stream
                MR         DOUBLE,
                ML         DOUBLE,
                ECG        DOUBLE,
                PRIMARY KEY (patient_id, week, file, sample_idx)
            );

            -- features schema holds the sliding‐window features
            CREATE SCHEMA IF NOT EXISTS features;

            CREATE TABLE IF NOT EXISTS features.feature_windows (
                patient_id   BIGINT,
                week         VARCHAR,
                file         VARCHAR,
                window_idx   INTEGER,
                start_time   DOUBLE,
                end_time     DOUBLE,
                std_mr       DOUBLE,
                std_ml       DOUBLE,
                var_mr       DOUBLE,
                var_ml       DOUBLE,
                rms_mr       DOUBLE,
                rms_ml       DOUBLE,
                mav_mr       DOUBLE,
                mav_ml       DOUBLE,
                log_det_mr   DOUBLE,
                log_det_ml   DOUBLE,
                wl_mr        DOUBLE,
                wl_ml        DOUBLE,
                aac_mr       DOUBLE,
                aac_ml       DOUBLE,
                dasdv_mr     DOUBLE,
                dasdv_ml     DOUBLE,
                wamp_mr      DOUBLE,
                wamp_ml      DOUBLE,
                fr_mr        DOUBLE,
                fr_ml        DOUBLE,
                mnp_mr       DOUBLE,
                mnp_ml       DOUBLE,
                tot_mr       DOUBLE,
                tot_ml       DOUBLE,
                mnf_mr       DOUBLE,
                mnf_ml       DOUBLE,
                mdf_mr       DOUBLE,
                mdf_ml       DOUBLE,
                pkf_mr       DOUBLE,
                pkf_ml       DOUBLE,
                HRV_mean     DOUBLE,
                HRV_median   DOUBLE,
                HRV_sdnn     DOUBLE,
                HRV_min      DOUBLE,
                HRV_max      DOUBLE,
                HRV_vhf      DOUBLE,
                HRV_lf       DOUBLE,
                HRV_hf       DOUBLE,
                HRV_lf_hf    DOUBLE,
                RRI          DOUBLE,
                PRIMARY KEY (patient_id, week, file, window_idx)
            );


        """
        )
        app.extensions["duckdb"] = self

    @property
    def cursor(self):
        return self.conn


duckdb_instance = DuckDB()
