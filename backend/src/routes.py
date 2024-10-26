from flask import Blueprint, request, send_from_directory, abort, jsonify, make_response
from .models import Threshold, NightDuration, SSD, MVC, Prediction, Settings, db
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
import openpyxl


main = Blueprint('main', __name__)


@main.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == "GET":
        settings = Settings.query.first()

        if settings:
            result = {"emgRight": settings.emg_right_name, "emgLeft": settings.emg_left_name, "ecg": settings.ecg_name, 
                    "modelFileName": settings.model_file_name, "originalDataPath": settings.original_data_path,
                    "downsampledDataPath": settings.downsampled_data_path, "modelPath": settings.model_path,
                    "originalSamplingRate": settings.original_sampling_rate, "minimumSamplingRate": settings.minimum_sampling_rate}
        else:
            result = {}

        return result, 200

    if request.method == "POST":
        Settings.query.delete()
        emg_right_name = request.json["emgRight"]
        emg_left_name = request.json["emgLeft"]
        ecg_name = request.json["ecg"]
        model_file_name = request.json["modelFileName"]
        original_data_path = request.json["originalDataPath"]
        downsampled_data_path = request.json["downsampledDataPath"]
        model_path = request.json["modelPath"]
        original_sampling_rate = request.json["originalSamplingRate"]
        minimum_sampling_rate = request.json["minimumSamplingRate"]

        settings = Settings(emg_right_name=emg_right_name, emg_left_name=emg_left_name, ecg_name=ecg_name, model_file_name=model_file_name,
                            original_data_path=original_data_path, downsampled_data_path=downsampled_data_path, model_path=model_path,
                            original_sampling_rate=original_sampling_rate, minimum_sampling_rate=minimum_sampling_rate)
        
        db.session.add(settings)
        db.session.commit()

        return "Settings updated successfully", 200



@main.route('/patients-data', methods=['GET'])
def get_patient_data():
    original_data_path = get_settings().original_data_path
    result = parse_data_structure(original_data_path)
    sorted_result = sort_data_structure(result)

    return sorted_result, 200

@main.route('/ssd/<int:patient_id>/<string:week>/<string:filename>/<int:sampling_rate>', methods=['GET'])
def get_ssd(patient_id, week, filename, sampling_rate):
    
    results = SSD.query.filter_by(patient_id=patient_id, week=week, file=filename).all()
    if results:
        ssd = [{'HRV_LFHF': result.HRV_LFHF, 'HRV_SDNN': result.HRV_SDNN, 'x': result.x, 'y': result.y, 'stage': result.stage} for result in results]
    else:
        start_time = time.time()
        ssd = HRV_analysis(patient_id, week, filename, sampling_rate)
        end_time = time.time()
        print(f"The loading time for the request is {end_time-start_time} seconds.")

    return ssd, 200



@main.route('/patient-threshold/<int:patient_id>/<string:week>/<string:file>', methods=['GET', 'POST'])
def patient_threshold(patient_id, week, file):
    if request.method == 'GET':
        emg_right_name = get_settings().emg_right_name # 'MR'
        emg_left_name = get_settings().emg_left_name # 'ML'
        threshold_db = Threshold.query.filter_by(patient_id=patient_id, week=week, file=file).all()
        if threshold_db:
            result = {}
            if len(threshold_db) == 2:
                for tr in threshold_db:
                    result[tr.sensor] = tr.threshold
            
            if len(threshold_db) == 1:
                if threshold_db[0].sensor == emg_right_name:
                    result[emg_right_name] = threshold_db[0].threshold
                    result[emg_left_name] = 10
                
                if threshold_db[0].sensor == emg_left_name:
                    result[emg_left_name] = threshold_db[0].threshold
                    result[emg_right_name] = 10

        else:
            result = {emg_right_name: 10, emg_left_name: 10}
        
        return result, 200

    if request.method == 'POST':
        """
        payload
            {
                'sensor': string,
                'threshold': int 

            }
        """
        threshold = request.json["threshold"]
        sensor = request.json["sensor"]
        threshold_db = Threshold.query.filter_by(patient_id=patient_id, week=week, file=file, sensor=sensor).first()
        if not threshold_db:
            print("threshold not in db!")
            threshold_db = Threshold(patient_id=patient_id, week=week, file=file, sensor=sensor, threshold=threshold)
            db.session.add(threshold_db)
            db.session.commit()

        else:
            threshold_db.threshold = threshold
            db.session.commit()

        return "threshold updated succesffully", 200

