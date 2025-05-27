import pika
import json
import requests
import sys , os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils')))
from utils import get_resumes_collection 
from model import Resume

from google import genai

# === Config === #
resumes_collection = get_resumes_collection()

# === Gemini API Setup ===
client = genai.Client(api_key="AIzaSyBv6R7CsUy6lPW9q7CVRqD3ViaDzT1BXu4")
# List available models to confirm free-tier support
# print("Available Gemini models:", [m.name for m in available_models])
# Free-tier models typically include text-bison-001 and chat-bison-001
MODEL_NAME = "gemini-2.0-flash"
# === RabbitMQ Setup ===
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='resume.parsed')
channel.queue_declare(queue='resume.tailored')

# === Tailoring Function ===
def tailor_resume(resume_doc):
    prompt = f"""I need to tailor my resume for a specific job. Here's my resume in JSON format:{json.dumps(resume_doc, indent=2)}. The job I'm applying for is for a {resume_doc['job_description']}

Please update my resume with the following guidelines:

1.  **Skills Section:** Explicitly highlight and prioritize skills relevant to the target job (e.g., placing them first in their respective categories). Add new skills if they are critical to the target job and commonly expected, even if not explicitly in my original resume, assuming general proficiency.
2.  **Experience Section:** Keep the original experience bullet points intact. However, rephrase or subtly adjust the wording of *existing* bullet points to emphasize transferable skills and achievements that are highly relevant to the target technology/role, without altering the factual content or meaning. For example, highlight "microservices architecture" if applicable to the new role, or "performance optimization" if that's a key requirement. Do not add new bullet points.
3.  **Projects Section:**
    * Review my existing projects.
    * If a project directly showcases the core skills required by the target job (e.g., a .NET project for a .NET job), ensure its description strongly emphasizes those skills.
    * If my projects *do not* adequately cover the core skills required by the target job (e.g., no .NET project for a .NET role, or no Python project for a Python role), then **replace the second project in the list** with a *new, hypothetical project* that demonstrates strong proficiency in those core required skills. Provide a realistic title, date, and detailed bullet points for this new project, making it sound like a genuine personal or academic endeavor.
4.  **Job Description & Keywords:** Update the `job_description` and `jd_keywords` fields in the JSON to accurately reflect the new target role (e.g., "Looking for a .NET and C# developer").

Please return the entire updated resume in the same JSON format without a tab character treat '-' as '-' and not a tab in output."""
    
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[prompt],
         config={
        "response_mime_type": "application/json",
        "response_schema": Resume,
    }
    )
    tailored_resume: Resume = response.text # or replace("\t", "") to remove tabs
    tailored_resume = tailored_resume.replace("\t","-")
    return tailored_resume

# === Consumer Callback ===
# Note: define callback with channel reference
def on_parsed(ch, method, properties, body):
    msg = json.loads(body)
    resume_id = msg['resume_id']
    print(resume_id)
    resume = resumes_collection.find_one({'_id': resume_id})
    tailored = tailor_resume(resume)

    resumes_collection.update_one(
        {'_id': resume_id},
        {'$set': {'tailored_resume': tailored, 'status': 'tailored'}}
    )
    channel.basic_publish(
        exchange='', routing_key='resume.tailored',
        body=json.dumps({'resume_id': resume_id})
    )
    # Notify orchestrator
    requests.post('http://localhost:5000/tailored-done', json={'resume_id': resume_id})

# === Start Consuming ===
channel.basic_consume(queue='resume.parsed', on_message_callback=on_parsed, auto_ack=True)
print('Resume Tailor Service: awaiting messages...')
channel.start_consuming()
