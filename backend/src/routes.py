from flask import Blueprint, request
from .models import Patient, NightDuration, SSD, MVC, db
from .utils import *
from .ssd import *
import psycopg2
from psycopg2.extras import execute_values
import time, io
from sqlalchemy import create_engine
import time
import xgboost as xgb
import joblib
import pandas as pd
import polars as pl


main = Blueprint('main', __name__)



@main.route('/patients-data', methods=['GET'])
def get_patient_data():
    base_dir="C:/Users/eleon/Desktop/SDAP/backend/src/data"
    result = parse_data_structure(base_dir)
    sorted_result = sort_data_structure(result)

    return sorted_result, 200

@main.route('/ssd/<int:patient_id>/<string:week>/<string:filename>/<int:sampling_rate>', methods=['GET'])
def get_ssd(patient_id, week, filename, sampling_rate):
    
    results = SSD.query.filter_by(patient_id=patient_id, week=week, file=filename).all()
    if results:
        ssd = [{'HRV_LFHF': result.HRV_LFHF, 'HRV_SDNN': result.HRV_SDNN, 'x': result.x, 'y': result.y, 'stage': result.stage, 'selected': result.selected} for result in results]
    else:
        start_time = time.time()
        ssd = return_HRV_analysis(patient_id, week, filename, sampling_rate)
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

@main.route('/get-emg/<int:patient_id>/<string:week>/<string:file>/<float:idx>',  methods=['GET'])
def get_emg(patient_id, week, file, idx):
    data_path = 'C:/Users/eleon/Desktop/SDAP/backend/src/data_resampled'
    start = time.time()
    start_id = int(200 * 60 * 5 * idx)
    end_id = start_id + 200*60*5

    print("open file")
    data = pl.read_csv(f"{data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv",columns=['MR', 'ML'], skip_rows_after_header=start_id, n_rows=end_id-start_id)

    mr = pd.Series(data['MR'].to_list())
    ml = pd.Series(data['ML'].to_list())

    # Rectify
    print("rectify the signal")
    mr_rect = rectify_signal(mr)
    ml_rect = rectify_signal(ml)

    print("calculate rms")
    mr_rms = rms(mr_rect)
    ml_rms = rms(ml_rect)

    print(mr_rms)

    num_samples = len(mr_rms)
    start_time = start_id / 200  # Convert start index to seconds (since original is at 2000 Hz)
    
    emg_time = np.linspace(start_time, start_time + num_samples / 200, num_samples, endpoint=False)


    result = {'MR': mr_rms.tolist(), 'ML': ml_rms.tolist(), 'EMG_t': emg_time.tolist()}
    end = time.time()

    print(f"{end-start} seconds taken.")
    # print(result)

    return result, 200


"""

@main.route('/get-emg/<int:patient_id>/<string:week>/<string:file>/<int:idx>',  methods=['GET'])
def get_emg(patient_id, week, file, idx):
    data_path = 'C:/Users/eleon/Desktop/SDAP/backend/src/data/'
    start = time.time()
    start_id = 2000 * 60 * 5 * idx
    end_id = start_id + 2000*60*5

    print("open file")
    data = pl.read_csv(f"{data_path}/p{patient_id}_wk{week}/{file}",columns=['MR', 'ML'], skip_rows_after_header=start_id, n_rows=end_id-start_id)
    loc = read_loc_csv(patient_id, week, file)


    mr = pd.Series(data['MR'].to_list())
    ml = pd.Series(data['ML'].to_list())

    # Rectify
    print("rectify the signal")
    mr_rect = rectify_signal(mr)
    ml_rect = rectify_signal(ml)

    print("calculate rms")
    mr_rms = rms(mr_rect)
    ml_rms = rms(ml_rect)

    print(mr_rms)

    print("find mvc")
    mr_mvc = find_mvc(mr_rms, loc)
    ml_mvc = find_mvc(ml_rms, loc)

    print("downsample data")
    mr_downsampled = downsample_data(mr_rms, desired_sampling=256)
    ml_downsampled = downsample_data(ml_rms, desired_sampling=256)

     # Generate the time vector based on the downsampled data length and start_index
    num_samples = len(mr_downsampled)
    start_time = start_id / 2000  # Convert start index to seconds (since original is at 2000 Hz)
    
    emg_time = np.linspace(start_time, start_time + num_samples / 256, num_samples, endpoint=False)


    result = {'MR': mr_downsampled.tolist(), 'ML': ml_downsampled.tolist(), 'EMG_t': emg_time.tolist(), 'MR_mvc': mr_mvc, 'ML_mvc': ml_mvc}
    end = time.time()

    print(f"{end-start} seconds taken.")
    # print(result)

    return result, 200

"""

