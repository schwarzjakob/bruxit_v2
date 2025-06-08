import polars as pl
import pandas as pd
import neurokit2 as nk
import numpy as np
import os
import re
from collections import defaultdict
import datetime
from src.extensions import db
from src.models.night_duration import NightDuration
from src.models.event_prediction import EventPrediction
from src.models.settings import Settings
import math
from sklearn.preprocessing import MinMaxScaler
import matplotlib

matplotlib.use("Agg")  # Use the non-GUI backend for Matplotlib
import matplotlib.pyplot as plt
import shutil


def get_settings():
    return Settings.query.first()


def read_loc_csv(p, w, f):
    data_path = get_settings().original_data_path
    f_short = f.rsplit("Fnorm.csv", 1)[0]
    loc = pl.read_csv(data_path + f"/p{p}_wk{w}/{f_short}location_Bites.csv")

    return loc


def rectify_signal(signal):
    return np.abs(signal)


def rms(emg_signal, sampling=200, window=0.06, min_periods=1):
    window_size = int(window * sampling)

    # Compute RMS with a rolling window
    signal_rms = emg_signal.rolling(window=window_size, min_periods=min_periods).apply(
        lambda x: np.sqrt(np.mean(x**2)), raw=True
    )

    # Check the output size
    print(f"Original signal length: {len(emg_signal)}")
    print(f"RMS signal length: {len(signal_rms)}")

    return signal_rms


def fast_rms(signal, sampling=200, window=0.06):
    window_size = int(window * sampling)

    # Square the signal
    squared_signal = np.square(signal)

    # Compute the rolling mean of the squared signal
    rolling_mean = (
        pd.Series(squared_signal).rolling(window=window_size, min_periods=1).mean()
    )

    # Take the square root of the rolling mean to get the RMS
    rms_values = np.sqrt(rolling_mean)

    return rms_values


def find_mvc(signal_rms, loc):
    # Define Maximum Volontary Contraction
    signal_mvc = 0

    for row in loc.iter_rows():
        begin_contraction, end_contraction = int(row[0]), int(row[1])

        signal_bite_data = signal_rms[begin_contraction:end_contraction]

        signal_max_in_bite = signal_bite_data.max().iloc[0]

        if float(signal_max_in_bite) > float(signal_mvc):
            signal_mvc = signal_max_in_bite

        return signal_mvc


def parse_data_structure(base_dir):
    data_dict = defaultdict(lambda: defaultdict(list))

    # Match folder names (e.g., p1_wk1, p1_wk3-4)
    folder_pattern = re.compile(r"^(p\d+)_wk(\d+(-\d+)?)$")

    for root, dirs, files in os.walk(base_dir):
        for dir_name in dirs:
            match = folder_pattern.match(dir_name)
            if match:
                patient_id = match.group(1)[1:]
                week_id = match.group(2)
                # Collect files in directory
                folder_path = os.path.join(root, dir_name)
                night_files = [
                    f
                    for f in os.listdir(folder_path)
                    if f.endswith("Fnorm.csv") and not f.endswith("location_Bites.csv")
                ]

                for file_name in night_files:
                    file_path = os.path.join(folder_path, file_name)

                    # Calculate file size in GB
                    file_size_bytes = os.path.getsize(file_path)
                    file_size_gb = file_size_bytes / (1024**3)

                    data_dict[patient_id][week_id].append(
                        {
                            "file_name": file_name,
                            "size_gb": round(
                                file_size_gb, 2
                            ),  # Rounded to 4 decimal places
                        }
                    )

    return dict(data_dict)


def sort_week_key(week):
    """Extract numerical parts of the week to enable correct sorting."""
    # Find all numeric parts of the week identifier (e.g., "13-14" becomes [13, 14])
    numbers = list(map(int, re.findall(r"\d+", week)))
    return (
        numbers[0],
        numbers[-1],
    )  # Sort by the first number, then by the last number if range exists


def sort_data_structure(data_dict):
    sorted_dict = {}

    for patient, weeks in data_dict.items():
        # Sort weeks using the custom key
        sorted_weeks = dict(sorted(weeks.items(), key=lambda x: sort_week_key(x[0])))
        sorted_dict[patient] = sorted_weeks

    return sorted_dict


