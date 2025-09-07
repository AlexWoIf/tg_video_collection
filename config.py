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
        self.db_url = f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}' # noqa: E501

        tg_bot_token = os.getenv('TG_BOT_TOKEN', '')
        self.tg_bot_token = tg_bot_token
        tg_base_url = os.getenv('TG_BASE_URL', 'https://api.telegram.org/bot')
        self.tg_api_url = f'{tg_base_url}{tg_bot_token}'

        self.parameters = {
            'storage_chat_id': os.getenv('STORAGE_CHAT_ID', ''),
            'page_length': int(os.getenv('MAX_PAGE_LENGTH', '10')),
        }

        # TODO: use pydantic instead
        if not db_name or not db_user or not db_password or not tg_bot_token:
            raise ValueError('Some params does not set')
