import os
from datetime import datetime, timezone

LOG_DIR = "./log"
LOG_FILE = f"{LOG_DIR}/call_log.log"

def check_folder_exist():
    if not os.path.exists(LOG_DIR):
        os.mkdir(LOG_DIR)

def log_msg_file(filepath: str, content: str):
    time = datetime.today().isoformat()
    file = open(filepath, "+a", encoding="utf-8")
    file.write(f"{time}\n{content}\n\n")
    file.close()

def log_call_log(content: str):
    log_msg_file(LOG_FILE, content)

def get_msg_log():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return ""