def calculate_night_duration(patient_id, week, file_name, file_length, sampling_rate):
    seconds = file_length / sampling_rate
    duration = datetime.timedelta(seconds=seconds)

    nigh_duration = NightDuration.query.filter_by(
        patient_id=patient_id,
        week=week,
        file=file_name,
        seconds=seconds,
        duration=duration,
    ).first()

    if nigh_duration is None:
        night_duration = NightDuration(
            patient_id=patient_id,
            week=week,
            file=file_name,
            seconds=seconds,
            duration=duration,
        )

        db.session.add(night_duration)
        db.session.commit()


def convert_to_sample_indexes(x, y, data_length, sampling_rate):
    # Samples per minute
    samples_per_minute = sampling_rate * 60

    # Samples per 5-minuteS
    samples_per_5_min = 5 * samples_per_minute

    # 5-minute intervals in a row (90-minute - 18 intervals)
    intervals_per_row = 90 // 5

    # Start index
    start_id = (y * intervals_per_row + x) * samples_per_5_min

    # End index
    end_id = start_id + samples_per_5_min
    print(end_id)

    if end_id > data_length:
        end_id = data_length
        print(end_id)

    return start_id, end_id


def generate_night_images(patient_id, week, file, mr, ml, predictions):
    # Create output directory for plots
    downsampled_data_path = get_settings().downsampled_data_path
    emg_right_name = get_settings().emg_right_name  # 'MR'
    emg_left_name = get_settings().emg_left_name  # 'ML'
    minimum_sampling_rate = get_settings().minimum_sampling_rate  # 200

    output_dir = (
        f"{downsampled_data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv_images/"
    )

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    # Whole Night Plot
    sleep_cycle_step = 90 * 60  # Sleep cycle step in seconds
    sleep_cycles = math.ceil(
        len(mr) / (minimum_sampling_rate * 90 * 60)
    )  # Number of sleep cycles
    plt.figure(figsize=(25, 10))
    plt.title("Whole Night Signal")
    time_steps = np.linspace(0, len(mr) / minimum_sampling_rate, len(mr))

    plt.plot(time_steps, mr, color="blue", alpha=0.7, label=emg_right_name)
    plt.plot(time_steps, ml, color="red", alpha=0.5, label=emg_left_name)
    plt.axvline(x=0, color="black")

    j = sleep_cycle_step
    for i in range(sleep_cycles):
        plt.axvline(x=j, color="black")
        plt.text(j - 3000, max(mr + ml), f"Cycle {i + 1}")
        j += sleep_cycle_step

    # Mark events in the whole night plot
    position_flag = True
    for event in predictions:
        start_s = event.start_s
        end_s = event.end_s
        label = event.name

        if event.confirmed == True:
            # Mark the event area as a shaded rectangle
            plt.fill_betweenx(
                y=[min(mr + ml), max(mr + ml)],
                x1=start_s,
                x2=end_s,
                color="green",
                alpha=0.5,
            )

            # Alternate between top and bottom for labels
            y_pos = max(mr + ml) if position_flag else min(mr + ml)
            plt.text(
                (start_s + end_s) / 2,
                y_pos,
                label,
                fontsize=12,
                color="green",
                verticalalignment="top" if position_flag else "bottom",
                horizontalalignment="center",
            )
            position_flag = not position_flag

    plt.xlabel("Time [s]")
    plt.ylabel("Amplitude")
    plt.legend(loc="upper right")

    plt.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.1)

    plt.savefig(f"{output_dir}/whole_night_signal.png")  # Save the whole night plot
    plt.close()

    # Sleep Cycle Plots
    sleep_cycle_duration_s = 90 * 60  # Duration of one sleep cycle in seconds
    samples_per_cycle = (
        sleep_cycle_duration_s * minimum_sampling_rate
    )  # Total samples per sleep cycle

    start_x_axis = 0
    end_x_axis = sleep_cycle_duration_s
    # Generate individual plots for each sleep cycle
    for cycle in range(sleep_cycles):
        start_idx = int(cycle * samples_per_cycle)
        end_idx = int((cycle + 1) * samples_per_cycle)

        # Ensure the end index does not exceed the length of the signal
        if end_idx > len(mr):
            end_idx = len(mr)

        # Time steps for the current sleep cycle should go from 0 to 5400 seconds (90 minutes)
        time_steps_cycle = np.linspace(start_x_axis, end_x_axis, end_idx - start_idx)

        # Plot for the current sleep cycle
        plt.figure(figsize=(15, 5))
        plt.title(f"Sleep Cycle {cycle + 1}")
        plt.plot(
            time_steps_cycle, mr[start_idx:end_idx], color="blue", alpha=0.5, label="MR"
        )
        plt.plot(
            time_steps_cycle, ml[start_idx:end_idx], color="red", alpha=0.5, label="ML"
        )

        # Mark events in the sleep cycle plot
        position_flag = True
        for event in predictions:
            start_s = event.start_s
            end_s = event.end_s
            label = event.name

            if (
                start_s >= start_x_axis
                and end_s <= end_x_axis
                and event.confirmed == True
            ):
                # Mark the event area as a shaded rectangle
                plt.fill_betweenx(
                    y=[min(mr + ml), max(mr + ml)],
                    x1=start_s,
                    x2=end_s,
                    color="green",
                    alpha=0.2,
                )

                # Alternate between top and bottom for labels
                y_pos = max(mr + ml) if position_flag else min(mr + ml)
                plt.text(
                    (start_s + end_s) / 2,
                    y_pos,
                    label,
                    fontsize=12,
                    color="green",
                    verticalalignment="top" if position_flag else "bottom",
                    horizontalalignment="center",
                )
                position_flag = not position_flag

        plt.xlabel("Time [s]")
        plt.ylabel("Amplitude")
        plt.legend(loc="upper right")
        start_x_axis += sleep_cycle_duration_s
        end_x_axis += sleep_cycle_duration_s

        plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.15)

        plt.savefig(
            f"{output_dir}/sleep_cycle_{cycle + 1}.png"
        )  # Save the sleep cycle plot
        plt.close()