@main.route('/download-events-csv', methods=['GET'])
def download_events_csv():
    # Create a pandas DataFrame with your data
    predictions = Prediction.query.filter_by(confirmed=True)
    prediction_data = []

    for prediction in predictions:
                prediction_data.append({'patient_id': prediction.patient_id,
                                       'week': prediction.week,
                                       'file': prediction.file,
                                       'name': prediction.name,
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
                                        "justification": prediction.justification})

    predictions_df = pd.DataFrame(prediction_data)
    predictions_df = predictions_df.sort_values(by=['patient_id', 'week', 'file', 'name'])

    # Save the DataFrame to a CSV file in-memory (not on disk)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        predictions_df.to_excel(writer, index=False, sheet_name='Confirmed Events')

    output.seek(0)

    # Create a response with the CSV file and set appropriate headers
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=confirmed_events.xlsx'
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    return response

@main.route('/get-emg/<int:patient_id>/<string:week>/<string:file>/<float:idx>',  methods=['GET'])
def get_emg(patient_id, week, file, idx):
    downsampled_data_path = get_settings().downsampled_data_path
    minimum_sampling_rate = get_settings().minimum_sampling_rate # 200
    emg_right_name = get_settings().emg_right_name # 'MR'
    emg_left_name = get_settings().emg_left_name # 'ML'
    
    start = time.time()

    total_seconds = NightDuration.query.filter_by(patient_id=patient_id, week=week, file=file).first().seconds
    print(total_seconds)
    data_length = int(total_seconds * minimum_sampling_rate)

    start_id = int(minimum_sampling_rate * 60 * 5 * idx)
    end_id = start_id + minimum_sampling_rate*60*5

    print("open file")
    data = pl.read_csv(f"{downsampled_data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv",columns=[emg_right_name, emg_left_name], skip_rows_after_header=start_id, n_rows=end_id-start_id)
    features = pl.read_csv(f"{downsampled_data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz_features.csv")

    mr = pd.Series(data[emg_right_name].to_list())
    ml = pd.Series(data[emg_left_name].to_list())

    # Rectify
    print("rectify the signal")
    mr_rect = rectify_signal(mr)
    ml_rect = rectify_signal(ml)

    print("calculate rms")
    mr_rms = rms(mr_rect, sampling=minimum_sampling_rate)
    ml_rms = rms(ml_rect, sampling=minimum_sampling_rate)

    print(mr_rms)

    num_samples = len(mr_rms)
    if end_id >= data_length:
        print("last window")
    start_time = start_id / minimum_sampling_rate  # Convert start index to seconds (since original is at 2000 Hz)
    
    emg_time = np.linspace(start_time, start_time + num_samples / minimum_sampling_rate, num_samples, endpoint=False)

    continuous_features = get_continuous_features(features, idx, data_length=len(mr_rms))
    print("len features: ")
    print(len(continuous_features['std_mr']))
    result = {emg_right_name: mr_rms.tolist(), emg_left_name: ml_rms.tolist(), 'EMG_t': emg_time.tolist()}
    end = time.time()

    print(f"{end-start} seconds taken.")
    # print(result)

    return result | continuous_features, 200


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
    emg_right_name = get_settings().emg_right_name # 'MR'
    emg_left_name = get_settings().emg_left_name # 'ML'

    mvc_mr = MVC.query.filter_by(patient_id=patient_id, week=week, file=file, sensor=emg_right_name).first()
    mvc_ml = MVC.query.filter_by(patient_id=patient_id, week=week, file=file, sensor=emg_left_name).first()

    if mvc_mr is None or mvc_ml is None:
        return "No MVC for this night.", 404
    
    else:
        return {"mvc_mr": mvc_mr.mvc, "mvc_ml": mvc_ml.mvc}, 200

