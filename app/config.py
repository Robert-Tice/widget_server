import os

class Config(object):
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    TASK_TIME_LIMIT = 30

    RECEIVED_FILE_CHAR_LIMIT = 50 * 1000
    # The limit in number of characters of files to accept

    TEMPLATE_DIR = os.path.join(os.getcwd(), "app", "widget", "static", "templates")