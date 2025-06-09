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
            CREATE SCHEMA IF NOT EXISTS raw;
            CREATE TABLE IF NOT EXISTS raw.recordings AS SELECT * FROM raw.recordings WHERE false;
            CREATE SCHEMA IF NOT EXISTS feat;
            CREATE TABLE IF NOT EXISTS feat.features (
                patient_id BIGINT,
                week       VARCHAR,
                file       VARCHAR,
                window_idx INTEGER,
                -- other feature columns added automatically by your repo
                PRIMARY KEY (patient_id, week, file, window_idx)
            );
            CREATE SCHEMA IF NOT EXISTS ds;
            CREATE TABLE IF NOT EXISTS ds.signal_200hz (
                patient_id  BIGINT,
                week        VARCHAR,
                file        VARCHAR,
                sample_idx  INTEGER,          -- 0-based
                MR          DOUBLE,
                ML          DOUBLE,
                ECG         DOUBLE,
                PRIMARY KEY (patient_id, week, file, sample_idx)
            );
        """
        )
        app.extensions["duckdb"] = self

    @property
    def cursor(self):
        return self.conn


duckdb_instance = DuckDB()
