from flask import Blueprint, request, send_from_directory, abort, jsonify
from .models import Patient, NightDuration, SSD, MVC, Prediction, db
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
from sklearn.preprocessing import MinMaxScaler


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

    total_seconds = NightDuration.query.filter_by(patient_id=patient_id, week=week, file=file).first().seconds
    print(total_seconds)
    data_length = int(total_seconds * 200)

    start_id = int(200 * 60 * 5 * idx)
    end_id = start_id + 200*60*5

    print("open file")
    data = pl.read_csv(f"{data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv",columns=['MR', 'ML'], skip_rows_after_header=start_id, n_rows=end_id-start_id)
    features = pl.read_csv(f"{data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz_features.csv")

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
    if end_id >= data_length:
        print("last window")
    start_time = start_id / 200  # Convert start index to seconds (since original is at 2000 Hz)
    
    emg_time = np.linspace(start_time, start_time + num_samples / 200, num_samples, endpoint=False)

    continuous_features = get_continuous_features(features, idx, data_length=len(mr_rms))
    print("len features: ")
    print(len(continuous_features['std_mr']))
    result = {'MR': mr_rms.tolist(), 'ML': ml_rms.tolist(), 'EMG_t': emg_time.tolist()}
    end = time.time()

    print(f"{end-start} seconds taken.")
    # print(result)

    return result | continuous_features, 200


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


@main.route('/mvc/<int:patient_id>/<string:week>/<string:file>', methods=['GET'])
def get_mvc(patient_id, week, file):
    mvc_mr = MVC.query.filter_by(patient_id=patient_id, week=week, file=file, sensor="MR").first()
    mvc_ml = MVC.query.filter_by(patient_id=patient_id, week=week, file=file, sensor="ML").first()

    if mvc_mr is None or mvc_ml is None:
        return "No MVC for this night.", 404
    
    else:
        return {"mvc_mr": mvc_mr.mvc, "mvc_ml": mvc_ml.mvc}, 200

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

        # Check that there are no null values in the recording
        df_missing = (
            data
            .filter(
                pl.any_horizontal(pl.all().is_null())
            )
        )

        print(df_missing)

        if len(df_missing) > 0:
            print("fill")
            # Fill null values
            data = data.with_columns(pl.all().fill_null(strategy='backward'))

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
        print(mr_short)
        print(type(mr_short))
        mr_rect = rectify_signal(mr_short)
        ml_rect = rectify_signal(ml_short)

        mr_rect = pd.DataFrame(mr_rect)
        ml_rect = pd.DataFrame(ml_rect)

        print("calculate rms")
        mr_rms = rms(mr_rect, sampling=2000)
        ml_rms = rms(ml_rect, sampling=2000)

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

@main.route('/confirmed-events/<int:patient_id>/<string:week>/<string:file>', methods=['PATCH'])
def patch_confirmed_events(patient_id, week, file):
    update = request.json
    print(update)

    
    # sensor = update['sensor']
    #  if set(sensor) == set(['ML']): sensor = 'ML'
    # if set(sensor) == set(['MR']): sensor = 'MR'
    # if set(sensor) == set(['ML', 'MR']): sensor = 'both' 
    # event_type = update['event_type']
    # justification = update['justification']

    prediction_to_update = Prediction.query.filter_by(patient_id=patient_id, week=week, file=file, name=update['name']).first()

    prediction_to_update.start_s = update['start_s']
    prediction_to_update.end_s = update['end_s']
    prediction_to_update.confirmed = update['confirmed']

    if((prediction_to_update.start_s != update['start_s']) or (prediction_to_update.end_s != update['end_s'])):
        prediction_to_update.status = "modified"

        # Change y_pred?


    #prediction_to_update.sensor = sensor
    # if event_type: prediction_to_update = event_type
    # prediction_to_update.justification = justification
    db.session.commit()

    return "Confirmation of event updated successfully.", 200

