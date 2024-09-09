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