def append_features(continuous_features, row, mean=False):
    if mean:
        continuous_features["std_mr"].append(row["std_mr"][0])
        continuous_features["std_ml"].append(row["std_ml"][0])
        continuous_features["var_mr"].append(row["var_mr"][0])
        continuous_features["var_ml"].append(row["var_ml"][0])
        continuous_features["mnf_mr"].append(row["mnf_mr"][0])
        continuous_features["mnf_ml"].append(row["mnf_ml"][0])
        continuous_features["mdf_mr"].append(row["mdf_mr"][0])
        continuous_features["mdf_ml"].append(row["mdf_ml"][0])
        continuous_features["HRV_mean"].append(row["HRV_mean"][0])
        continuous_features["HRV_median"].append(row["HRV_median"][0])
        continuous_features["HRV_sdnn"].append(row["HRV_sdnn"][0])
        continuous_features["HRV_lf_hf"].append(row["HRV_lf_hf"][0])
        continuous_features["RRI"].append(row["RRI"][0])
    else:
        continuous_features["std_mr"].append(row["std_mr"])
        continuous_features["std_ml"].append(row["std_ml"])
        continuous_features["var_mr"].append(row["var_mr"])
        continuous_features["var_ml"].append(row["var_ml"])
        continuous_features["mnf_mr"].append(row["mnf_mr"])
        continuous_features["mnf_ml"].append(row["mnf_ml"])
        continuous_features["mdf_mr"].append(row["mdf_mr"])
        continuous_features["mdf_ml"].append(row["mdf_ml"])
        continuous_features["HRV_mean"].append(row["HRV_mean"])
        continuous_features["HRV_median"].append(row["HRV_median"])
        continuous_features["HRV_sdnn"].append(row["HRV_sdnn"])
        continuous_features["HRV_lf_hf"].append(row["HRV_lf_hf"])
        continuous_features["RRI"].append(row["RRI"])


