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
- Inside back-end folder: ``python -m venv .venv``
- macOS: ``source .venv/bin/activate``
- Windows: ``.venv\Scripts\activate``
- ``pip install Flask Flask-Cors``
- Define location of flask app (Windows): ``set FLASK_APP=run.py``, ``$env:FLASK_APP = "run.py"``, ``flask run``
- Initialize database: ``flask db init``
- Migrate database: ``flask db migrate``
- Upgrade database: ``flask db upgrade``


### Frontend
- ``npm install -g @vue/cli``
- ``npm install vue-router@4``
- ``npm install vuex@next --save``
- ``npm install --save vuex-persist``
- ``npm install localforage``
- ``npm i pouchdb-utils``
