from pymongo import MongoClient

uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["NeuraNet"]

collection_name = "device_info_predictions"

def create_timeseries_collection():
    try:
        db.create_collection(
            collection_name,
            timeseries={
                "timeField": "timestamp",
                "metaField": "metadata",
                "granularity": "minutes"
            }
        )
        print(f"Time series collection '{collection_name}' created successfully.")
    except Exception as e:
        if "already exists" in str(e):
            print(f"Collection '{collection_name}' already exists.")
        else:
            print(f"Error creating collection: {e}")

if __name__ == "__main__":
    create_timeseries_collection() 