def get_continuous_features(features, idx, data_length=None):
    start_time = 60 * 5 * idx
    end_time = start_time + 60 * 5
    print(start_time, end_time)

    filtered = features.filter(
        ((pl.col("start_time") >= start_time) | (pl.col("end_time") > start_time))
        & ((pl.col("end_time") <= end_time) | (pl.col("start_time") < end_time))
    )

    continuous_features = {
        "std_mr": [],
        "std_ml": [],
        "var_mr": [],
        "var_ml": [],
        "mnf_mr": [],
        "mnf_ml": [],
        "mdf_mr": [],
        "mdf_ml": [],
        "HRV_mean": [],
        "HRV_median": [],
        "HRV_sdnn": [],
        "HRV_lf_hf": [],
        "RRI": [],
    }
    count = 0
    if len(filtered) == 0:
        last_feature_row = features.row(len(features) - 1, named=True)
        for _ in range(data_length):
            append_features(continuous_features, last_feature_row)

    else:
        for row in filtered.rows(named=True):
            if count == 0 or count == len(filtered) - 1:
                for i in range(100):
                    append_features(continuous_features, row)

                if count == 0:
                    next = filtered.row(count + 1, named=True)
                    df_new = pl.DataFrame([row, next])
                    mean_rows = df_new.mean().to_dict(as_series=False)
                    for _ in range(100):
                        append_features(continuous_features, mean_rows, mean=True)

                if count == len(filtered) - 1:
                    print("check if smaller than rms mr: ")
                    len_last_signal_interval = data_length
                    len_continuous_feature_list = len(continuous_features["std_mr"])
                    # If this is the last 5 min intervals is important to make sure that the features length is the same as the data length
                    if len_last_signal_interval > len_continuous_feature_list:
                        missing = len_last_signal_interval - len_continuous_feature_list
                        for _ in range(missing):
                            append_features(continuous_features, row)
                    print(data_length)
                    print(len(continuous_features["std_mr"]))

            else:
                next = filtered.row(count + 1, named=True)
                df_new = pl.DataFrame([row, next])
                mean_rows = df_new.mean().to_dict(as_series=False)
                for _ in range(100):
                    append_features(continuous_features, mean_rows, mean=True)

            count += 1
    return continuous_features


def get_new_event_metrics(patient_id, week, file, start_s, end_s):
    print("take features from where the event locates")
    downsampled_data_path = get_settings().downsampled_data_path
    features = pl.read_csv(
        f"{downsampled_data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz_features.csv"
    )

    features_event = features.filter(
        ((pl.col("start_time") >= start_s) | (pl.col("end_time") > start_s))
        & ((pl.col("end_time") <= end_s) | (pl.col("start_time") < end_s))
    )
    print(features_event.mean()[:, 3:])
    features_event_mean = features_event.mean()[:, 2:]

    return features_event_mean


def add_new_prediction(
    patient_id,
    week,
    file,
    start_s,
    end_s,
    event_type,
    sensor,
    justification,
    name,
    metrics,
):
    new_prediction = EventPrediction(
        patient_id=patient_id,
        week=week,
        file=file,
        name=name,
        start_s=start_s,
        end_s=end_s,
        std_mr=metrics["std_mr"].item(),
        std_ml=metrics["std_ml"].item(),
        var_mr=metrics["var_mr"].item(),
        var_ml=metrics["var_ml"].item(),
        rms_mr=metrics["rms_mr"].item(),
        rms_ml=metrics["rms_ml"].item(),
        mav_mr=metrics["mav_mr"].item(),
        mav_ml=metrics["mav_ml"].item(),
        log_det_mr=metrics["log_det_mr"].item(),
        log_det_ml=metrics["log_det_ml"].item(),
        wl_mr=metrics["wl_mr"].item(),
        wl_ml=metrics["wl_ml"].item(),
        aac_mr=metrics["aac_mr"].item(),
        aac_ml=metrics["aac_ml"].item(),
        dasdv_mr=metrics["dasdv_mr"].item(),
        dasdv_ml=metrics["dasdv_ml"].item(),
        wamp_mr=metrics["wamp_mr"].item(),
        wamp_ml=metrics["wamp_ml"].item(),
        fr_mr=metrics["fr_mr"].item(),
        fr_ml=metrics["fr_ml"].item(),
        mnp_mr=metrics["mnp_mr"].item(),
        mnp_ml=metrics["mnp_ml"].item(),
        tot_mr=metrics["tot_mr"].item(),
        tot_ml=metrics["tot_ml"].item(),
        mnf_mr=metrics["mnf_mr"].item(),
        mnf_ml=metrics["mnf_ml"].item(),
        mdf_mr=metrics["mdf_mr"].item(),
        mdf_ml=metrics["mdf_ml"].item(),
        pkf_mr=metrics["pkf_mr"].item(),
        pkf_ml=metrics["pkf_ml"].item(),
        HRV_mean=metrics["HRV_mean"].item(),
        HRV_median=metrics["HRV_median"].item(),
        HRV_sdnn=metrics["HRV_sdnn"].item(),
        HRV_min=metrics["HRV_min"].item(),
        HRV_max=metrics["HRV_max"].item(),
        HRV_vhf=metrics["HRV_vhf"].item(),
        HRV_lf=metrics["HRV_lf"].item(),
        HRV_hf=metrics["HRV_hf"].item(),
        HRV_lf_hf=metrics["HRV_lf_hf"].item(),
        RRI=metrics["RRI"].item(),
        y_prob=1.00,
        confirmed=True,
        sensor=sensor,
        event_type=event_type,
        status="new",
        justification=justification,
    )

    db.session.add(new_prediction)
    db.session.commit()


