import polars as pl
import pandas as pd
import neurokit2 as nk
import numpy as np
import os
import re
from collections import defaultdict
import datetime
from .models import NightDuration, MVC, db
import math

data_path = 'C:/Users/eleon/Desktop/SDAP/backend/src/data/'

def read_data_csv(p, w, f, cols):
    data = pl.read_csv(data_path + f'p{p}_wk{w}/{f}', columns=cols)

    return data

def read_loc_csv(p, w, f):
    f_short = f.rsplit('Fnorm.csv', 1)[0]
    loc = pl.read_csv(data_path + f'p{p}_wk{w}/{f_short}location_Bites.csv')

    return loc


"""
def get_interval_from_csv(data, interval_index, sampling_rate=2000, interval_duration=5*60):

    Extracts a specific 5-minute interval from a CSV file containing EMG data using Polars.

    Parameters:
    - file_path (str): Path to the CSV file.
    - interval_index (int): Index of the 5-minute interval to retrieve (0-based).
    - sampling_rate (int): Sampling rate of the data in Hz.
    - interval_duration (int): Duration of the interval in seconds (default is 5 minutes).

    Returns:
    - pl.DataFrame: Polars DataFrame containing the data for the specified 5-minute interval.

    # Calculate the number of samples per interval
    samples_per_interval = sampling_rate * interval_duration

    # Load the data from the CSV file
    data = data
    num_samples = len(data)

    # Calculate the number of intervals
    num_intervals = (num_samples + samples_per_interval - 1) // samples_per_interval  # Ceiling division

    # Print the number of 5-minute intervals
    print(f"Total number of 5-minute intervals: {num_intervals}")

    # Validate the interval_index
    if interval_index < 0 or interval_index >= num_intervals:
        raise ValueError(f"Invalid interval_index. Must be between 0 and {num_intervals - 1}.")

    # Calculate the start and end indices of the requested interval
    start_index = interval_index * samples_per_interval
    end_index = min(start_index + samples_per_interval, num_samples)

    # Extract the interval data
    interval_data = data.slice(start_index, end_index - start_index)

    return interval_data, start_index, end_index
"""

def rectify_signal(signal):
    return np.abs(signal)


def rms(emg_signal, sampling=2000, window=0.06, min_periods=1):
    # Define a window size (in number of samples)
    # 60-120 ms?
    window_size = int(window*sampling)

    # Compute RMS with a rolling window
    signal_rms = emg_signal.rolling(window=window_size, min_periods=min_periods).apply(lambda x: np.sqrt(np.mean(x**2)), raw=True)

    # Check the output size
    print(f"Original signal length: {len(emg_signal)}")
    print(f"RMS signal length: {len(signal_rms)}")

    return signal_rms

def fast_rms(signal, sampling=2000, window=0.06):
    window_size = int(window*sampling)

    # Square the signal
    squared_signal = np.square(signal)
    
    # Compute the rolling mean of the squared signal
    rolling_mean = pd.Series(squared_signal).rolling(window=window_size, min_periods=1).mean()
    
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

        # TODO: check if average of ML and MR max row is okay
        # max_in_bite_avg = (max_in_bite['MR'][0] + max_in_bite['ML'][0]) / 2

        if float(signal_max_in_bite) > float(signal_mvc):
            signal_mvc = signal_max_in_bite

        return signal_mvc
    

def downsample_data(signal, desired_sampling, original_sampling=2000, method="interpolation"):
    return nk.signal_resample(signal, sampling_rate=original_sampling, desired_sampling_rate=desired_sampling, method=method)


def parse_data_structure(base_dir):
    data_dict = defaultdict(lambda: defaultdict(list))
    
    # Match folder names (e.g., p1_wk1, p1_wk3-4)
    folder_pattern = re.compile(r'^(p\d+)_wk(\d+(-\d+)?)$')

    for root, dirs, files in os.walk(base_dir):
        for dir_name in dirs:
            match = folder_pattern.match(dir_name)
            if match:
                patient_id = match.group(1)[1:]
                week_id = match.group(2)
                # Collect files in directory
                folder_path = os.path.join(root, dir_name)
                night_files = [
                    f for f in os.listdir(folder_path) 
                    if f.endswith('.csv') and not f.endswith('location_Bites.csv')
                ]
                
                for file_name in night_files:
                    file_path = os.path.join(folder_path, file_name)
                    
                    # Calculate file size in GB
                    file_size_bytes = os.path.getsize(file_path)
                    file_size_gb = file_size_bytes / (1024 ** 3)

                    data_dict[patient_id][week_id].append({
                        'file_name': file_name,
                        'size_gb': round(file_size_gb, 2),  # Rounded to 4 decimal places
                    })

    return dict(data_dict)


