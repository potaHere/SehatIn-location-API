from google.cloud import secretmanager
import os
import json
from flask import Flask, jsonify, request
from google.cloud import storage
from dotenv import load_dotenv
from geopy.distance import geodesic

app = Flask(__name__)

# Function to get secret from Secret Manager
def get_secret(secret_id):
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    name = f"projects/609904973527/secrets/service-account-bucket/versions/1"
    response = client.access_secret_version(request={"name": name})
    secret_string = response.payload.data.decode("UTF-8")
    return secret_string

# Replace with your secret ID
SERVICE_ACCOUNT_KEY = get_secret("service-account-key")

# Initialize Google Cloud Storage client
storage_client = storage.Client.from_service_account_info(json.loads(SERVICE_ACCOUNT_KEY))

# Function to load data from Google Cloud Storage
def load_data_from_gcs(bucket_name, file_name):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    data = json.loads(blob.download_as_string())
    return data

# Function to save data to Google Cloud Storage
def save_data_to_gcs(bucket_name, file_name, data):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    blob.upload_from_string(json.dumps(data))

# Load environment variables
load_dotenv()

# Define constants
BUCKET_NAME = os.getenv('BUCKET_NAME')
FILE_NAME = os.getenv('FILE_NAME')

# Load data from Google Cloud Storage
data = load_data_from_gcs(BUCKET_NAME, FILE_NAME)

# Define Flask routes
@app.route('/toko/dekat', methods=['GET'])
def get_nearby_toko():
    user_lat = request.args.get('latitude', type=float)
    user_lng = request.args.get('longitude', type=float)
    if user_lat is None or user_lng is None:
        return jsonify({'error': 'Latitude and longitude are required'}), 400

    def distance_to_user(store):
        store_lat = store['latitude']
        store_lng = store['longitude']
        return geodesic((user_lat, user_lng), (store_lat, store_lng)).kilometers

    stores_within_radius = [store for store in data if distance_to_user(store) <= 3]
    return jsonify(stores_within_radius), 200, {'message': f"Berhasil mendapatkan {len(stores_within_radius)} toko terdekat dari anda"}

@app.route('/toko', methods=['POST'])
def add_toko():
    new_toko = request.json
    data.append(new_toko)
    save_data_to_gcs(BUCKET_NAME, FILE_NAME, data)
    return jsonify(new_toko), 201, {'message': 'Berhasil menambahkan toko baru'}

@app.route('/toko/<int:index>', methods=['DELETE'])
def delete_toko(index):
    if index < 0 or index >= len(data):
        return jsonify({'error': 'Index out of range'}), 404
    deleted_toko = data.pop(index)
    save_data_to_gcs(BUCKET_NAME, FILE_NAME, data)
    return jsonify(deleted_toko), 200, {'message': 'Berhasil menghapus toko'}

@app.route('/toko/<int:index>', methods=['PUT'])
def update_toko(index):
    updated_toko = request.json
    if index < 0 or index >= len(data):
        return jsonify({'error': 'Index out of range'}), 404
    data[index] = updated_toko
    save_data_to_gcs(BUCKET_NAME, FILE_NAME, data)
    return jsonify(updated_toko), 200, {'message': f"Berhasil memperbaharui toko {updated_toko['nama_toko']}"} 

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)