@main.route('/prediction-sensors/<int:patient_id>/<string:week>/<string:file>/', methods=['PATCH'])
def patch_prediction_sensors(patient_id, week, file):
    update = request.json
    print(update)
    sensor = update['sensor']

    # sensor = update['sensor']
    if set(sensor) == set(['ML']): sensor = 'ML'
    if set(sensor) == set(['MR']): sensor = 'MR'
    if set(sensor) == set(['ML', 'MR']): sensor = 'both' 

    prediction_to_update = Prediction.query.filter_by(patient_id=patient_id, week=week, file=file, name=update['name']).first()
    prediction_to_update.sensor = sensor
    db.session.commit()

    return "Sensor updated successfully.", 200


@main.route('/prediction-event-type/<int:patient_id>/<string:week>/<string:file>', methods=['PATCH'])
def patch_prediction_event_type(patient_id, week, file):
    update = request.json
    print(update)
    event_type = update['event_type']

    prediction_to_update = Prediction.query.filter_by(patient_id=patient_id, week=week, file=file, name=update['name']).first()
    prediction_to_update.event_type = event_type
    db.session.commit()

    return "Event type updated successfully.", 200

@main.route('/night-images/<int:patient_id>/<string:week>/<string:file>/<string:version>', methods=['GET'])
def get_night_images(patient_id, week, file, version):
    path = 'C:/Users/eleon/Desktop/SDAP/backend/src/data_resampled'

    # List the generated images from the directory
    output_dir = path + f"/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv_images"
    if not os.path.exists(output_dir) or version=="new":
        #return jsonify({"error": "No images found"}), 404
        data = pl.read_csv(path + f"/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv",columns=['MR', 'ML'])
        mr = data.get_column("MR")
        ml = data.get_column("ML")

        predictions = Prediction.query.filter_by(patient_id=patient_id, week=week, file=file).all()
        print(predictions)
        print(type(predictions))
        #if not predictions:
        #    predictions = {}
        generate_night_images(patient_id, week, file, mr, ml, predictions)

    # List all images in the directory
    image_files = [f for f in os.listdir(output_dir) if f.endswith('.png')]

    print(image_files)

    # Create URLs for the generated images
    images_with_urls = [
        {
            "label": 'Whole Night Signal' if 'whole_night_signal' in img else f"Sleep Cycle {img.split('_')[2][:-4]}",
            "src": f"http://localhost:5000/image/{patient_id}/{week}/{file}/{img}"
        }
        for img in image_files
    ]

    return jsonify(images_with_urls), 200


@main.route('/image/<int:patient_id>/<string:week>/<string:file>/<string:img>', methods=['GET'])
def serve_image(patient_id, week, file, img):
    path = 'C:/Users/eleon/Desktop/SDAP/backend/src/data_resampled/'

    folder_path = path + f'p{patient_id}_wk{week}/{file[:-4]}200Hz.csv_images/'
    print(folder_path + img)
    if os.path.exists(folder_path + img):
        return send_from_directory(folder_path, img)
    else:
        return abort(404)  # File not found

