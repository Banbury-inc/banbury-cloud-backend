# Banbury Cloud Back End
This repo contains the server that provides API access to all the functionality of Banbury Cloud.

# Getting Started

# Run the script
'''
./run.sh
'''

Or you can run each individually

Run server in dev environemnt
'''
python3  manage.py runserver 0.0.0.0:8080 --noreload
'''

Run Websocket server
'''
daphne -p 8082 helloproject.asgi:application
'''