def sort_week_key(week):
    """Extract numerical parts of the week to enable correct sorting."""
    # Find all numeric parts of the week identifier (e.g., "13-14" becomes [13, 14])
    numbers = list(map(int, re.findall(r'\d+', week)))
    return numbers[0], numbers[-1]  # Sort by the first number, then by the last number if range exists


def sort_data_structure(data_dict):
    sorted_dict = {}
    
    for patient, weeks in data_dict.items():
        # Sort weeks using the custom key
        sorted_weeks = dict(sorted(weeks.items(), key=lambda x: sort_week_key(x[0])))
        sorted_dict[patient] = sorted_weeks
    
    return sorted_dict


def calculate_night_duration(patient_id, week, file_name, file_length, sampling_rate):
    seconds = file_length / sampling_rate
    duration = datetime.timedelta(seconds = seconds)

    nigh_duration = NightDuration.query.filter_by(patient_id=patient_id, week=week, file=file_name, seconds=seconds, duration=duration).first()

    if nigh_duration is None:
        # TODO: insert duration in DB
        night_duration = NightDuration(patient_id=patient_id, week=week, file=file_name, seconds=seconds, duration=duration)

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



def preprocess_and_downsample_emg(patient_id, week, filename, df, loc, seconds, new_sampling_rate=256):
    print("in preprocess_and downample function")
    mr = pd.Series(df['MR'].to_list())
    ml = pd.Series(df['ML'].to_list())

    mr_rect = rectify_signal(mr)
    ml_rect = rectify_signal(ml)

    mr_rms = fast_rms(mr_rect)
    ml_rms = fast_rms(ml_rect)

    mr_mvc = find_mvc(mr_rms, loc)
    ml_mvc = find_mvc(ml_rms, loc)

    print(mr_mvc)
    print(type(mr_mvc))

    mr_mvc_db = MVC(patient_id=patient_id, week=week, file=filename, sensor='MR', mvc=mr_mvc.item())
    ml_mvc_db = MVC(patient_id=patient_id, week=week, file=filename, sensor='ML', mvc=ml_mvc.item())

    db.session.add(mr_mvc_db)
    db.session.add(ml_mvc_db)

    db.session.commit()

    mr_downsampled = downsample_data(mr_rms, desired_sampling=new_sampling_rate)
    ml_downsampled = downsample_data(ml_rms, desired_sampling=new_sampling_rate)

    print(len(mr_downsampled))

    #emg_time = np.linspace(0, seconds, int(seconds * new_sampling_rate), endpoint=False)  # Time vector

    print(f"mr: {len(mr_downsampled.tolist())}")
    print(f"mr: {len(mr_downsampled.tolist())}")

    #result = pd.DataFrame(data={'MR': mr_downsampled.tolist(), 'ML': ml_downsampled.tolist(), 'EMG_t': emg_time.tolist()})
    result = pd.DataFrame(data={'MR': mr_downsampled.tolist(), 'ML': ml_downsampled.tolist()})
    print(result)

    path = f"C:/Users/eleon/Desktop/SDAP/backend/src/data_resampled/p{patient_id}_wk{week}"
    if not os.path.exists(path):
        print("not exist")
        os.makedirs(path)
    result.to_csv(path + f'/{filename}_emg_{new_sampling_rate}Hz.csv')



def get_5_min_emg(df, seconds):
    mr = pd.Series(df['MR'].to_list())
    ml = pd.Series(df['ML'].to_list())

    emg_time = np.linspace(0, seconds, int(seconds * 256), endpoint=False)  # Time vector

    print(f"len mr: {len(mr.tolist())}")
    print(f"len ml: {len(ml.tolist())}")
    print(f"len time: {len(emg_time.tolist())}")

    result = {'MR': mr.tolist(), 'ML': ml.tolist(), 'EMG_t': emg_time.tolist()}

    return result

