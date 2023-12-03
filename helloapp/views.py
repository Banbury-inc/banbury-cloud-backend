from django.shortcuts import render
import os
import pymongo
import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from .forms import UserForm


def homepage(request):
    service = os.environ.get('K_SERVICE', 'Unknown service')
    revision = os.environ.get('K_REVISION', 'Unknown revision')
    
    return render(request, 'homepage.html', context={
        "message": "It's running!",
        "Service": service,
        "Revision": revision,
    })

def aboutpage(request):
    return render(request, 'aboutpage.html', context={})

def adduser(request):
    # MongoDB connection string

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    # Create a MongoDB client
    client = pymongo.MongoClient(uri, server_api=ServerApi('1'))

    # Select the database and collection
    db = client['myDatabase']
    user_collection = db['users']

    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            # Insert the user into the database
            try:
                user_collection.insert_one({"username": username})
                message = f"User '{username}' added successfully."
            except pymongo.errors.OperationFailure as e:
                message = f"An error occurred: {e}"
            return render(request, 'user_added.html', {'message': message})
    else:
        form = UserForm()

    return render(request, 'add_user.html', {'form': form})







