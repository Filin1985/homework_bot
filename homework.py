from http import HTTPStatus
import logging
import os
from logging.handlers import RotatingFileHandler
import time

from dotenv import load_dotenv
import requests
import telegram

from exceptions import (
    ServerDenied,
    ResponseStatusError
)

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    __file__ + '.log',
    maxBytes=50000000,
    backupCount=5
)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PR_TOKEN')
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

TOKENS = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
ERROR_CODES = ['code', 'error']

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

PARSE_STATUS = 'Изменился статус проверки работы "{name}". {verdict}'
REQUEST_ERROR = (
    'Запрос {url} с заголовками {headers} и'
    'параметрами {params}: '
    'вернул {text}'
)
RESPONSE_ERROR = (
    'Запрос {url} с заголовками {headers} и'
    'параметрами {params}: '
    'вурнул ответ с ключем {code} и'
    'значением {text}'
)
STATUS_ERROR = (
    'Запрос {url} с заголовками {headers} и'
    'параметрами {params}: '
    'вурнул ответ со статусом {status}'
)
NOT_DICT = 'Тип данных {response} не словарь'
NOT_LIST = (
    'Тип данных {homeworks} по ключу "homeworks" не соответствует списку'
)
HOMEWORK_STATUS = 'Неожиданный статус {status}'
CHECK_TOKENS = 'Один или несколько токенов отсутствуют'
CHECK_STATUS = 'Статус проверки не изменился'
MESSAGE_ERROR = 'Сбой в работе программы: {error}'
MESSAGE_SENT = 'Сообщение {message} направлено в чат'
MESSAGE_NOT_SENT = 'Сообщение {message} не удалось направить в чат; {error}'


def send_message(bot, message):
    """Направляет сообщение в чат телеграмм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(
            MESSAGE_SENT.format(message=message)
        )
        return True
    except Exception as error:
        logger.exception(
            MESSAGE_NOT_SENT.format(message=message, error=error)
        )
        return False


def get_api_answer(current_timestamp):
    """Направляет запрос в API сервиса Практикум.Домашка."""
    request_data = dict(
        url=ENDPOINT,
        headers=HEADERS,
        params={'from_date': current_timestamp}
    )
    try:
        response = requests.get(**request_data)
    except requests.exceptions.RequestException as error:
        raise ConnectionError(
            REQUEST_ERROR.format(text=error, **request_data)
        )
    if response.status_code != HTTPStatus.OK:
        raise ResponseStatusError(
            STATUS_ERROR.format(status=response.status_code, **request_data)
        )
    result = response.json()
    for key in ERROR_CODES:
        if key in result:
            raise ServerDenied(
                RESPONSE_ERROR.format(
                    code=key,
                    text=result[key],
                    **request_data
                )
            )
    return result


def check_response(response):
    """Проверяет, что полученные данные в нужном формате."""
    if not isinstance(response, dict):
        raise TypeError(NOT_DICT.format(response=type(response)))
    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError('Данные по ключу "homeworks" отсутствуют')
    if not isinstance(homeworks, list):
        raise TypeError(NOT_LIST.format(homeworks=type(homeworks)))
    return homeworks


def parse_status(homework):
    """Проверяет данные полученной домашки и возвращает текущий статус."""
    name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(HOMEWORK_STATUS.format(status=status))
    return PARSE_STATUS.format(
        name=name,
        verdict=HOMEWORK_VERDICTS[status]
    )


def check_tokens():
    """Проверяет наличие и валидность необходимых переменных окружения."""
    tokens_failed = [name for name in TOKENS if not globals()[name]]
    if tokens_failed:
        logging.error(f'Токен(ы) {tokens_failed} отсутствует')
    return not tokens_failed


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise ValueError(CHECK_TOKENS)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    error_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            message = parse_status(check_response(response))
            if status == message:
                logging.debug(CHECK_STATUS)
                continue
            if send_message(bot, message):
                status = message
                current_timestamp = response.get(
                    'current_date',
                    current_timestamp
                )
        except Exception as error:
            message = MESSAGE_ERROR.format(error=error)
            logging.error(MESSAGE_ERROR.format(error=error))
            if message != error_message and send_message(bot, message):
                error_message = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s',
        filemode='w'
    )
    main()