# Prediction functions
def calculate_hrv(ecg_90s):
    try:
        ecg_clean = nk.ecg_clean(ecg_90s, sampling_rate=200)
        ecg_peaks = nk.ecg_findpeaks(ecg_clean, sampling_rate=200)
        info, r_peaks_corrected = nk.signal_fixpeaks(ecg_peaks, sampling_rate=200, iterative=False, show=False, method="Kubios")
        hrv = nk.hrv(r_peaks_corrected,sampling_rate=200, show=False)
        mean = hrv["HRV_MeanNN"][0]
        median = hrv["HRV_MedianNN"][0]
        sdnn = hrv["HRV_SDNN"][0]
        min = hrv["HRV_MinNN"][0]
        max = hrv["HRV_MaxNN"][0]
        vlf = hrv["HRV_VLF"][0]
        vhf = hrv["HRV_VHF"][0]
        lf = hrv["HRV_LF"][0]
        hf = hrv["HRV_HF"][0]
        lf_hf = hrv["HRV_LFHF"][0]


        return mean, median, sdnn, min, max, vlf, vhf, lf, hf, lf_hf
    except:
        return np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan

def next_power_of_2(x):
    return 1 if x == 0 else 2 ** (x - 1).bit_length()

def spectrum(signal, sampling_rate):
    m = len(signal)
    n = next_power_of_2(m)
    y = np.fft.fft(signal, n)
    yh = y[0:int(n / 2 - 1)]
    fh = (sampling_rate / n) * np.arange(0, n / 2 - 1, 1)
    power = np.real(yh * np.conj(yh) / n)

    return fh, power


def frequency_ratio(frequency, power):
    power_low = power[(frequency >= 1) & (frequency <= 30)]  # Low range: 1-30 Hz
    power_high = power[(frequency > 30) & (frequency <= 100)]  # High range: 30-100 Hz (up to Nyquist)

    ULC = np.sum(power_low)
    UHC = np.sum(power_high)

    # Avoid division by zero in case the high-frequency power is 0
    if UHC == 0:
        return np.inf  # Return infinity or handle it as appropriate
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


def get_rri(ecg, sampling_rate=2000):
    ecg_clean = nk.ecg_clean(ecg, sampling_rate=sampling_rate)
    ecg_peaks = nk.ecg_findpeaks(ecg_clean, sampling_rate=sampling_rate)
    info, r_peaks_corrected = nk.signal_fixpeaks(ecg_peaks, sampling_rate=sampling_rate, iterative=False, show=False, method="Kubios")

    # Calculate RR intervals
    rr_intervals = np.diff(r_peaks_corrected) / sampling_rate * 1000

    # Insert fake data point
    rr_intervals_adjusted = np.insert(rr_intervals, 0, rr_intervals[0])

    # Calculate time axis
    time_r_peaks = r_peaks_corrected[1:] / sampling_rate  # Time corresponding to the RR intervals
    time_r_peaks_adjusted = np.insert(time_r_peaks, 0, 0)  # Add a time point for the fake interval
    print(time_r_peaks[0])

    rri_adj_df = pd.DataFrame(data={'RRI': rr_intervals_adjusted, 'RRI_t': time_r_peaks_adjusted})

    return rri_adj_df

# Function to populate the RRI column in df_sliding
def extend_df_with_rri(df_sliding, df_rr):
    # Create a new column to store RR intervals
    df_sliding['RRI'] = np.nan  # Placeholder for the new RR interval column
    
    rri_index = 0  # Pointer for the df_rr
    total_rr_rows = len(df_rr)

    for idx in range(len(df_sliding)):
        # Get the current start time of the sliding window
        window_start = df_sliding.at[idx, 'start_time']
        
        # Update the RRI value until we reach the next RRI_t
        while rri_index < total_rr_rows and df_rr.at[rri_index, 'RRI_t'] <= window_start:
            # Populate the RRI value for this window
            df_sliding.at[idx, 'RRI'] = df_rr.at[rri_index, 'RRI']
            rri_index += 1
        
        # If we have reached the end of RRI DataFrame, we can break
        if rri_index >= total_rr_rows:
            break
    
    # Fill any remaining NaN values in the RRI column with the last known value
    df_sliding['RRI'].fillna(method='ffill', inplace=True)
    
    return df_sliding


