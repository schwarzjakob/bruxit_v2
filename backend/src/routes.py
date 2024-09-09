from flask import Blueprint, request
from .models import Patient, NightDuration, SSD, db
from .utils import *
from .ssd import *
import psycopg2
from psycopg2.extras import execute_values
import time, io
from sqlalchemy import create_engine
import time


main = Blueprint('main', __name__)



@main.route('/patients-data', methods=['GET'])
def get_patient_data():
    base_dir="C:/Users/eleon/Desktop/SDAP/backend/src/data"
    result = parse_data_structure(base_dir)
    sorted_result = sort_data_structure(result)

    return sorted_result, 200

@main.route('/ssd/<int:patient_id>/<string:week>/<string:filename>', methods=['GET'])
def get_ssd(patient_id, week, filename):
    
    results = SSD.query.filter_by(patient_id=patient_id, week=week, file=filename).all()
    if results:
        ssd = [{'HRV_LFHF': result.HRV_LFHF, 'HRV_SDNN': result.HRV_SDNN, 'x': result.x, 'y': result.y, 'stage': result.stage, 'selected': result.selected} for result in results]
    else:
        start_time = time.time()
        ssd = return_HRV_analysis(patient_id, week, filename)
        end_time = time.time()
        print(f"The loading time for the request is {end_time-start_time} seconds.")

    return ssd, 200


@main.route('/selected-intervals/<int:patient_id>/<string:week>/<string:filename>', methods=['POST'])
def selected_intervals(patient_id, week, filename):
    """
    payload:
        {
            'x': int,
            'y': int,

        }
    """
    selected_intervals = request.json

    # The condition - update all users with the name 'John'
    SSD_to_update = SSD.query.filter_by(patient_id=patient_id, week=week, file=filename)
    
    # Update the 'active' column to False for all these users
    SSD_to_update.update({'selected': False})
    

    for selected_interval in selected_intervals:
        update_row = SSD.query.filter_by(patient_id=patient_id, week=week, file=filename, x=selected_interval['x'], y=selected_interval['y'])
        update_row.update({'selected': True})

    # Commit the transaction
    db.session.commit()

    return "Selected intervals updated.", 200






@main.route('/get-emg',  methods=['GET'])
def get_emg():
    data = read_data_csv(1,1,'1022102', 'c', ['MR', 'ML'])
    loc = read_loc_csv(1,1,'1022102', 'c')

    df_5min = get_interval_from_csv(data, 0, 2000)
    seconds = int(len(df_5min) / 2000)

    mr = pd.Series(df_5min['MR'].to_list())
    ml = pd.Series(df_5min['ML'].to_list())

    mr_rect = rectify_signal(mr)
    ml_rect = rectify_signal(ml)

    mr_rms = rms(mr_rect)
    ml_rms = rms(ml_rect)

    print(mr_rms)

    mr_mvc = find_mvc(mr_rms, loc)
    ml_mvc = find_mvc(ml_rms, loc)

    mr_downsampled = downsample_data(mr_rms, desired_sampling=256)
    ml_downsampled = downsample_data(ml_rms, desired_sampling=256)

    emg_time = np.linspace(0, seconds, seconds * 256, endpoint=False)  # Time vector

    result = {'MR': mr_downsampled.tolist(), 'ML': ml_downsampled.tolist(), 'EMG_t': emg_time.tolist(), 'MR_mvc': mr_mvc, 'ML_mvc': ml_mvc}

    # print(result)

    return result, 200



@main.route('/insert-night/<int:patient_id>/<string:week>/<string:night_id>/<string:recorder>', methods=['POST'])
def insert_night(patient_id, week, night_id, recorder):

    uri = "postgresql://epura:29091998@localhost:5433/sdap"

    df = read_data_csv(patient_id, week, night_id, recorder, ['MR', 'ML', 'ECG'])

    df = df.with_columns(
        patient_id = pl.lit(patient_id),
        week=pl.lit(week),
        night_id=pl.lit(night_id),
        recorder=pl.lit(recorder)
    )
    df = df.with_columns(pl.arange(0, df.height).alias("data_point"))

    df.write_database(table_name="patient_data",  connection=uri, if_table_exists='append')

    print(df.head())

    return "okay", 200

    """"

    print("DataFrame read")
    # Create a list of dictionaries representing rows
    rows = [
        {
            'data_point': idx,
            'patient_id': patient_id,
            'week': week,
            'night_id': night_id,
            'recorder': recorder,
            'mr': row['MR'],
            'ml': row['ML'],
            'ecg': row['ECG']
        }
        for idx, row in enumerate(df.to_dicts())
    ]

    print("Finished creating dict")
    # Use SQLAlchemy bulk_insert_mappings for a bulk insert
    db.session.bulk_insert_mappings(PatientData, rows)
    db.session.commit()
    return "Succesfully inserted into db", 200

    """

"""
@main.route('/get-emg',  methods=['GET'])
def get_emg():
    # Example usage
    file_path = 'C:/Users/eleon/Desktop/SDAP/backend/src/data/p1_wk1/1022102cFnorm.csv'
    sampling_rate = 2000  # Hz
    five_min_samples = sampling_rate*60*5

    # Example to find event start index
    # In this example, you would somehow know where the event starts
    event_start_idx = 1800600  # Hypothetical start index of the event

    df = pl.read_csv(file_path,columns=['ECG'], skip_rows_after_header=five_min_samples * int(event_start_idx/five_min_samples), n_rows=five_min_samples)



    return df.to_dict(as_series=False), 200


"""

