# resume_parser_service/main.py

from flask import Flask, request, jsonify
import os, sys
import uuid
import spacy
import pika
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils')))
from utils import get_resumes_collection


# === Config === #
app = Flask(__name__)

# === NLP Setup === #
lp = spacy.load("en_core_web_sm")


resumes_collection = get_resumes_collection()

# === RabbitMQ Setup === #
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='resume.parsed')

# === Keyword Extraction === #
def extract_keywords(text, top_n=20):
    doc = lp(text)
    keywords = [token.lemma_.lower() for token in doc if token.is_alpha and not token.is_stop]
    freq = {}
    for word in keywords:
        freq[word] = freq.get(word, 0) + 1
    sorted_keywords = sorted(freq, key=freq.get, reverse=True)
    return sorted_keywords[:top_n]

# === Route === #
@app.route('/upload-json', methods=['POST'])
def upload_resume_json():
    jd_text = request.args.get("jd", default="", type=str)
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing or invalid JSON payload"}), 400

    resume_id = str(uuid.uuid4())
    jd_keywords = extract_keywords(jd_text)

    resume_doc = {
        "_id": resume_id,
        "name": data.get("name", ""),
        "contact_number": data.get("contact_number", ""),
        "email": data.get("email", ""),
        "linkedin": data.get("linkedin", ""),
        "skills": data.get("skills", {}),
        "experience": data.get("experience", []),
        "education": data.get("education", []),
        "projects": data.get("projects", []),
        "honors_and_awards": data.get("honors_and_awards", []),
        "job_description": jd_text,
        "jd_keywords": jd_keywords,
        "status": "parsed"
    }

    print(resume_doc)
    resumes_collection.insert_one(resume_doc)

    message = json.dumps({"resume_id": resume_id, "status": "parsed"})
    channel.basic_publish(exchange='', routing_key='resume.parsed', body=message)

    return jsonify({"message": "JSON resume parsed and published", "resume_id": resume_id})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
