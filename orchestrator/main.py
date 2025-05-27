from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

TAILOR_ENDPOINT = 'http://localhost:5002/tailor'

@app.route('/resume-ready', methods=['POST'])
def resume_ready():
    data = request.get_json()
    resume_id = data.get('resume_id')
    # Notify tailor service to process this resume
    requests.post(TAILOR_ENDPOINT, json={'resume_id': resume_id})
    return jsonify({'message': f'Tailoring started for {resume_id}'})

@app.route('/tailored-done', methods=['POST'])
def tailored_done():
    data = request.get_json()
    resume_id = data.get('resume_id')
    print(f'Tailored resume ready: {resume_id}')
    return jsonify({'message': f'Received tailored resume for {resume_id}'})

if __name__ == '__main__':
    app.run(port=5000, debug=True)