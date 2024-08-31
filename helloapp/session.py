import json
from pymongo.mongo_client import MongoClient
import json


def get_session(username):
        # Parse the JSON body
        task_device = "michael-ubuntu"

        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['NeuraNet']
        session_collection = db['sessions']

        # Query for sessions with the given username and task_device
        sessions = session_collection.find({"username": username, "task_device": task_device})

        all_sessions_data = []
        # Convert the cursor to a list of dictionaries and serialize ObjectId to string
        for session in sessions:
            all_sessions_data.append({
                "task_name": session["task_name"],
                "task_device": session["task_device"],
                "task_status": session["task_status"],
                })



            # Use json.dumps to serialize the data, ensuring all elements are JSON-compatible
        response_data = {
            "result": "success",
            "sessions": all_sessions_data
        }
        return response_data

def main():
    # Test the function
    username = "mmills"
    response_data = get_session(username)
    print(response_data)


if __name__ == '__main__':
    main()


 