@main.route('/downsample-data/<int:patient_id>/<string:week>/<string:file>', methods=['GET'])
def downsample_data(patient_id, week, file):
    original_data_path = get_settings().original_data_path
    downsampled_data_path = get_settings().downsampled_data_path

    emg_right_name = get_settings().emg_right_name # 'MR'
    emg_left_name = get_settings().emg_left_name # 'ML'
    ecg_name = get_settings().ecg_name # 'ECG'

    original_sampling_rate = get_settings().original_sampling_rate # 2000
    minimum_sampling_rate = get_settings().minimum_sampling_rate # 200

    if os.path.isfile(f"{downsampled_data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv"):
        return "Data already downsampled", 200
    
    else:
        print("Open datasets")
        data = pl.read_csv(f"{original_data_path}/p{patient_id}_wk{week}/{file}", columns=[emg_right_name, emg_left_name, ecg_name])
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

        mr = data.get_column(emg_right_name)
        ml = data.get_column(emg_left_name)
        ecg = data.get_column(ecg_name)

        calculate_night_duration(patient_id, week, file, len(mr), sampling_rate=original_sampling_rate)

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
        mr_rms = rms(mr_rect, sampling=original_sampling_rate)
        ml_rms = rms(ml_rect, sampling=original_sampling_rate)

        print("find mvc")
        mr_mvc = find_mvc(mr_rms, loc)
        ml_mvc = find_mvc(ml_rms, loc)

        print("save mvc to db")
        mr_mvc_db = MVC(patient_id=patient_id, week=week, file=file, sensor=emg_right_name, mvc=mr_mvc.item())
        ml_mvc_db = MVC(patient_id=patient_id, week=week, file=file, sensor=emg_left_name, mvc=ml_mvc.item())
        db.session.add(mr_mvc_db)
        db.session.add(ml_mvc_db)

        db.session.commit()

        mr_ds = nk.signal_resample(mr, sampling_rate=original_sampling_rate, desired_sampling_rate=minimum_sampling_rate)
        ml_ds = nk.signal_resample(ml, sampling_rate=original_sampling_rate, desired_sampling_rate=minimum_sampling_rate)
        ecg_ds = nk.signal_resample(ecg, sampling_rate=original_sampling_rate, desired_sampling_rate=minimum_sampling_rate)

        new_df = pd.DataFrame({emg_right_name: mr_ds, emg_left_name: ml_ds, ecg_name: ecg_ds})

        if not os.path.exists(f'{downsampled_data_path}/p{patient_id}_wk{week}'):
            os.makedirs(f'{downsampled_data_path}/p{patient_id}_wk{week}')

        new_df.to_csv(f"{downsampled_data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv")

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
    
    if((prediction_to_update.start_s != update['start_s']) or (prediction_to_update.end_s != update['end_s'])):
        print("update status because of different start or end")
        prediction_to_update.status = "modified"

    prediction_to_update.start_s = update['start_s']
    prediction_to_update.end_s = update['end_s']
    prediction_to_update.confirmed = update['confirmed']

        # Change y_pred?


    #prediction_to_update.sensor = sensor
    # if event_type: prediction_to_update = event_type
    # prediction_to_update.justification = justification
    db.session.commit()

    return "Confirmation of event updated successfully.", 200

@main.route('/prediction-sensors/<int:patient_id>/<string:week>/<string:file>', methods=['PATCH'])
def patch_prediction_sensors(patient_id, week, file):
    emg_right_name = get_settings().emg_right_name # 'MR'
    emg_left_name = get_settings().emg_left_name # 'ML'
    
    update = request.json
    print(update)
    sensor = update['sensor']

    # sensor = update['sensor']
    if set(sensor) == set([emg_left_name]): sensor = emg_left_name
    if set(sensor) == set([emg_right_name]): sensor = emg_right_name
    if set(sensor) == set([emg_left_name, emg_right_name]): sensor = 'both' 

    prediction_to_update = Prediction.query.filter_by(patient_id=patient_id, week=week, file=file, name=update['name']).first()
    prediction_to_update.sensor = sensor
    db.session.commit()

    return "Sensor updated successfully.", 200

