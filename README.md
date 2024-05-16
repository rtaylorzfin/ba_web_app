Biocurator Assistant Web Front-End
===

### Quickstart
The cookiecutter project allows docker, but I prefer to run the project locally. To do so, follow these steps:

#### Build:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
npm install
npm run-script build
```

#### Initialize Environment:
```
cp .env.example .env
```

#### Initialize DB:
```
flask db init
flask db migrate
flask db upgrade
```

#### Run:
```
docker run -it -p '6379:6379' redis
celery -A autoapp.celery worker
flask run
```

