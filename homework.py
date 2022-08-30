from http import HTTPStatus
import logging
from logging.handlers import RotatingFileHandler
import os
import time
from urllib.error import HTTPError

from dotenv import load_dotenv
import requests
import telegram


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

TOKENS = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

PARSE_STATUS_PHRASE = 'Изменился статус проверки работы "{name}". {verdict}'
CONNECTION_ERROR_PHRASE = (
    'Запрос {endpoint} с заголовками {headers} и'
    'параметрами {params}: '
    '{text}'
)
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
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException as error:
        raise error(
            CONNECTION_ERROR_PHRASE.format(
                endpoint=ENDPOINT,
                headers=HEADERS,
                params=params,
                text=f'вернул {error}'
            )
        )
    if response.status_code != HTTPStatus.OK:
        raise HTTPError(
            CONNECTION_ERROR_PHRASE.format(
                endpoint=ENDPOINT,
                headers=HEADERS,
                params=params,
                text=f'вернул {response.status_code}'
            )
        )
    result = response.json()
    if 'code' in result and 'error' in result:
        raise HTTPError(
            CONNECTION_ERROR_PHRASE.format(
                endpoint=ENDPOINT,
                headers=HEADERS,
                params=params,
                text=f'передан неверный параметр {params}'
            )
        )
    return result


def check_response(response):
    """Проверяет, что полученные данные в нужном формате."""
    if not isinstance(response, dict):
        raise TypeError("Тип полученных данных не соответствует словарю")
    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError('Данные по ключу "homeworks" отсутствуют')
    if not isinstance(homeworks, list):
        raise TypeError(
            'Тип данных по ключу "homeworks" не соответствует списку'
        )
    return homeworks


def parse_status(homework):
    """Проверяет данные полученной домашки и возвращает текущий статус."""
    name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(
            f'Неожиданный статус {status}'
        )
    return PARSE_STATUS_PHRASE.format(
        name=name,
        verdict=HOMEWORK_VERDICTS[status]
    )


def check_tokens():
    """Проверяет наличие и валидность необходимых переменных окружения."""
    for name in TOKENS:
        if globals()[name] != name:
            logging.error(f'Токен {name} отсутствует')
        return False
    if all(TOKENS):
        return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise AttributeError('Один или несколько токенов отсутствуют')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    error_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            message = parse_status(check_response(response))
            if status != message:
                is_sended = send_message(bot, message)
                if is_sended:
                    status = message
            else:
                logging.debug('Статус проверки не изменился')
            current_timestamp = response.get('current_date', current_timestamp)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != error_message:
                send_message(bot, message)
                error_message = message
            logging.error(f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_TIME)

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s',
        filemode='w'
    )
    main()
