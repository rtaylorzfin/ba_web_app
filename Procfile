release: flask db upgrade
web: gunicorn ba_web_app.app:create_app\(\) -b 0.0.0.0:$PORT -w 3