# Prediction functions
def calculate_hrv(ecg_90s):
    try:
        ecg_clean = nk.ecg_clean(ecg_90s, sampling_rate=200)
        ecg_peaks = nk.ecg_findpeaks(ecg_clean, sampling_rate=200)
        info, r_peaks_corrected = nk.signal_fixpeaks(
            ecg_peaks, sampling_rate=200, iterative=False, show=False, method="Kubios"
        )
        hrv = nk.hrv(r_peaks_corrected, sampling_rate=200, show=False)
        mean = hrv["HRV_MeanNN"][0]
        median = hrv["HRV_MedianNN"][0]
        sdnn = hrv["HRV_SDNN"][0]
        min = hrv["HRV_MinNN"][0]
        max = hrv["HRV_MaxNN"][0]
        vhf = hrv["HRV_VHF"][0]
        lf = hrv["HRV_LF"][0]
        hf = hrv["HRV_HF"][0]
        lf_hf = hrv["HRV_LFHF"][0]

        return mean, median, sdnn, min, max, vhf, lf, hf, lf_hf
    except:
        return np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan


def next_power_of_2(x):
    return 1 if x == 0 else 2 ** (x - 1).bit_length()


def spectrum(signal, sampling_rate):
    m = len(signal)
    n = next_power_of_2(m)
    y = np.fft.fft(signal, n)
    yh = y[0 : int(n / 2 - 1)]
    fh = (sampling_rate / n) * np.arange(0, n / 2 - 1, 1)
    power = np.real(yh * np.conj(yh) / n)

    return fh, power


def frequency_ratio(frequency, power):
    power_low = power[(frequency >= 1) & (frequency <= 30)]  # Low range: 1-30 Hz
    power_high = power[
        (frequency > 30) & (frequency <= 100)
    ]  # High range: 30-100 Hz (up to Nyquist)

    ULC = np.sum(power_low)
    UHC = np.sum(power_high)

    # Avoid division by zero in case the high-frequency power is 0
    if UHC == 0:
        return np.nan  # Return infinity or handle it as appropriate
    else:
        return ULC / UHC


def mean_freq(frequency, power):
    num = 0
    den = 0
    for i in range(int(len(power) / 2)):
        num += frequency[i] * power[i]
        den += power[i]

    if den == 0:
        return np.nan
    else:
        return num / den


def median_freq(frequency, power):
    power_total = np.sum(power) / 2
    temp = 0
    tol = 0.01
    errel = 1
    i = 0
    try:
        while abs(errel) > tol:
            temp += power[i]
            errel = (power_total - temp) / power_total
            i += 1
            if errel < 0:
                errel = 0
                i -= 1

        return frequency[i]
    except:
        return np.nan


def peak_freq(frequency, power):
    try:
        return frequency[power.argmax()]

    except:
        return np.nan