@main.route('/predict-events/<int:patient_id>/<string:week>/<string:file>', methods=['GET', 'POST'])
def predict_events(patient_id, week, file):
    predictions = Prediction.query.filter_by(patient_id=patient_id, week=week, file=file).all()
    print(predictions)

    if request.method == 'GET':
        path = 'C:/Users/eleon/Desktop/SDAP/backend/src/data_resampled'
        model_name = 'brazil_model_features_new_2.json'
        #sensor_data = read_data_csv(patient_id, week, file, ['ECG', 'MR', 'ML'])

        if not predictions:

            if os.path.isfile(f"{path}/p{patient_id}_wk{week}/{file[:-4]}200Hz_features.csv"):
                features = pd.read_csv(f"{path}/p{patient_id}_wk{week}/{file[:-4]}200Hz_features.csv")

                times = features.iloc[:, 1:3]
                features = features.iloc[:, 3:43]

            else:
                sensor_data = pd.read_csv(f"{path}/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv")
                features = extract_features_for_prediction(sensor_data)

                features.to_csv(f"{path}/p{patient_id}_wk{week}/{file[:-4]}200Hz_features.csv")

                times = features.iloc[:, 0:2]
                features = features.iloc[:, 2:42]

            # Load model
            loaded_model = xgb.XGBClassifier()
            loaded_model.load_model(f"C:/Users/eleon/Desktop/SDAP/backend/src/data_brazil/{model_name}")

            y_pred = loaded_model.predict(features)  

            y_pred_proba = loaded_model.predict_proba(features)  # Probabilities for each class

            print(f"Predicted class labels for new data: {y_pred}")

            print(f"Predicted probabilities for new data: {y_pred_proba}")

            unique, counts = np.unique(y_pred, return_counts=True)

            print(f"Prediction: {dict(zip(unique, counts))}")

            result = pd.concat([times, features], axis=1)
            result["y"] = y_pred
            result["y_prob"] = [max(p) for p in y_pred_proba]

            #print(result)

            predictions = result[result["y"] == 1]
            predictions["confirmed"] = True

            print(predictions)



            predictions_with_features = aggregate_events(predictions)

            for key in predictions_with_features:
                prediction_db = Prediction(patient_id=patient_id, week=week, file=file, name=key, start_s=predictions_with_features[key]['start_s'], end_s=predictions_with_features[key]['end_s'],
                                        std_mr=predictions_with_features[key]['std_mr'].item(), std_ml=predictions_with_features[key]['std_ml'].item(), var_mr=predictions_with_features[key]['var_mr'].item(),
                                        var_ml=predictions_with_features[key]['var_ml'].item(), rms_mr=predictions_with_features[key]['rms_mr'].item(), rms_ml=predictions_with_features[key]['rms_ml'].item(),
                                        mav_mr=predictions_with_features[key]['mav_mr'].item(), mav_ml=predictions_with_features[key]['mav_ml'].item(), log_det_mr=predictions_with_features[key]['log_det_mr'].item(),
                                        log_det_ml=predictions_with_features[key]['log_det_ml'].item(), wl_mr=predictions_with_features[key]['wl_mr'].item(), wl_ml=predictions_with_features[key]['wl_ml'].item(),
                                        aac_mr=predictions_with_features[key]['aac_mr'].item(), aac_ml=predictions_with_features[key]['aac_ml'].item(), dasdv_mr=predictions_with_features[key]['dasdv_mr'].item(),
                                        dasdv_ml=predictions_with_features[key]['dasdv_ml'].item(),wamp_mr=predictions_with_features[key]['wamp_mr'].item(), wamp_ml=predictions_with_features[key]['wamp_ml'].item(), 
                                        fr_mr=predictions_with_features[key]['fr_mr'].item(), fr_ml=predictions_with_features[key]['fr_ml'].item(), mnp_mr=predictions_with_features[key]['mnp_mr'].item(),
                                        mnp_ml=predictions_with_features[key]['mnp_ml'].item(), tot_mr=predictions_with_features[key]['tot_mr'].item(), tot_ml=predictions_with_features[key]['tot_ml'].item(),
                                        mnf_mr=predictions_with_features[key]['mnf_mr'].item(), mnf_ml=predictions_with_features[key]['mnf_ml'].item(), mdf_mr=predictions_with_features[key]['mdf_mr'].item(), 
                                        mdf_ml=predictions_with_features[key]['mdf_ml'].item(), pkf_mr=predictions_with_features[key]['pkf_mr'].item(), pkf_ml=predictions_with_features[key]['pkf_ml'].item(),
                                        HRV_mean=predictions_with_features[key]['HRV_mean'].item(), HRV_median=predictions_with_features[key]['HRV_median'].item(), HRV_sdnn=predictions_with_features[key]['HRV_sdnn'].item(),
                                        HRV_min=predictions_with_features[key]['HRV_min'].item(), HRV_max=predictions_with_features[key]['HRV_max'].item(), HRV_vhf=predictions_with_features[key]['HRV_vhf'].item(),
                                        HRV_lf=predictions_with_features[key]['HRV_lf'].item(), HRV_hf=predictions_with_features[key]['HRV_hf'].item(), HRV_lf_hf=predictions_with_features[key]['HRV_lf_hf'].item(),
                                        RRI=predictions_with_features[key]['RRI'].item(), y_prob=predictions_with_features[key]['y_prob'].item(), confirmed=True, sensor="both", event_type="", status="model", justification="")

                db.session.add(prediction_db)

            db.session.commit()

            return predictions_with_features, 200
        else:
            result = {}
            for prediction in predictions:
                result[prediction.name] = {
                    "start_s": prediction.start_s,
                    "end_s": prediction.end_s,
                    "std_mr": prediction.std_mr,
                    "std_ml": prediction.std_ml,
                    "var_mr": prediction.var_mr,
                    "var_ml": prediction.var_ml,
                    "rms_mr": prediction.rms_mr,
                    "rms_ml": prediction.rms_ml,
                    "mav_mr": prediction.mav_mr,
                    "mav_ml": prediction.mav_ml,
                    "log_det_mr": prediction.log_det_mr,
                    "log_det_ml": prediction.log_det_ml,
                    "wl_mr": prediction.wl_mr,
                    "wl_ml": prediction.wl_ml,
                    "aac_mr": prediction.aac_mr,
                    "aac_ml": prediction.aac_ml,
                    "dasdv_mr": prediction.dasdv_mr,
                    "dasdv_ml": prediction.dasdv_ml,
                    "wamp_mr": prediction.wamp_mr,
                    "wamp_ml": prediction.wamp_ml,
                    "fr_mr": prediction.fr_mr,
                    "fr_ml": prediction.fr_ml,
                    "mnp_mr": prediction.mnp_mr,
                    "mnp_ml": prediction.mnp_ml,
                    "tot_mr": prediction.tot_mr,
                    "tot_ml": prediction.tot_ml,
                    "mnf_mr": prediction.mnf_mr,
                    "mnf_ml": prediction.mnf_ml,
                    "mdf_mr": prediction.mdf_mr,
                    "mdf_ml": prediction.mdf_ml,
                    "pkf_mr": prediction.pkf_mr,
                    "pkf_ml": prediction.pkf_ml,
                    "HRV_mean": prediction.HRV_mean,
                    "HRV_median": prediction.HRV_median,
                    "HRV_sdnn": prediction.HRV_sdnn,
                    "HRV_min": prediction.HRV_min,
                    "HRV_max": prediction.HRV_max,
                    "HRV_vhf": prediction.HRV_vhf,
                    "HRV_lf": prediction.HRV_lf,
                    "HRV_hf": prediction.HRV_hf,
                    "HRV_lf_hf": prediction.HRV_lf_hf,
                    "RRI": prediction.RRI,
                    "y_prob": prediction.y_prob,
                    "confirmed": prediction.confirmed,
                    "sensor": prediction.sensor,
                    "event_type": prediction.event_type,
                    "status": prediction.status,
                    "justification": prediction.justification
                }

            return result, 200
        
    if request.method == 'POST':
        event_info = request.json
        print(event_info)

        start_s = float(event_info['start_s'])
        end_s = float(event_info['end_s'])
        justification = event_info['justification']
        print(start_s, end_s, justification)

        # Calculate metrics
        metrics = get_new_event_metrics(patient_id, week, file, start_s, end_s)

        print(metrics)

        # Get new event name and rename others
        if not predictions:
            print("Add prediction with name e1")
            name = "e1"

            add_new_prediction(patient_id, week, file, start_s, end_s, justification, name, metrics)
        
        else:
            print("logic to find new event position")
            events_after = Prediction.query.filter(
                Prediction.patient_id==patient_id,
                Prediction.week==week,
                Prediction.file==file,
                Prediction.start_s >= start_s
            ).order_by(Prediction.start_s).all()

            print(f"Event after: {events_after}")
            if events_after:
                name = events_after[0].name
                position = int(name[1:])

                for event in events_after:
                    position +=1
                    event.name = f"e{position}" 
                    #print(event.file, event.name, event.start_s, event.end_s)
                db.session.commit()
                add_new_prediction(patient_id, week, file, start_s, end_s, justification, name, metrics)


            else:
                last_event = Prediction.query.filter(
                    Prediction.patient_id == patient_id,
                    Prediction.week == week,
                    Prediction.file == file,
                    Prediction.start_s < start_s
                ).order_by(Prediction.start_s.desc()).first()

                print("Last event: ", last_event.name)

                last_position = int(last_event.name[1:])
                name = f"e{last_position + 1}"

                add_new_prediction(patient_id, week, file, start_s, end_s, justification, name, metrics)

        return "Post event added by expert.", 200




    



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

        

        