@main.route('/justification/<int:patient_id>/<string:week>/<string:file>', methods=['PATCH'])
def patch_justification(patient_id, week, file):
    update = request.json
    print(update)
    name = update['name']
    justification = update['justification']

    justification_to_update = Prediction.query.filter_by(patient_id=patient_id, week=week, file=file, name=name).first()
    justification_to_update.justification = justification
    db.session.commit()

    return "Justification updated successfully.", 200


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
    #path = 'C:/Users/eleon/Desktop/SDAP/backend/src/data_resampled'
    downsampled_data_path = get_settings().downsampled_data_path
    emg_right_name = get_settings().emg_right_name # 'MR'
    emg_left_name = get_settings().emg_left_name # 'ML'

    # List the generated images from the directory
    output_dir = downsampled_data_path + f"/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv_images"
    if not os.path.exists(output_dir) or version=="new":
        #return jsonify({"error": "No images found"}), 404
        data = pl.read_csv(downsampled_data_path + f"/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv",columns=[emg_right_name, emg_left_name])
        mr = data.get_column(emg_right_name)
        ml = data.get_column(emg_left_name)

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
    downsampled_data_path = get_settings().downsampled_data_path

    folder_path = downsampled_data_path + f'/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv_images/'
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
        downsampled_data_path = get_settings().downsampled_data_path
        model_path = get_settings().model_path

        minimum_sampling_rate = get_settings().minimum_sampling_rate # 200

        model_file_name = get_settings().model_file_name

        if not predictions:

            if os.path.isfile(f"{downsampled_data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz_features.csv"):
                features = pd.read_csv(f"{downsampled_data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz_features.csv")

                times = features.iloc[:, 1:3]
                features = features.iloc[:, 3:43]

            else:
                sensor_data = pd.read_csv(f"{downsampled_data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv")
                features = extract_features_for_prediction(sensor_data, sampling_rate=minimum_sampling_rate)

                features.to_csv(f"{downsampled_data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz_features.csv")

                times = features.iloc[:, 0:2]
                features = features.iloc[:, 2:42]

            # Load model
            loaded_model = xgb.XGBClassifier()
            loaded_model.load_model(f"{model_path}/{model_file_name}")

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
        emg_right_name = get_settings().emg_right_name # 'MR'
        emg_left_name = get_settings().emg_left_name # 'ML'


        event_info = request.json
        print(event_info)

        start_s = float(event_info['start_s'])
        end_s = float(event_info['end_s'])
        event_type = event_info['event_type']

        sensor = event_info['sensor']

        # sensor = update['sensor']
        if set(sensor) == set([emg_left_name]): sensor = emg_left_name
        if set(sensor) == set([emg_right_name]): sensor = emg_right_name
        if set(sensor) == set([emg_left_name, emg_right_name]): sensor = 'both' 
        
        justification = event_info['justification']
        print(start_s, end_s, justification)

        # Calculate metrics
        metrics = get_new_event_metrics(patient_id, week, file, start_s, end_s)

        print(metrics)

        # Get new event name and rename others
        if not predictions:
            print("Add prediction with name e1")
            name = "e1"

            add_new_prediction(patient_id, week, file, start_s, end_s, event_type, sensor, justification, name, metrics)
        
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
                add_new_prediction(patient_id, week, file, start_s, end_s, event_type, sensor, justification, name, metrics)


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

                add_new_prediction(patient_id, week, file, start_s, end_s, event_type, sensor, justification, name, metrics)

        return "Post event added by expert.", 200

# Feature importance (assuming you have trained with feature names)
@main.route('/model-feature-importance', methods=['GET'])
def get_feature_importance():
    model_file_name = get_settings().model_file_name
    model_path = get_settings().model_path

    model = xgb.XGBClassifier()
    model.load_model(f"{model_path}/{model_file_name}")

    importance = model.feature_importances_  # Use feature_importances_ from XGBClassifier
    feature_names = model.get_booster().feature_names
    feature_importance = sorted(zip(feature_names, importance.tolist()), key=lambda x: x[1], reverse=True)

    print(feature_importance)
    print(jsonify(feature_importance))
    return jsonify(feature_importance)

# Model summary information (e.g., model parameters)
@main.route('/model-summary', methods=['GET'])
def get_model_summary():
    model_file_name = get_settings().model_file_name
    model_path = get_settings().model_path

    model = xgb.XGBClassifier()
    model.load_model(f"{model_path}/{model_file_name}")

    params = model.get_params()  # Gets model parameters
    print(params)
    print(jsonify(params))
    return jsonify(params)


#@main.route('/train-model', methods=['GET'])