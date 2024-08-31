import json
from pymongo.mongo_client import MongoClient

def get_session(username):
        # Parse the JSON body
        task_device = "michael-ubuntu"

        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['NeuraNet']
        session_collection = db['sessions']

        # Query for sessions with the given username and task_device
        sessions = session_collection.find({"username": username, "task_device": task_device})

        # Convert the cursor to a list of dictionaries and serialize ObjectId to string
        session_list = []
        for session in sessions:
            session['_id'] = str(session['_id'])  # Convert _id ObjectId to string
            session['device_id'] = str(session['device_id'])  # Convert device_id ObjectId to string
            session_list.append(session)


            # Use json.dumps to serialize the data, ensuring all elements are JSON-compatible
        response_data = {
            "result": "success",
            "sessions": session_list
        }
        return response_data

def main():
    # Test the function
    username = "mmills"
    response_data = get_session(username)
    print(response_data)

    json_response = json.dumps(response_data, indent=3)
    print(json_response)

if __name__ == '__main__':
    main()


 