@main.route('/night-duration/<int:patient_id>/<string:week>/<string:file>', methods=['GET'])
def get_night_duration(patient_id, week, file):
    night_duration = NightDuration.query.filter_by(patient_id=patient_id, week=week, file=file).first()
    print(night_duration.seconds)

    if night_duration is None:
        return "No night duration for this night.", 404
    
    else:
        return {"duration_s": night_duration.seconds}, 200

@main.route('/downsample-data/<int:patient_id>/<string:week>/<string:file>', methods=['GET'])
def downsample_data(patient_id, week, file):
    path_resampled_data = 'C:/Users/eleon/Desktop/SDAP/backend/src/data_resampled'
    path_data = 'C:/Users/eleon/Desktop/SDAP/backend/src/data'

    if os.path.isfile(f"{path_resampled_data}/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv"):
        return "Data already downsampled", 200
    
    else:
        print("Open datasets")
        data = pl.read_csv(f"{path_data}/p{patient_id}_wk{week}/{file}", columns=["MR", "ML", "ECG"])
        loc = read_loc_csv(patient_id, week, file)

        mr = data.get_column("MR")
        ml = data.get_column("ML")
        ecg = data.get_column("ECG")

        calculate_night_duration(patient_id, week, file, len(mr), sampling_rate=2000)

        print("Extract MVC")

        last_index = int(loc[2, 1])
        print(last_index)
        mr_short = mr[:last_index+1]
        ml_short = ml[:last_index+1]

        print("rectify")
        mr_rect = rectify_signal(mr_short)
        ml_rect = rectify_signal(ml_short)

        mr_rect = pd.DataFrame(mr_rect)
        ml_rect = pd.DataFrame(ml_rect)

        print("calculate rms")
        mr_rms = rms(mr_rect)
        ml_rms = rms(ml_rect)

        print("find mvc")
        mr_mvc = find_mvc(mr_rms, loc)
        ml_mvc = find_mvc(ml_rms, loc)

        print("save mvc to db")
        mr_mvc_db = MVC(patient_id=patient_id, week=week, file=file, sensor='MR', mvc=mr_mvc.item())
        ml_mvc_db = MVC(patient_id=patient_id, week=week, file=file, sensor='ML', mvc=ml_mvc.item())
        db.session.add(mr_mvc_db)
        db.session.add(ml_mvc_db)

        db.session.commit()
        

        mr_ds = nk.signal_resample(mr, sampling_rate=2000, desired_sampling_rate=200)
        ml_ds = nk.signal_resample(ml, sampling_rate=2000, desired_sampling_rate=200)
        ecg_ds = nk.signal_resample(ecg, sampling_rate=2000, desired_sampling_rate=200)

        new_df = pd.DataFrame({'MR': mr_ds, 'ML': ml_ds, 'ECG': ecg_ds})

        if not os.path.exists(f'{path_resampled_data}/p{patient_id}_wk{week}'):
            os.makedirs(f'{path_resampled_data}/p{patient_id}_wk{week}')

        new_df.to_csv(f"{path_resampled_data}/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv")

        return "Data downsampled and saved correctly.", 200