def get_rri(ecg, sampling_rate=200):
    ecg_clean = nk.ecg_clean(ecg, sampling_rate=sampling_rate)
    ecg_peaks = nk.ecg_findpeaks(ecg_clean, sampling_rate=sampling_rate)
    info, r_peaks_corrected = nk.signal_fixpeaks(
        ecg_peaks,
        sampling_rate=sampling_rate,
        iterative=False,
        show=False,
        method="Kubios",
    )

    # Calculate RR intervals
    rr_intervals = np.diff(r_peaks_corrected) / sampling_rate * 1000

    # Insert fake data point
    rr_intervals_adjusted = np.insert(rr_intervals, 0, rr_intervals[0])

    # Calculate time axis
    time_r_peaks = (
        r_peaks_corrected[1:] / sampling_rate
    )  # Time corresponding to the RR intervals
    time_r_peaks_adjusted = np.insert(
        time_r_peaks, 0, 0
    )  # Add a time point for the fake interval
    print(time_r_peaks[0])

    rri_adj_df = pd.DataFrame(
        data={"RRI": rr_intervals_adjusted, "RRI_t": time_r_peaks_adjusted}
    )

    return rri_adj_df


# Function to populate the RRI column in df_sliding
def extend_df_with_rri(df_sliding, df_rr):
    # Create a new column to store RR intervals
    df_sliding["RRI"] = np.nan  # Placeholder for the new RR interval column

    rri_index = 0  # Pointer for the df_rr
    total_rr_rows = len(df_rr)

    for idx in range(len(df_sliding)):
        # Get the current start time of the sliding window
        window_start = df_sliding.at[idx, "start_time"]

        # Update the RRI value until we reach the next RRI_t
        while (
            rri_index < total_rr_rows and df_rr.at[rri_index, "RRI_t"] <= window_start
        ):
            # Populate the RRI value for this window
            df_sliding.at[idx, "RRI"] = df_rr.at[rri_index, "RRI"]
            rri_index += 1

        # If we have reached the end of RRI DataFrame, we can break
        if rri_index >= total_rr_rows:
            break

    # Fill any remaining NaN values in the RRI column with the last known value
    df_sliding["RRI"].fillna(method="ffill", inplace=True)

    return df_sliding


