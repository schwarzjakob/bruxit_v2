# TODO: Refactor this file into the following modules and move corresponding code:

# 1. services/sleep_stage_service.py
#    - HRV_analysis(patient_id, week, file, sampling_rate)
#    - return_HRV_analysis(patient_id, week_id, filename, sampling_rate)

# 2. services/database_service.py
#    - add_sleep_stages_to_db(patient_id, week_id, filename, df)

# 3. utils/hrv_utils.py
#    - compute_hrv_segments(peaks, sampling_rate)             (formerly compute_HRV_metrics)
#    - categorize_sleep_stage(lf_hf_ratio)
#    - get_ako_ranges()
#    - add_matrix_coordinates(df, x_max=18)
#    - find_selected_tiles(value)

# 4. utils/signal_processing.py
#    - clean_ecg_and_find_peaks(ecg_signal, sampling_rate)
#    - compute_rr_intervals(peaks, sampling_rate)

# After migrating:
# - This file can be deleted.
# - Ensure all imports are updated in dependent files.
# - Confirm function signatures and naming consistency.


import neurokit2 as nk
import pandas as pd
import polars as pl
import numpy as np
import math
from utils.utils import *
from models.models import SSD, Settings, db
import os


def add_matrix_coordinates(df, x_max=18):
    df = df.copy()

    # Add x coordinate
    df["x"] = np.arange(len(df)) % x_max

    # Add y coordinate
    df["y"] = np.arange(len(df)) // x_max

    return df


def compute_HRV_metrics(peaks, sampling_rate):
    duration_peaks = peaks[len(peaks) - 1]
    divider = duration_peaks / sampling_rate / 60 / 5
    segment = np.array_split(peaks, math.ceil(divider))

    hrv_segment_df = pd.DataFrame()

    for i in range(len(segment)):
        # print(i)
        hrv_segment = nk.hrv(segment[i], sampling_rate=sampling_rate, show=False)
        hrv_segment_df = pd.concat([hrv_segment_df, hrv_segment], ignore_index=True)

    return hrv_segment_df


"""Return REM and NREM LF/HF ranges from: Ako et al., Correlation between electroencephalography and heart rate variability during sleep (2003)
    All the values as a reference:
    stage_1 = {'min': 2.30-0.29, 'median': 2.30, 'max': 2.30+0.29}
    stage_2 = {'min': 1.85-0.09 , 'median': 1.85 , 'max': 1.85+0.09}
    stage_3 = {'min': 0.78-0.06 , 'median': 0.78, 'max': 0.78+0.06}
    stage_4 = {'min': 0.86-0.14, 'median': 0.86, 'max': 0.86+0.14}
    rem = {'min': 2.51-0.17, 'median': 2.51, 'max': 2.51+0.17}
"""


def get_ako_ranges():
    return {
        "nrem": {"min": 0.72, "median": (2.59 - 0.72) / 2, "max": 2.59},
        "rem": {"min": 2.51 - 0.17, "median": 2.51, "max": 2.51 + 0.17},
    }


def categorize_sleep_stage(lf_hf_ratio):
    # Ranges from Ako et al. paper
    light_sleep_range = (1.76, 2.59)
    deep_sleep_range = (0.72, 1.00)
    rem_sleep_range = (2.34, 2.68)

    # Handle the overlapping range between REM and light sleep
    if rem_sleep_range[0] <= lf_hf_ratio <= light_sleep_range[1]:
        # Calculate the distance to REM and Light Sleep
        dist_to_light_sleep = min(
            abs(lf_hf_ratio - light_sleep_range[0]),
            abs(lf_hf_ratio - light_sleep_range[1]),
        )
        dist_to_rem_sleep = min(
            abs(lf_hf_ratio - rem_sleep_range[0]), abs(lf_hf_ratio - rem_sleep_range[1])
        )

        # Assign to the category with the closest distance
        if dist_to_rem_sleep < dist_to_light_sleep:
            return "rem"
        else:
            return "light"

    elif deep_sleep_range[0] <= lf_hf_ratio <= deep_sleep_range[1]:
        return "deep"
    else:
        # If out of range, assign to the closest category
        # Compute distances to the nearest boundary of each range
        dist_to_deep_sleep = min(
            abs(lf_hf_ratio - deep_sleep_range[0]),
            abs(lf_hf_ratio - deep_sleep_range[1]),
        )
        dist_to_light_sleep = min(
            abs(lf_hf_ratio - light_sleep_range[0]),
            abs(lf_hf_ratio - light_sleep_range[1]),
        )
        dist_to_rem_sleep = min(
            abs(lf_hf_ratio - rem_sleep_range[0]), abs(lf_hf_ratio - rem_sleep_range[1])
        )

        # Find the minimum distance
        min_distance = min(dist_to_deep_sleep, dist_to_light_sleep, dist_to_rem_sleep)

        # Assign category based on the closest distance
        if min_distance == dist_to_deep_sleep:
            return "deep"
        elif min_distance == dist_to_rem_sleep:
            return "rem"
        else:
            return "light"


