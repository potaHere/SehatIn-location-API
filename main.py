from flask import Flask, jsonify, request
from google.cloud import storage
import json
import os
from dotenv import load_dotenv
from geopy.distance import geodesic

app = Flask(__name__)

def load_data_from_gcs(bucket_name, file_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    data = blob.download_as_text()
    return json.loads(data)

def save_data_to_gcs(bucket_name, file_name, data):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    blob.upload_from_string(json.dumps(data))

def download_service_account_key(bucket_name, file_name, local_path):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    blob.download_to_filename(local_path)

load_dotenv()

SERVICE_ACCOUNT_KEY_PATH = "/tmp/sehatin-capstone-c241-9dd097cc8db3.json"
BUCKET_NAME = os.getenv('BUCKET_NAME')
FILE_NAME = os.getenv('FILE_NAME')
SERVICE_ACCOUNT_FILE_NAME = "sehatin-capstone-c241-9dd097cc8db3.json"
download_service_account_key(BUCKET_NAME, SERVICE_ACCOUNT_FILE_NAME, SERVICE_ACCOUNT_KEY_PATH)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = SERVICE_ACCOUNT_KEY_PATH

data = load_data_from_gcs(BUCKET_NAME, FILE_NAME)

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
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