@main.route('/predict-events/<int:patient_id>/<string:week>/<string:file>', methods=['GET'])
def predict_events(patient_id, week, file):
    path = 'C:/Users/eleon/Desktop/SDAP/backend/src/data_resampled'
    model_name = 'brazil_model_features_new.json'
    #sensor_data = read_data_csv(patient_id, week, file, ['ECG', 'MR', 'ML'])

    if os.path.isfile(f"{path}/p{patient_id}_wk{week}/{file[:-4]}200Hz_features.csv"):
        features = pd.read_csv(f"{path}/p{patient_id}_wk{week}/{file[:-4]}200Hz_features.csv")

        times = features.iloc[:, 1:3]
        features = features.iloc[:, 3:46]

    else:
        sensor_data = pd.read_csv(f"{path}/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv")
        features = extract_features_for_prediction(sensor_data)

        features.to_csv(f"{path}/p{patient_id}_wk{week}/{file[:-4]}200Hz_features.csv")

        times = features.iloc[:, 0:2]
        features = features.iloc[:, 2:45]

    # Load model
    scaler = joblib.load("C:/Users/eleon/Desktop/SDAP/backend/src/data_brazil/minmax_scaler.pkl")
    loaded_model = xgb.XGBClassifier()
    loaded_model.load_model(f"C:/Users/eleon/Desktop/SDAP/backend/src/data_brazil/{model_name}")

    # Scale features
    features_scaled = pd.DataFrame(scaler.transform(features), columns=features.columns)

    y_pred = loaded_model.predict(features_scaled)  

    y_pred_proba = loaded_model.predict_proba(features_scaled)  # Probabilities for each class

    print(f"Predicted class labels for new data: {y_pred}")

    print(f"Predicted probabilities for new data: {y_pred_proba}")

    unique, counts = np.unique(y_pred, return_counts=True)

    print(f"Prediction: {dict(zip(unique, counts))}")

    result = pd.concat([times, features], axis=1)
    result["y"] = y_pred
    result["y_prob"] = [max(p) for p in y_pred_proba]

    #print(result)

    predictions = result[result["y"] == 1]

    print(predictions)

    predictions_with_features = aggregate_events(predictions)


    return predictions_with_features, 200



    



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


@main.route('/get-emg-5-min/<string:sensor>/<int:patient_id>/<string:week>/<string:filename>/<int:x>/<int:y>',  methods=['GET'])
def get_mr_5_min(sensor, patient_id, week, filename, x, y):
    try:
        sampling_rate = 256
        total_seconds = NightDuration.query.filter_by(patient_id=patient_id, week=week, file=filename).first().seconds
        print(total_seconds)
        data_length = int(total_seconds * sampling_rate)

        print(f"data length: {data_length}")

        # Example usage
        file_path = f'C:/Users/eleon/Desktop/SDAP/backend/src/data_resampled/p{patient_id}_wk{week}/{filename}_emg_256Hz.csv'
        
        start_id, end_id = convert_to_sample_indexes(x, y, data_length, 256)

        print("got start and end id")
        print(start_id, end_id)

        if sensor == 'emg':
            df = pl.read_csv(file_path,columns=['MR', 'ML'], skip_rows_after_header=start_id, n_rows=end_id-start_id)
            print("df read ")

            seconds = int(len(df) / 2000)

            df = get_5_min_emg(df, seconds)
            
        if sensor == 'ecg':
            df = pl.read_csv(file_path,columns=['ECG'], skip_rows_after_header=start_id, n_rows=end_id-start_id)


        return df, 200
    
    except Exception as e:
        print(f"An error occurred: {e}")



@main.route('/save-emg-downsampled-data/<int:patient_id>/<string:week>/<string:filename>',  methods=['GET'])
def save_downsampled_data(patient_id, week, filename):
    try:
        print("Start")
        start_time = time.time()
        sampling_rate = 2000
        
        file_path = f'C:/Users/eleon/Desktop/SDAP/backend/src/data/p{patient_id}_wk{week}/{filename}'

        loc = pl.read_csv(file_path.rsplit('Fnorm.csv', 1)[0] + "location_Bites.csv")
        df = pl.read_csv(file_path,columns=['MR', 'ML'])

        print("df read")

        seconds = int(len(df) / sampling_rate)

        preprocess_and_downsample_emg(patient_id, week, filename, df, loc, seconds)

        end_time = time.time()

        print(F"Elapsed time: {(end_time-start_time)}")

        return "Downsampled data saved successfully.", 200
    
    except Exception as e:
        print(f"An error occurred: {e}")

        

        


