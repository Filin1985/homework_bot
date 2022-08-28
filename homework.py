import logging
import os
from urllib.error import HTTPError
import requests
import telegram
import time

from dotenv import load_dotenv
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

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


def send_message(bot, message):
    """Направляет сообщение в чат телеграмм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(
            f'Сообщение {message} направлено в чат'
        )
        return True
    except Exception:
        logger.exception(
            f'Сообщение {message} не удалось направить в чат'
        )
        return False


def get_api_answer(current_timestamp):
    """Направляет запрос в API сервиса Практикум.Домашка."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except ConnectionError:
        logger.error(
            CONNECTION_ERROR_PHRASE.format(
                endpoint=ENDPOINT,
                headers=HEADERS,
                params=params,
                text=f'вернул {response.text}'
            )
        )
        raise ConnectionError(
            CONNECTION_ERROR_PHRASE.format(
                endpoint=ENDPOINT,
                headers=HEADERS,
                params=params,
                text=f'вернул {response.text}'
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
    if 'code' and 'error' in result:
        raise HTTPError(
            CONNECTION_ERROR_PHRASE.format(
                endpoint=ENDPOINT,
                headers=HEADERS,
                params=params,
                text=f'передан неверный параметр {params}'
            )
        )
    if 'code' in result:
        raise HTTPError(
            CONNECTION_ERROR_PHRASE.format(
                endpoint=ENDPOINT,
                headers=HEADERS,
                params=params,
                text='имеет невалидный токен '
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
        raise KeyError(
            f'Полученный статус {status} несоотвутствует ожидаемым'
        )
    verdict = HOMEWORK_VERDICTS[status]
    return PARSE_STATUS_PHRASE.format(name=name, verdict=verdict)


def check_tokens():
    """Проверяет наличие и валидность необходимых переменных окружения."""
    for name in ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']:
        if globals()[name] != name:
            logging.error(f'Токен {name} отсутствует')
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
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
    from unittest import TestCase, mock, main as uni_main
    RegEx = requests.RequestException
    JSON_ERROR = {'error': 'testing'}
    JSON_HOMEWORK = {
        'homeworks': [{'homework_name': 'test', 'status': 'test'}]
    }
    JSON_DATA = {'homeworks': 1}

    class TestReq(TestCase):
        """Тестирование отработки исключений при запросе на сервер"""
        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            cls.resp = mock.Mock()

        @mock.patch('requests.get')
        def test_error(self, req_get):
            """Запрос выдаст исключение при ошибке сервера."""
            self.resp.json = mock.Mock(
                return_value=JSON_ERROR
            )
            req_get.return_value = self.resp
            req_get.side_effect = mock.Mock(
                side_effect=RegEx('Server Error')
            )
            if 'error' in self.resp.json():
                return req_get.side_effect()
            main()

        @mock.patch('requests.get')
        def test_status_code(self, req_get):
            """Запрос выдаст исключение возврате статуса отличного от 200."""
            self.resp.status_code = mock.Mock(
                return_value=333
            )
            req_get.return_value = self.resp
            req_get.side_effect = mock.Mock(
                side_effect=RegEx('Invalid status code')
            )
            if self.resp.status_code != 200:
                return req_get.side_effect()
            main()

        @mock.patch('requests.get')
        def test_homework_status(self, req_get):
            """Запрос выдаст исключение при невалидном статусе домашнего задания"""
            self.resp.json = mock.Mock(
                return_value=JSON_HOMEWORK
            )
            req_get.return_value = self.resp
            req_get.side_effect = mock.Mock(
                side_effect=RegEx('Unexpected Status')
            )
            if self.resp.json()['homeworks'][0]['homework_name'] == 'test':
                return req_get.side_effect()
            main()

        @mock.patch('requests.get')
        def test_json(self, req_get):
            """Запрос выдаст исключение при невалидном значении ключа 'homeworks'"""
            self.resp.json = mock.Mock(
                return_value=JSON_DATA
            )
            req_get.return_value = self.resp
            req_get.side_effect = mock.Mock(
                side_effect=RegEx('Invalid JSON')
            )
            if not isinstance(self.resp.json()['homeworks'], list):
                return req_get.side_effect()
            main()

    uni_main()