def extract_features_for_prediction(
    sensor_data,
    window_size_emg_s=1,
    overlap_emg_s=0.5,
    window_size_ecg_s=90,
    overlap_ecg_s=45,
    sampling_rate=200,
):
    emg_right_name = get_settings().emg_right_name  # 'MR'
    emg_left_name = get_settings().emg_left_name  # 'ML'
    ecg_name = get_settings().ecg_name  # 'ECG

    minimum_sampling_rate = get_settings().minimum_sampling_rate

    window_size_emg = int(window_size_emg_s * sampling_rate)
    window_size_ecg = int(window_size_ecg_s * sampling_rate)
    overlap_emg = int(overlap_emg_s * sampling_rate)
    overlap_ecg = int(overlap_ecg_s * sampling_rate)

    features_1s = []
    features_90s = []

    scaler_mr = MinMaxScaler(feature_range=(0, 100))
    scaler_ml = MinMaxScaler(feature_range=(0, 100))

    ecg_data = sensor_data[ecg_name].values
    mr_data = pd.DataFrame(
        scaler_mr.fit_transform(sensor_data[[emg_right_name]]), columns=[emg_right_name]
    )[emg_right_name].values
    ml_data = pd.DataFrame(
        scaler_ml.fit_transform(sensor_data[[emg_left_name]]), columns=[emg_left_name]
    )[emg_left_name].values

    mr_threshold = np.mean(mr_data) + 3 * np.std(mr_data)
    ml_threshold = np.mean(ml_data) + 3 * np.std(ml_data)

    print("seconds: ", len(sensor_data) / minimum_sampling_rate)

    for i in range(window_size_emg, len(sensor_data), overlap_emg):

        # Extract the 1-second window
        mr_window = mr_data[i - window_size_emg : i]
        ml_window = ml_data[i - window_size_emg : i]

        # Standard Deviation
        std_mr = np.std(mr_window)
        std_ml = np.std(ml_window)

        # Variance
        var_mr = np.var(mr_window)
        var_ml = np.var(ml_window)

        # RMS
        rms_mr = np.sqrt(np.mean(mr_window**2))
        rms_ml = np.sqrt(np.mean(ml_window**2))

        # Mean Absolute Value
        mav_mr = np.mean(np.abs(mr_window))
        mav_ml = np.mean(np.abs(ml_window))

        # Log detector
        log_det_mr = np.mean(np.log(np.maximum(np.absolute(mr_window), 1e-10)))
        log_det_ml = np.mean(np.log(np.maximum(np.absolute(ml_window), 1e-10)))

        # Wavelength
        wl_mr = np.sum(abs(np.diff(mr_window)))
        wl_ml = np.sum(abs(np.diff(ml_window)))

        # Average Amplitude Change
        aac_mr = np.mean(np.abs(np.diff(mr_window)))
        aac_ml = np.mean(np.abs(np.diff(ml_window)))

        # Difference absolute standard deviation value
        dasdv_mr = math.sqrt(
            (1 / (window_size_emg - 1)) * np.sum((np.diff(mr_window)) ** 2)
        )
        dasdv_ml = math.sqrt(
            (1 / (window_size_emg - 1)) * np.sum((np.diff(ml_window)) ** 2)
        )

        # Willison Amplitude
        wamp_mr = np.sum(np.abs(np.diff(mr_window)) > mr_threshold)
        wamp_ml = np.sum(np.abs(np.diff(ml_window)) > ml_threshold)

        frequency_mr, power_mr = spectrum(mr_window, sampling_rate)
        frequency_ml, power_ml = spectrum(ml_window, sampling_rate)

        # Frequency Ratio
        fr_mr = frequency_ratio(frequency_mr, power_mr)
        fr_ml = frequency_ratio(frequency_mr, power_mr)

        # Mean power
        mnp_mr = np.sum(power_mr) / len(power_mr)
        mnp_ml = np.sum(power_ml) / len(power_ml)

        # Total power
        tot_mr = np.sum(power_mr)
        tot_ml = np.sum(power_ml)

        # Mean Frequency
        mnf_mr = mean_freq(frequency_mr, power_mr)
        mnf_ml = mean_freq(frequency_ml, power_ml)

        # Median frequency
        mdf_mr = median_freq(frequency_mr, power_mr)
        mdf_ml = median_freq(frequency_ml, power_ml)

        # Peak frequency
        pkf_mr = peak_freq(frequency_mr, power_mr)
        pkf_ml = peak_freq(frequency_ml, power_ml)

        start_time = (i - window_size_emg) / sampling_rate
        end_time = i / sampling_rate

        current_features = [
            start_time,
            end_time,
            std_mr,
            std_ml,
            var_mr,
            var_ml,
            rms_mr,
            rms_ml,
            mav_mr,
            mav_ml,
            log_det_mr,
            log_det_ml,
            wl_mr,
            wl_ml,
            aac_mr,
            aac_ml,
            dasdv_mr,
            dasdv_ml,
            wamp_mr,
            wamp_ml,
            fr_mr,
            fr_ml,
            mnp_mr,
            mnp_ml,
            tot_mr,
            tot_ml,
            mnf_mr,
            mnf_ml,
            mdf_mr,
            mdf_ml,
            pkf_mr,
            pkf_ml,
        ]
        features_1s.append(current_features)

    for i in range(window_size_ecg, len(ecg_data), overlap_ecg):
        # Extract 90 seconds of ECG data
        window_90s = ecg_data[i - window_size_ecg : i]  # 90-second window

        mean, median, sdnn, min, max, vhf, lf, hf, lf_hf = calculate_hrv(window_90s)

        num_1s_windows_in_90s = window_size_ecg // window_size_emg
        for _ in range(num_1s_windows_in_90s):
            features_90s.append([mean, median, sdnn, min, max, vhf, lf, hf, lf_hf])

    combined_features = [
        f1 + f41 for f1, f41 in zip(features_1s, features_90s[: len(features_1s)])
    ]

    columns = [
        "start_time",
        "end_time",
        "std_mr",
        "std_ml",
        "var_mr",
        "var_ml",
        "rms_mr",
        "rms_ml",
        "mav_mr",
        "mav_ml",
        "log_det_mr",
        "log_det_ml",
        "wl_mr",
        "wl_ml",
        "aac_mr",
        "aac_ml",
        "dasdv_mr",
        "dasdv_ml",
        "wamp_mr",
        "wamp_ml",
        "fr_mr",
        "fr_ml",
        "mnp_mr",
        "mnp_ml",
        "tot_mr",
        "tot_ml",
        "mnf_mr",
        "mnf_ml",
        "mdf_mr",
        "mdf_ml",
        "pkf_mr",
        "pkf_ml",
        "HRV_mean",
        "HRV_median",
        "HRV_sdnn",
        "HRV_min",
        "HRV_max",
        "HRV_vhf",
        "HRV_lf",
        "HRV_hf",
        "HRV_lf_hf",
    ]

    features = pd.DataFrame(combined_features, columns=columns)

    rri = get_rri(ecg_data)
    features_rri = extend_df_with_rri(features, rri)

    return features_rri


