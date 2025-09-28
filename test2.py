import pymongo
import pandas as pd

def mongo_to_csv(
    connection_string,
    database_name, 
    collection_name,
    output_file="submissions_export.csv"
):
    client = pymongo.MongoClient(connection_string)
    db = client[database_name]
    collection = db[collection_name]
    
    documents = list(collection.find())
    
    if not documents:
        print("No documents found")
        return
    
    # Flatten submissions into individual rows
    flattened_data = []
    
    for doc in documents:
        # Base user info
        base_info = {
            'user_id': str(doc.get('_id', '')),
            'discord_id': doc.get('discord_id', ''),
            'rsn': doc.get('rsn', '').replace('"', ''),
            'clan': doc.get('clan', ''),
            'total_gained': doc.get('total_gained', 0)
        }
        
        submissions = doc.get('submissions', [])
        if submissions:
            for submission in submissions:
                row = base_info.copy()
                row.update({
                    'item': submission.get('item', ''),
                    'source': submission.get('source', ''),
                    'tier': submission.get('tier', ''),
                    'status': submission.get('status', ''),
                    'accepted_by': submission.get('accepted_by', ''),
                    'timestamp': submission.get('timestamp', ''),
                    'points_awarded': submission.get('points_awarded', 0)
                })
                flattened_data.append(row)
        else:
            flattened_data.append(base_info)
    
    df = pd.DataFrame(flattened_data)
    
    df = df.dropna(axis=1, how='all')
    
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    if 'timestamp' in df.columns:
        df = df.sort_values('timestamp')
    
    df.to_csv(output_file, index=False)
    print(f"Exported {len(df)} submission records to {output_file}")
    print(f"Columns: {list(df.columns)}")

def mongo_to_summary_csv(
    connection_string,
    database_name,
    collection_name,
    output_file="user_summary.csv"
):
    client = pymongo.MongoClient(connection_string)
    db = client[database_name]
    collection = db[collection_name]
    
    documents = list(collection.find())
    
    summary_data = []
    for doc in documents:
        summary = {
            'user_id': str(doc.get('_id', '')),
            'discord_id': doc.get('discord_id', ''),
            'rsn': doc.get('rsn', '').replace('"', ''),
            'clan': doc.get('clan', ''),
            'total_submissions': len(doc.get('submissions', [])),
            'total_gained': doc.get('total_gained', 0),
            'screenshot_categories': len(doc.get('screenshots', [])),
            'unique_items': len(doc.get('obtained_items', {}))
        }
        summary_data.append(summary)
    
    df = pd.DataFrame(summary_data)
    df.to_csv(output_file, index=False)
    print(f"Exported {len(df)} user summaries to {output_file}")


if __name__ == "__main__":
    CONNECTION_STRING = "mongodb://cvc-db:lkNzU2Y2Q4MmNkYTJlMTY1Y@db.ironfoundry.cc/?tlsInsecure=true"
    DATABASE_NAME = "Frenzy"
    COLLECTION_NAME = "Players"
    
    mongo_to_csv(CONNECTION_STRING, DATABASE_NAME, COLLECTION_NAME)
    
    mongo_to_summary_csv(CONNECTION_STRING, DATABASE_NAME, COLLECTION_NAME)