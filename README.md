# cicdmeta

# migrate
flask --app model.py db init
flask --app model.py db migrate
flask --app model.py db upgrade