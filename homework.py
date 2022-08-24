import os
import requests
import telegram
import time
from datetime import datetime
import logging

from dotenv import load_dotenv
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

load_dotenv()
logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s %(levelname)s %(message)s',
    filemode='w'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    'my_logger.log',
    maxBytes=50000000,
    backupCount=5
)
logger.addHandler(handler)

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
    """Направляет сообщение в чат телеграмм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение {message} направлено в чат {TELEGRAM_CHAT_ID}')
    except Exception:
        logger.error('Сбой при отправке сообщения в чат телеграмм')


def get_api_answer(current_timestamp):
    """Направляет запрос в API сервиса Практикум.Домашка."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        logger.error(
            f'{datetime.now()} Запрос {ENDPOINT} не отработал'
        )
    if response.status_code != HTTPStatus.OK:
        res_status = response.status_code
        logger.error(
            f'{datetime.now()} Запрос {ENDPOINT} вернул результат {res_status}'
        )
        raise Exception(f'Запрос вернул статус {res_status}')
    return response.json()


def check_response(response):
    """Проверяет, что полученные данные в нужном формате."""
    if type(response) is not dict:
        logger.error(
            f'{datetime.now()} Ответ получен в формате отличном от словаря'
        )
        raise TypeError("Ответ получен в формате отличном от словаря")
    return response['homeworks'][0]


def parse_status(homework):
    """Проверяет данные полученной домашки и возвращает текущий статус."""
    if 'homework_name' not in homework:
        logger.error(
            f'{datetime.now()} Ключа "homework_name" нет в результате запроса'
        )
        raise Exception('Ключа "homework_name" нет в результате запроса')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        logger.error(
            f'{datetime.now()} Запрос по адресу {ENDPOINT} не отработал'
        )
        raise Exception('Ключа "homework_status" нет в результате запроса')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие и валидность необходимых переменных окружения."""
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    STATUS = ''
    if not check_tokens():
        logger.critical(
            f'{datetime.now()} Один или несколько токенов невалидны'
        )
        raise Exception('Один или несколько токенов невалидны')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            message = parse_status(check_response(response))
            if STATUS != message:
                send_message(bot, message)
                STATUS = message
            else:
                logger.debug('Статус проверки не изменился')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(f'{datetime.now()} Сбой в работе программы')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
