
# Bruxism Events Labeling Tool (BELT)
## Abstract
Sleep Bruxism (SB) involves repetitive jaw-muscle activities, such as teeth clenching or grind-
ing, which can cause muscle hypertrophy, tooth damage, and pain. Researchers at the Univer-
sity of Zurich’s Center for Dental Medicine (ZZM) are exploring an innovative approach for the
long-term acquisition of masticatory muscle activity during sleep using portable EMG biosignal
recorders, allowing data collection in natural home environments. This setup offers more afford-
able, scalable, and quicker data collection compared to traditional in-lab studies. However, chal-
lenges include limited sensor data, lack of established tools, high cognitive and time demands,
and difficulty in generalizing event labels across different patients.


To address these challenges, we collaborated with experts at ZZM, and applying the Design
Study Methodology (DSM) we contributed to the domain problems and requirements charac-
terization, the development and validation of BELT, and a discussion of key insights from our
study. Bruxism Event Labeling Tool (BELT) is a Visual Analytics (VA) system enabling experts to
confirm, reject, or modify bruxism events suggested by an XGBoost Classifier, as well as to add
new occurrences or annotations. The tool’s multi-level exploration offers signal visualization at
different granularities, with dynamic attribute displays to support decision-making.


In a user study with four experts, BELT was evaluated combining qualitative feedback with
quantitative metrics from SUS and PREVis to assess both usability and visualization readability.
Results showed that BELT allows users to effectively perform interactive labeling. Future works
should mainly focus on improving its usability and integrating the ground truth event labels in
the refinement of the model.


## Visuals
![BELT demo](BELT-demo.gif)

## Installation

### Backend
- Inside back-end folder: ``python3 -m venv .venv``
- macOS: ``source .venv/bin/activate``
- Windows: ``.venv\Scripts\activate``
- ``pip install -r requirements.txt``
- Set up environment variables by creating a `.env` file in the `backend` folder with: ``echo "DATABASE_URL=postgresql://postgres@localhost:5432/bruxit" > .env``
- Start PostgreSQL:
  - macOS: ``brew services start postgresql@14``
  - Windows: ``pg_ctl -D "C:\Program Files\PostgreSQL\14\data" start``
- Create the database: ``psql -h localhost -p 5432 -U postgres -c "CREATE DATABASE bruxit;"``
- Initialize database: ``flask db init``
- Migrate database: ``flask db migrate``
- Upgrade database: ``flask db upgrade``
- Define location of flask app:
  - macOS/Linux: ``export FLASK_APP=src.backend.py``
  - Windows: ``set FLASK_APP=src.backend.py``, ``$env:FLASK_APP = "src.backend.py"``
- Run the app: ``python3 -m src.backend``

### Frontend
- ``npm install -g @vue/cli``
- ``npm install vue-router@4``
- ``npm install vuex@next --save``
- ``npm install --save vuex-persist``
- ``npm install localforage``
- ``npm i pouchdb-utils``
- ``npm run serve``

## Abbreviations Glossary

| Abbreviation | Meaning                                      | Used In                                           | Notes                                   |
| ------------ | -------------------------------------------- | ------------------------------------------------- | --------------------------------------- |
| **MVC**      | Maximum Voluntary Contraction                | `MaximumVoluntaryContraction` model, `mvc` column | Used as calibration baseline            |
| **HRV**      | Heart Rate Variability                       | `SleepStageSegment`, `EventPrediction`            | Common in physiological signal analysis |
| **LF**       | Low Frequency component (0.04–0.15 Hz)       | `HRV_lf`, `HRV_lf_hf`                             | Part of HRV spectral features           |
| **HF**       | High Frequency component (0.15–0.4 Hz)       | `HRV_hf`, `HRV_lf_hf`                             | —                                       |
| **LF/HF**    | LF to HF ratio                               | `HRV_LFHF`, `HRV_lf_hf`                           | Sympathetic/parasympathetic balance     |
| **SDNN**     | Standard Deviation of NN intervals           | `HRV_SDNN`, `HRV_sdnn`                            | Time-domain HRV metric                  |
| **RRI**      | RR Intervals (beat-to-beat timing)           | `RRI`                                             | Core input for HRV metrics              |
| **MR**       | Masseter Right (EMG channel)                 | `std_mr`, `mav_mr`, etc.                          | Electromyography feature for right side |
| **ML**       | Masseter Left (EMG channel)                  | `std_ml`, `mav_ml`, etc.                          | —                                       |
| **STD**      | Standard Deviation                           | `std_mr`, `std_ml`                                | General statistical feature             |
| **VAR**      | Variance                                     | `var_mr`, `var_ml`                                | —                                       |
| **RMS**      | Root Mean Square                             | `rms_mr`, `rms_ml`                                | —                                       |
| **MAV**      | Mean Absolute Value                          | `mav_mr`, `mav_ml`                                | —                                       |
| **WAMP**     | Willison Amplitude                           | `wamp_mr`, `wamp_ml`                              | Signal complexity measure               |
| **FR**       | Frequency Ratio                              | `fr_mr`, `fr_ml`                                  | Domain-specific feature                 |
| **MNP**      | Mean Power                                   | `mnp_mr`, `mnp_ml`                                | Spectral power                          |
| **TOT**      | Total Power                                  | `tot_mr`, `tot_ml`                                | —                                       |
| **MNF**      | Mean Frequency                               | `mnf_mr`, `mnf_ml`                                | —                                       |
| **MDF**      | Median Frequency                             | `mdf_mr`, `mdf_ml`                                | —                                       |
| **PKF**      | Peak Frequency                               | `pkf_mr`, `pkf_ml`                                | —                                       |
| **AAC**      | Average Amplitude Change                     | `aac_mr`, `aac_ml`                                | EMG complexity                          |
| **DASDV**    | Difference Absolute Standard Deviation Value | `dasdv_mr`, `dasdv_ml`                            | Noise-robust signal stat                |
| **WL**       | Waveform Length                              | `wl_mr`, `wl_ml`                                  | Shape complexity                        |
| **LOG\_DET** | Log Determinant                              | `log_det_mr`, `log_det_ml`                        | Shape/volume metric                     |
| **Y\_PROB**  | Predicted probability for class `y=1`        | `y_prob`                                          | Model output                            |
| **ZC**       | Zero Crossing (commented out)                | `zc_mr`, `zc_ml` (disabled)                       | Possibly noisy                          |
| **EMG**      | Electromyography                             | `emg_left_name`, `emg_right_name` in `DataConfig` | Muscle signal type                      |
| **ECG**      | Electrocardiography                          | `ecg_name` in `DataConfig`                        | Heart signal source                     |