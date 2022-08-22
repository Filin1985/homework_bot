import os
import requests
import telegram
import time
from datetime import datetime
import logging

from dotenv import load_dotenv
from http import HTTPStatus

load_dotenv()
logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s %(levelname)s %(message)s '
)

PRACTICUM_TOKEN = os.getenv('PR_TOKEN')
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    print('Hello')


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logging.error(f'{datetime.now()} Запрос по адресу {ENDPOINT} не отработал')
    if response.status != HTTPStatus.OK:
        res_status = response.status
        logging.error(f'{datetime.now()} Запрос по адресу {ENDPOINT} вернул результат {res_status}')
        raise Exception(f'Запрос вернул статус {res_status}')
    return response


def check_response(response):
    if type(response) is not dict:
        raise TypeError("Ответ получен в формате отличном от словаря")


def parse_status(homework):
    homework_name = ...
    homework_status = ...

    ...

    verdict = ...

    ...

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    ...


def main():
    """Основная логика работы бота."""
    ...

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    ...

    while True:
        try:
            response = get_api_answer(current_timestamp)

            ...

            current_timestamp = ...
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            ...
            time.sleep(RETRY_TIME)
        else:
            ...


if __name__ == '__main__':
    main()