def aggregate_events(df):
    events = {}  # Dictionary to store the events
    event_counter = 1

    # Initialize variables for aggregation
    current_event_start = None
    current_event_end = None
    current_event_features = []  # To collect feature values
    current_event_y_probs = []  # To collect y_prob values
    current_event_y_values = []  # To collect y values
    # current_event_confirmed_values = []

    # Use a for loop to iterate over the DataFrame rows
    for index, row in df.iterrows():
        # Check if we are starting a new event
        if current_event_start is None:
            # Initialize the first event
            current_event_start = row["start_time"]
            current_event_end = row["end_time"]
            current_event_features.append(row[2:-2].values)  # Collect feature values
            current_event_y_probs.append(row["y_prob"])  # Collect y_prob
            current_event_y_values.append(row["y"])  # Collect y
            continue

        # Check if the current row is part of the same event
        # Use index to find the previous row's index for continuity check
        previous_index = df.index[df.index.get_loc(index) - 1]
        if index == previous_index + 1:
            # Update the current event's end time and features
            current_event_end = row["end_time"]
            current_event_features.append(row[2:-2].values)  # Append features
            current_event_y_probs.append(row["y_prob"])  # Append y_prob
            current_event_y_values.append(row["y"])  # Append y
        else:
            # Save the current event to the events dictionary
            if current_event_start is not None:
                # Calculate means for features and y_prob
                feature_means = {
                    col: np.mean([f[i] for f in current_event_features])
                    for i, col in enumerate(
                        df.columns[2:-2]
                    )  # Features are from index 2 to -2 (excluding y)
                }
                y_prob_mean = (
                    np.mean(current_event_y_probs) if current_event_y_probs else 0
                )

                events[f"e{event_counter}"] = {
                    "start_s": current_event_start,
                    "end_s": current_event_end,
                    "duration": current_event_end - current_event_start,
                    **feature_means,
                    "y": current_event_y_values[
                        -1
                    ],  # Retain the last y value for the current event
                    "y_prob": y_prob_mean,  # Include the mean of y_prob
                    "confirmed": True,
                }
                event_counter += 1

            # Reset for the new event
            current_event_start = row["start_time"]
            current_event_end = row["end_time"]
            current_event_features = [row[2:-2].values]  # Start new collection
            current_event_y_probs = [row["y_prob"]]  # Start new collection
            current_event_y_values = [row["y"]]  # Start new collection
            # current_event_confirmed_values = [row['confirmed']]

    # Finalize the last event if it exists
    if current_event_start is not None:
        feature_means = {
            col: np.mean([f[i] for f in current_event_features])
            for i, col in enumerate(
                df.columns[2:-2]
            )  # Features are from index 2 to -2 (excluding y)
        }
        y_prob_mean = np.mean(current_event_y_probs) if current_event_y_probs else 0

        events[f"e{event_counter}"] = {
            "start_s": current_event_start,
            "end_s": current_event_end,
            "duration": current_event_end - current_event_start,
            **feature_means,
            "y": current_event_y_values[
                -1
            ],  # Retain the last y value for the current event
            "y_prob": y_prob_mean,  # Include the mean of y_prob
            "confirmed": True,
        }

    return events
