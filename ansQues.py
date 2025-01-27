import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import random
import logging
from constants import STATUS_3, STATUS_4, REPLIER_IDS, REPLY_QUESTION_URL, GOOGLE_SHEET
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    filename='answer_questions.log', 
    level=logging.INFO, 
    format='%(asctime)s:%(levelname)s:%(message)s'
)

# Google Sheets setup
# Load environment variables from the .env file
load_dotenv()
credentials_json_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_json_path, scope)
client = gspread.authorize(credentials)
sheet = client.open(GOOGLE_SHEET).sheet1

def ensure_columns_exist():
    columns = sheet.row_values(1)
    if 'Status' not in columns:
        sheet.update_cell(1, len(columns) + 1, 'Status')
    if 'Question ID' not in columns:
        sheet.update_cell(1, len(columns) + 1, 'Question ID')

# def get_random_posted_question(status):
#     records = sheet.get_all_records()
#     posted_questions = [record for record in records if record.get('Status') == status]
#     if posted_questions:
#         selected_question = random.choice(posted_questions)
#         row = records.index(selected_question) + 2  # +2 to account for header row and 1-based index
#         logging.debug(f"Selected question: {selected_question}")
#         return selected_question, row
#     return None, None

def get_all_posted_questions(status):
    records = sheet.get_all_records()
    # posted_questions = [record for record in records if record.get('Status') == status]
    posted_questions = {idx + 2: record for idx, record in enumerate(records) if record.get('Status') == status}
    logging.debug(f"Found {len(posted_questions)} posted questions")
    return posted_questions

def update_question_status(row, status):
    try:
        status_col = sheet.find('Status').col
        sheet.update_cell(row, status_col, status)
        logging.info(f"Updated question status at row {row} to {status}")
    except Exception as e:
        logging.error(f"Failed to update question status at row {row}: {e}")

def answer_question(question_id, answer_text, replier_id):
    url = REPLY_QUESTION_URL.format(question_id=question_id)
    headers = {
        'Authorization': os.getenv('API_TOKEN'),
        'Content-Type': 'application/json'
    }
    data = {
        "content": answer_text,
        "userForumId": replier_id
    }
    logging.debug(f"Answering question ID {question_id} with data: {data}")
    response = requests.post(url, headers=headers, json=data)
    logging.debug(f"Response status code: {response.status_code}")
    logging.debug(f"Response content: {response.content}")
    if response.ok:
        return True
    else:
        logging.error(f"Failed to answer question ID {question_id}: {response.text}")
        logging.error(f"Request headers: {headers}")
        logging.error(f"Request data: {data}")
        return False

def answer_all_posted_questions():
    questions = get_all_posted_questions(STATUS_3)
    for row, question in questions.items():
        if question:
            # row = questions.index(question) + 2
            question_id = question['Question ID']
            answer_text = question['Answer']
            replier_id = random.choice(REPLIER_IDS)
            logging.debug(f"Answering question ID {question_id} by user {replier_id}")
            if not answer_text:
                logging.error(f"Missing answer text for question ID {question_id}")
                continue
            if answer_question(question_id, answer_text, replier_id):
                update_question_status(row, STATUS_4)
                logging.info(f"Answered question ID {question_id} by user {replier_id}")
            else:
                logging.error(f"Failed to answer question ID {question_id}")
        else:
            logging.info("No posted questions to answer.")

if __name__ == '__main__':
    ensure_columns_exist()
    answer_all_posted_questions()
