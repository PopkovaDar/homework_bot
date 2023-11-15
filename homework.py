import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ApiUrlError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)


def check_tokens():
    """Проверка токенов."""
    environment_variables = all([
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ])
    if not environment_variables:
        logging.critical('Отсутствует обязательная переменная окружения')
        raise ValueError('Отсутствует переменная окружения')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.."""
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            logging.error(f'Ошибка при запросe к эндпоинту {ENDPOINT}')
            raise ApiUrlError
        logging.debug(f'Отправка запроса к {ENDPOINT} успешна.')
        return homework_statuses.json()
    except requests.RequestException as e:
        logging.error('Ошибка доступа', e)


def check_response(response):
    """Функция проверяет ответ API на соответствие документации.
    из урока API сервиса Практикум.Домашка.
    """
    try:
        response = response['homeworks']
    except KeyError:
        raise KeyError('Список "homeworks" пуст.')
    if not isinstance(response, list):
        raise TypeError('Данные не в виде списка.')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе.
    статус этой работы.
    """
    status_work = ['homework_name', 'status']
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    for name in status_work:
        if name not in homework:
            logging.error(
                f'Данные о результатах проекта отсутствуют {status_work}.'
            )
            raise KeyError('Проект не найден.')
    if status not in HOMEWORK_VERDICTS:
        logging.debug(f'Проект {homework_name} еще не проверен.')
        raise KeyError('Отсутствуют данные о результате проекта.')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Функция отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено.')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения {error}')


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            timestamp = int(time.time())
            response = get_api_answer(timestamp)
            check_response(response)
            if response['homeworks']:
                message = parse_status(response['homeworks'][0])
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