def find_selected_tiles(value):
    if value == "rem":
        return True
    else:
        return False


def HRV_analysis(patient_id, week, file, sampling_rate):
    downsampled_data_path = get_settings().downsampled_data_path
    file_path = f"{downsampled_data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv"
    ecg = pl.read_csv(file_path, columns=["ECG"])

    ecg_clean = nk.ecg_clean(ecg, sampling_rate=sampling_rate)
    ecg_peaks = nk.ecg_findpeaks(ecg_clean, sampling_rate=sampling_rate)
    info, r_peaks_corrected = nk.signal_fixpeaks(
        ecg_peaks,
        sampling_rate=sampling_rate,
        iterative=False,
        show=False,
        method="Kubios",
    )

    # Calculate HRV metrics
    hrv = compute_HRV_metrics(r_peaks_corrected, sampling_rate)

    hrv_cut = hrv[["HRV_LFHF", "HRV_SDNN"]]

    hrv_with_coords = add_matrix_coordinates(hrv_cut)

    hrv_with_coords["stage"] = hrv_with_coords["HRV_LFHF"].apply(categorize_sleep_stage)

    # Add sleep stage detection to DB
    add_SSD_to_db(patient_id, week, file, hrv_with_coords)

    print(hrv_with_coords)

    return hrv_with_coords.to_json(orient="records")


def return_HRV_analysis(patient_id, week_id, filename, sampling_rate):
    original_data_path = get_settings().original_data_path
    file_path = original_data_path + f"/p{patient_id}_wk{week_id}/{filename}"
    ecg = pl.read_csv(file_path, columns=["ECG"])

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
        time_r_peaks, 0, time_r_peaks[0] - rr_intervals[0]
    )  # Add a time point for the fake interval

    rri_adj_df = pd.DataFrame(
        data={"RRI": rr_intervals_adjusted, "RRI_t": time_r_peaks_adjusted}
    )

    downsampled_data_path = get_settings().downsampled_data_path
    path = f"{downsampled_data_path}/p{patient_id}_wk{week_id}"
    if not os.path.exists(path):
        os.makedirs(path)

    rri_adj_df.to_csv(path + f"/{filename}_rri_256Hz.csv")

    # Calculate HRV metrics
    hrv = compute_HRV_metrics(r_peaks_corrected, sampling_rate)

    hrv_cut = hrv[["HRV_LFHF", "HRV_SDNN"]]

    hrv_with_coords = add_matrix_coordinates(hrv_cut)

    hrv_with_coords["stage"] = hrv_with_coords["HRV_LFHF"].apply(categorize_sleep_stage)
    hrv_with_coords["selected"] = hrv_with_coords["stage"].apply(find_selected_tiles)

    # Add sleep stage detection to DB
    add_SSD_to_db(patient_id, week_id, filename, hrv_with_coords)

    print(hrv_with_coords)

    return hrv_with_coords.to_json(orient="records")


def add_SSD_to_db(patient_id, week_id, filename, df):
    for index, row in df.iterrows():
        ssd = SSD(
            patient_id=patient_id,
            week=week_id,
            file=filename,
            x=row["x"],
            y=row["y"],
            HRV_LFHF=row["HRV_LFHF"],
            HRV_SDNN=row["HRV_SDNN"],
            stage=row["stage"],
        )

        db.session.add(ssd)
        db.session.commit()
