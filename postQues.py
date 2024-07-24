import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import random
import logging
import json
from constants import STATUS_2, STATUS_3, AUTHOR_IDS, POST_QUESTION_URL, N

# Set up logging
logging.basicConfig(
    filename='post_questions.log', 
    level=logging.INFO, 
    format='%(asctime)s:%(levelname)s:%(message)s'
)

# Google Sheets setup
credentials_json_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_json_path, scope)
client = gspread.authorize(credentials)
sheet = client.open('questions').sheet1

def ensure_columns_exist():
    columns = sheet.row_values(1)
    if 'Status' not in columns:
        sheet.update_cell(1, len(columns) + 1, 'Status')
    if 'Question ID' not in columns:
        sheet.update_cell(1, len(columns) + 1, 'Question ID')

def get_random_pending_question(status):
    records = sheet.get_all_records()
    pending_questions = [record for record in records if record.get('Status') == status]
    if pending_questions:
        selected_question = random.choice(pending_questions)
        row = records.index(selected_question) + 2  # +2 to account for header row and 1-based index
        logging.debug(f"Selected question: {selected_question}")
        return selected_question, row
    return None, None

def update_question_status(row, status, question_id=None):
    status_col = sheet.find('Status').col
    sheet.update_cell(row, status_col, status)
    if question_id:
        question_id_col = sheet.find('Question ID').col
        sheet.update_cell(row, question_id_col, question_id)

def post_question(question_text, author_id):
    url = POST_QUESTION_URL
    headers = {
        'Authorization': os.getenv('API_TOKEN'),
        'Content-Type': 'application/json'
    }
    data = {
        "title": question_text,
        "content": question_text,
        "userForumId": author_id
    }
    logging.debug(f"Posting question: {data}")
    response = requests.post(url, headers=headers, json=data)
    logging.debug(f"Response status code: {response.status_code}")
    logging.debug(f"Response content: {response.content}")
    try:
        response_data = response.json()
        logging.debug(f"Response data: {response_data}")
        if response.status_code == 201 or response_data.get('success'):  # Assuming 201 Created is the success status code
            question_id = response_data['body'].get('topicId')
            return question_id
        else:
            logging.error(f"Failed to post question: {response_data}")
            return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON response: {str(e)} - Response text: {response.text}")
        return None

def post_pending_question():
    for n in range(N):
        question, row = get_random_pending_question(STATUS_2)
        if question:
            question_text = question['Title']
            author_id = random.choice(AUTHOR_IDS)
            logging.debug(f"Posting question {n}: '{question_text}' by user {author_id}")
            question_id = post_question(question_text, author_id)
            if question_id:
                update_question_status(row, STATUS_3, question_id)
                logging.info(f"Posted question {n+1} '{question_text}' with ID {question_id} by user {author_id}")
            else:
                logging.error(f"Failed to post question '{question_text}'")
        else:
            logging.info("No pending questions to post.")
            break
        
        # Add a counter, and post multiple questions at 10 am, should run in loop, 
        # num of questions to be posted should be modifyable ^^
        # authid and replyid in a const file,  ^^
        # status words, api url, everything in a const file ^^
        # Crappiest advice question 


if __name__ == '__main__':
    ensure_columns_exist()
    post_pending_question()
