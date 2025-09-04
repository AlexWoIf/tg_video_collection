import os
import logging

from dotenv import load_dotenv


class Config():
    def __init__(self, override=True):
        load_dotenv(override=override)

        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '3306')
        db_name = os.getenv('DB_NAME', 'your_database_name')
        db_user = os.getenv('DB_USER', 'your_username')
        db_password = os.getenv('DB_PASSWORD', 'your_password')
        self.db_url = f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}' # noqa: E501

        self.tg_bot_token = os.getenv('TG_BOT_TOKEN', '')
        self.tg_api_url = os.getenv('TG_API_URL', 'https://api.telegram.org/bot') # noqa: E501
        self.storage_channel_id = os.getenv('STORAGE_CHANNEL_ID', '')