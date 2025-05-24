# resume_parser_service/main.py

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
import uuid
import spacy
import pika
import json
from pymongo import MongoClient
from docx import Document

# === Config === #
UPLOAD_FOLDER = "./uploads"
ALLOWED_EXTENSIONS = {'docx'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# === NLP Setup === #
lp = spacy.load("en_core_web_sm")

# === MongoDB Setup === #
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["tailor_my_resume"]
resumes_collection = db["resumes"]

# === RabbitMQ Setup === #
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='resume.parsed')

# === Utils === #
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_docx(filepath):
    doc = Document(filepath)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_keywords(text, top_n=10):
    doc = lp(text)
    keywords = [token.text for token in doc if token.is_alpha and not token.is_stop]
    return list(set(keywords))[:top_n]

# === Route === #
@app.route('/upload', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files or 'jd' not in request.form:
        return jsonify({"error": "Missing resume file or job description"}), 400

    resume_file = request.files['resume']
    jd_text = request.form['jd']

    if resume_file.filename == '' or not allowed_file(resume_file.filename):
        return jsonify({"error": "Invalid or no DOCX file uploaded"}), 400

    filename = secure_filename(resume_file.filename)
    resume_id = str(uuid.uuid4())
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], resume_id + "_" + filename)
    resume_file.save(filepath)

    resume_text = extract_text_from_docx(filepath)
    jd_keywords = extract_keywords(jd_text)

    resume_doc = {
        "_id": resume_id,
        "parsed_resume": resume_text,
        "job_description": jd_text,
        "jd_keywords": jd_keywords,
        "status": "parsed"
    }

    resumes_collection.insert_one(resume_doc)

    # publish to RabbitMQ
    message = json.dumps({"resume_id": resume_id, "status": "parsed"})
    channel.basic_publish(exchange='', routing_key='resume.parsed', body=message)

    return jsonify({"message": "Resume parsed and published", "resume_id": resume_id})

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, port=5001)
