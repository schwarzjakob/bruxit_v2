import neurokit2 as nk
import pandas as pd
import polars as pl
import numpy as np
import math
from .utils import *
from .models import SSD, db
import os



base_dir="C:/Users/eleon/Desktop/SDAP/backend/src/data"

def add_matrix_coordinates(df, x_max=18):
    df = df.copy()
    
    # Add x coordinate
    df['x'] = np.arange(len(df)) % x_max

    # Add y coordinate
    df['y'] = np.arange(len(df)) // x_max

    return df


def compute_HRV_metrics(peaks):
    duration_peaks = peaks[len(peaks)-1]
    divider = duration_peaks/2000/60/5
    segment = np.array_split(peaks, math.ceil(divider))

    hrv_segment_df=pd.DataFrame()

    for i in range(len(segment)):
        #print(i)
        hrv_segment=nk.hrv(segment[i],sampling_rate=2000, show=False)
        hrv_segment_df = pd.concat([hrv_segment_df,hrv_segment],ignore_index=True)

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
        'nrem': {'min':0.72, 'median': (2.59-0.72)/2, 'max': 2.59},
        'rem': {'min': 2.51-0.17, 'median': 2.51 , 'max': 2.51+0.17}
    }


# TODO: talk with Gabi, Vera, Barbara about this
def categorize_sleep_stage(value):
    lower, upper = get_ako_ranges()['rem']['min'], get_ako_ranges()['rem']['max']
    if lower <= value <= upper:
        return "rem"
    else:
        return "nrem"

def find_selected_tiles(value):
    if value == 'rem':
        return True
    else:
        return False




def return_HRV_analysis(patient_id, week_id, filename):
    file_path = base_dir + f"/p{patient_id}_wk{week_id}/{filename}"
    ecg = pl.read_csv(file_path, columns=['ECG'])

    # Insert duration info in the database
    calculate_night_duration(patient_id, week_id, filename, len(ecg), sampling_rate=2000)

    ecg_clean = nk.ecg_clean(ecg, sampling_rate=2000)
    ecg_peaks = nk.ecg_findpeaks(ecg_clean, sampling_rate=2000)
    info, r_peaks_corrected = nk.signal_fixpeaks(ecg_peaks, sampling_rate=2000, iterative=False, show=False, method="Kubios")


    # Save RR intervals to plot in events classification page 
    # TODO: put in external function

    # Calculate RR intervals
    rr_intervals = np.diff(r_peaks_corrected) / 2000

    # Insert fake data point
    rr_intervals_adjusted = np.insert(rr_intervals, 0, rr_intervals[0])

    # Calculate time axis
    time_r_peaks = r_peaks_corrected[1:] / 2000  # Time corresponding to the RR intervals
    time_r_peaks_adjusted = np.insert(time_r_peaks, 0, time_r_peaks[0] - rr_intervals[0])  # Add a time point for the fake interval

    rri_adj_df = pd.DataFrame(data={'RRI': rr_intervals_adjusted, 'RRI_t': time_r_peaks_adjusted})

    path = f"C:/Users/eleon/Desktop/SDAP/backend/src/data_resampled/p{patient_id}/wk{week_id}"
    if not os.path.exists(path):
        os.makedirs(path)

    rri_adj_df.to_csv(path + f"/{filename}_rri_256Hz.csv")

    # Calculate HRV metrics
    hrv = compute_HRV_metrics(r_peaks_corrected)

    hrv_cut = hrv[['HRV_LFHF','HRV_SDNN']]

    hrv_with_coords = add_matrix_coordinates(hrv_cut)

    hrv_with_coords['stage'] = hrv_with_coords['HRV_LFHF'].apply(categorize_sleep_stage)
    hrv_with_coords['selected'] = hrv_with_coords['stage'].apply(find_selected_tiles)

    # Add sleep stage detection to DB
    add_SSD_to_db(patient_id, week_id, filename, hrv_with_coords)

    print(hrv_with_coords)
    

    return hrv_with_coords.to_json(orient='records')


def add_SSD_to_db(patient_id, week_id, filename, df):
    for index, row in df.iterrows():
        ssd = SSD(patient_id=patient_id, week=week_id, file=filename, x=row['x'], y=row['y'], HRV_LFHF=row['HRV_LFHF'], HRV_SDNN=row['HRV_SDNN'], stage=row['stage'], selected=row['selected'])

        db.session.add(ssd)
        db.session.commit()