def extract_features_for_prediction(sensor_data, window_size_emg_s=1, overlap_emg_s=0.5, window_size_ecg_s=90, overlap_ecg_s=45, sampling_rate=200):
    window_size_emg = int(window_size_emg_s * sampling_rate)
    window_size_ecg = int(window_size_ecg_s * sampling_rate)
    overlap_emg = int(overlap_emg_s * sampling_rate)
    overlap_ecg = int(overlap_ecg_s * sampling_rate)

    features_1s = []
    features_90s = []

    ecg_data = sensor_data['ECG'].values
    mr_data = sensor_data["MR"].values
    ml_data = sensor_data["ML"].values
    
    mr_threshold = np.mean(mr_data) + 3 * np.std(mr_data)
    ml_threshold = np.mean(ml_data) + 3 * np.std(ml_data)

    for i in range(window_size_emg, len(sensor_data), overlap_emg):

        # Extract the 1-second window
        mr_window = mr_data[i-window_size_emg:i]
        ml_window = ml_data[i-window_size_emg:i]

        # Standard Deviation
        std_mr = np.std(mr_window)
        std_ml = np.std(ml_window)

        # Variance
        var_mr = np.var(mr_window)
        var_ml = np.var(ml_window)

        # RMS
        rms_mr = np.sqrt(np.mean(mr_window ** 2))
        rms_ml = np.sqrt(np.mean(ml_window ** 2))

        # Mean Absolute Value
        mav_mr = np.mean(np.abs(mr_window))
        mav_ml = np.mean(np.abs(ml_window))

        # Log detector
        log_det_mr = np.mean(np.log(np.absolute(mr_window)))
        log_det_ml = np.mean(np.log(np.absolute(ml_window)))

        # Wavelength
        wl_mr = np.sum(abs(np.diff(mr_window)))
        wl_ml = np.sum(abs(np.diff(ml_window)))

        # Average Amplitude Change
        aac_mr = np.mean(np.abs(np.diff(mr_window)))
        aac_ml = np.mean(np.abs(np.diff(ml_window)))

        # Difference absolute standard deviation value
        dasdv_mr = math.sqrt((1 / (window_size_emg - 1)) * np.sum((np.diff(mr_window)) ** 2))
        dasdv_ml = math.sqrt((1 / (window_size_emg - 1)) * np.sum((np.diff(ml_window)) ** 2))

        # Zero Crossing Rate
        zc_mr = np.sum((mr_window[:-1] * mr_window[1:]) < 0) 
        zc_ml = np.sum((ml_window[:-1] * ml_window[1:]) < 0) 

        # Willison Amplitude
        wamp_mr = np.sum(np.abs(np.diff(mr_window)) > mr_threshold)
        wamp_ml = np.sum(np.abs(np.diff(ml_window)) > ml_threshold)

        frequency_mr, power_mr = spectrum(mr_window, sampling_rate)
        frequency_ml, power_ml = spectrum(ml_window, sampling_rate)
        
        # Frequency power
        fr_mr =frequency_ratio(frequency_mr, power_mr) 
        fr_ml =frequency_ratio(frequency_mr, power_mr)

        # Mean power
        mnp_mr = np.sum(power_mr) / len(power_mr)
        mnp_ml = np.sum(power_ml) / len(power_ml)

        
        # Total power
        tot_mr = np.sum(power_mr)
        tot_ml = np.sum(power_ml)

        #Mean Frequency
        mnf_mr = mean_freq(frequency_mr, power_mr)
        mnf_ml = mean_freq(frequency_ml, power_ml)

        # Median frequency
        mdf_mr = median_freq(frequency_mr, power_mr)
        mdf_ml = median_freq(frequency_ml, power_ml)

        # Peak frequency
        pkf_mr = peak_freq(frequency_mr, power_mr)
        pkf_ml = peak_freq(frequency_ml, power_ml)

        start_time = (i-window_size_emg) / sampling_rate
        end_time = i / sampling_rate
        
        current_features = [start_time, end_time, std_mr, std_ml, var_mr, var_ml, rms_mr, rms_ml, mav_mr, mav_ml, log_det_mr, log_det_ml, wl_mr, wl_ml, aac_mr, aac_ml, dasdv_mr, dasdv_ml, zc_mr, zc_ml, wamp_mr, wamp_ml, fr_mr, fr_ml, mnp_mr, mnp_ml, tot_mr, tot_ml, mnf_mr, mnf_ml, mdf_mr, mdf_ml, pkf_mr, pkf_ml]
        features_1s.append(current_features)
    

        if i % 10000000 == 0:
            print(f"i: {i}")

    for i in range(window_size_ecg, len(ecg_data), overlap_ecg):
        # Extract 90 seconds of ECG data
        window_90s = ecg_data[i - window_size_ecg:i]  # 90-second window

        mean, median, sdnn, min, max, vlf, vhf, lf, hf, lf_hf = calculate_hrv(window_90s)

        num_1s_windows_in_90s = window_size_ecg // window_size_emg
        for _ in range(num_1s_windows_in_90s):
            features_90s.append([mean, median, sdnn, min, max, vlf, vhf, lf, hf, lf_hf])


    combined_features = [f1 + f44 for f1, f44 in zip(features_1s, features_90s[:len(features_1s)])]

    columns = ["start_time", "end_time", "std_mr", "std_ml", "var_mr", "var_ml", "rms_mr",
               "rms_ml", "mav_mr", "mav_ml", "log_det_mr", "log_det_ml", "wl_mr", "wl_ml",
               "aac_mr", "aac_ml", "dasdv_mr", "dasdv_ml", "zc_mr", "zc_ml", "wamp_mr",
               "wamp_ml", "fr_mr", "fr_ml", "mnp_mr", "mnp_ml", "tot_mr", "tot_ml", "mnf_mr",
               "mnf_ml", "mdf_mr", "mdf_ml", "pkf_mr", "pkf_ml", "HRV_mean", "HRV_median", 
               "HRV_sdnn", "HRV_min", "HRV_max", "HRV_vlf", "HRV_vhf", "HRV_lf", "HRV_hf", "HRV_lf_hf"]
    
    features = pd.DataFrame(combined_features, columns=columns)

    rri = get_rri(ecg_data)
    features_rri = extend_df_with_rri(features, rri)
    

    return features_rri



