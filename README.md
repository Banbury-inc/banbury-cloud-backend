# In order to deploy to gcloud


gcloud auth login

gcloud auth configure-docker

deploy to cloud run

do i need to update dockerfile before I do a git commit?

select cloud build option instead of local

test

# Run server in dev environemnt
'''
python3  manage.py runserver 0.0.0.0:8080 --noreload
'''

# Run Websocket server
'''
daphne -p 8080 helloproject.asgi:application
'''
