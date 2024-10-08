import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from telegram.error import TelegramError

from exceptions import ApiAccessError, ApiUrlError

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
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)


def check_tokens():
    """Проверка токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


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
            raise ApiUrlError
        logging.debug(f'Отправка запроса к {ENDPOINT} успешна.')
        return homework_statuses.json()
    except requests.RequestException as e:
        logging.error('Ошибка доступа', e)
        raise ApiAccessError


def check_response(response):
    """Функция проверяет ответ API на соответствие документации.
    из урока API сервиса Практикум.Домашка.
    """
    if not isinstance(response, dict):
        raise TypeError('Данные не в виде словаря.')
    if 'current_date' not in response:
        raise KeyError('В ответе от API нет ключа "current_date".')
    if 'homeworks' not in response:
        raise KeyError('В ответе от API нет ключа "homeworks".')
    homeworks_list = response.get('homeworks')
    if not isinstance(homeworks_list, list):
        raise TypeError('Данные не в виде списка.')
    return homeworks_list


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе.
    статус этой работы.
    """
    status_work = ['homework_name', 'status']
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    for name in status_work:
        if name not in homework:
            raise KeyError('Проект не найден.')
    if status not in HOMEWORK_VERDICTS:
        raise KeyError('Отсутствуют данные о результате проекта.')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Функция отправляет сообщение в Telegram чат."""
    logging.info('Начинаем отправку сообщения.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено: {message}.')
    except TelegramError:
        logging.error('Ошибка при отправке сообщения: {telegram_error}.')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует обязательная переменная окружения')
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks_list = check_response(response)
            if homeworks_list:
                message = parse_status(homeworks_list[0])
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
