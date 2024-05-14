Biocurator Assistant Web Front-End
===

### Quickstart
The cookiecutter project allows docker, but I prefer to run the project locally. To do so, follow these steps:

#### Build:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/dev.txt
npm install
npm run-script build
```

#### Initialize Environment:
```
export FLASK_ENV=production
export FLASK_DEBUG=0
export DATABASE_URL="sqlite:////tmp/biocurator.db"
export REDIS_URL=redis://localhost:6379/0
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