import pandas as pd
import numpy as np

def aggregate_events(df):
    events = {}  # Dictionary to store the events
    event_counter = 1 

    # Initialize variables for aggregation
    current_event_start = None
    current_event_end = None
    current_event_features = []  # To collect feature values
    current_event_y_probs = []    # To collect y_prob values
    current_event_y_values = []    # To collect y values

    # Use a for loop to iterate over the DataFrame rows
    for index, row in df.iterrows():
        # Check if we are starting a new event
        if current_event_start is None:
            # Initialize the first event
            current_event_start = row['start_time']
            current_event_end = row['end_time']
            current_event_features.append(row[2:-2].values)  # Collect feature values
            current_event_y_probs.append(row['y_prob'])  # Collect y_prob
            current_event_y_values.append(row['y'])  # Collect y
            continue

        # Check if the current row is part of the same event
        # Use index to find the previous row's index for continuity check
        previous_index = df.index[df.index.get_loc(index) - 1]
        if index == previous_index + 1:
            # Update the current event's end time and features
            current_event_end = row['end_time']
            current_event_features.append(row[2:-2].values)  # Append features
            current_event_y_probs.append(row['y_prob'])  # Append y_prob
            current_event_y_values.append(row['y'])  # Append y
        else:
            # Save the current event to the events dictionary
            if current_event_start is not None:
                # Calculate means for features and y_prob
                feature_means = {
                    col: np.mean([f[i] for f in current_event_features]) 
                    for i, col in enumerate(df.columns[2:-2])  # Features are from index 2 to -2 (excluding y)
                }
                y_prob_mean = np.mean(current_event_y_probs) if current_event_y_probs else 0
                
                events[f"e{event_counter}"] = {
                    "start_s": current_event_start,
                    "end_s": current_event_end,
                    "duration": current_event_end - current_event_start,
                    **feature_means,
                    "y": current_event_y_values[-1],  # Retain the last y value for the current event
                    "y_prob": y_prob_mean  # Include the mean of y_prob
                }
                event_counter += 1
            
            # Reset for the new event
            current_event_start = row['start_time']
            current_event_end = row['end_time']
            current_event_features = [row[2:-2].values]  # Start new collection
            current_event_y_probs = [row['y_prob']]  # Start new collection
            current_event_y_values = [row['y']]  # Start new collection

    # Finalize the last event if it exists
    if current_event_start is not None:
        feature_means = {
            col: np.mean([f[i] for f in current_event_features]) 
            for i, col in enumerate(df.columns[2:-2])  # Features are from index 2 to -2 (excluding y)
        }
        y_prob_mean = np.mean(current_event_y_probs) if current_event_y_probs else 0
        
        events[f"e{event_counter}"] = {
            "start_s": current_event_start,
            "end_s": current_event_end,
            "duration": current_event_end - current_event_start,
            **feature_means,
            "y": current_event_y_values[-1],  # Retain the last y value for the current event
            "y_prob": y_prob_mean  # Include the mean of y_prob
        }

    return events





