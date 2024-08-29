import polars as pl
import pandas as pd
import neurokit2 as nk
import numpy as np
import os
import re
from collections import defaultdict

data_path = 'C:/Users/eleon/Desktop/SDAP/backend/src/data/'

def read_data_csv(p, w, n, s, cols):
    data = pl.read_csv(data_path + f'p{p}_wk{w}/{n}{s}Fnorm.csv', columns=cols)

    return data

def read_loc_csv(p, w, n, s):
    loc = pl.read_csv(data_path + f'p{p}_wk{w}/{n}{s}location_Bites.csv')

    return loc

def get_interval_from_csv(data, interval_index, sampling_rate=2000, interval_duration=5*60):
    """
    Extracts a specific 5-minute interval from a CSV file containing EMG data using Polars.

    Parameters:
    - file_path (str): Path to the CSV file.
    - interval_index (int): Index of the 5-minute interval to retrieve (0-based).
    - sampling_rate (int): Sampling rate of the data in Hz.
    - interval_duration (int): Duration of the interval in seconds (default is 5 minutes).

    Returns:
    - pl.DataFrame: Polars DataFrame containing the data for the specified 5-minute interval.
    """

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

    return interval_data

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


def find_mvc(signal_rms, loc):
    # Define Maximum Volontary Contraction
    signal_mvc = 0

    for row in loc.iter_rows():
        begin_contraction, end_contraction = int(row[0]), int(row[1])


        signal_bite_data = signal_rms[begin_contraction:end_contraction]

        signal_max_in_bite = signal_bite_data.max()

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







