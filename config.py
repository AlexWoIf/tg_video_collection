import os

from dotenv import load_dotenv


class Config():
    def __init__(self, override=True):
        load_dotenv(override=override)

        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '3306')
        db_name = os.getenv('DB_NAME', '')
        db_user = os.getenv('DB_USER', '')
        db_password = os.getenv('DB_PASSWORD', '')
        if not db_name or not db_user or not db_password:
            raise ValueError('Some DB params are not set')
        self.db_url = f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}' # noqa: E501

        self.tg_bot_token = os.getenv('TG_BOT_TOKEN', '')
        tg_base_url = os.getenv('TG_BASE_URL', 'https://api.telegram.org/bot')
        self.tg_api_url = f'{tg_base_url}{self.tg_bot_token}'

        self.storage_chat_id = os.getenv('STORAGE_CHAT_ID', '')
