import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import time

import requests
import telebot
from http import HTTPStatus
from dotenv import load_dotenv
from telebot import TeleBot

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='program.log',
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_logger.log',
    maxBytes=50000000,
    backupCount=5
)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

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


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = (
        ('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
        ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
        ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID),
    )
    token_availability = True
    for key, value in tokens:
        if not value:
            token_availability = False
            logger.critical(f'Отсутсвует токен {key}.')
    if not token_availability:
        raise KeyError('Отсутсвуют токены')

    return token_availability


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telebot.apihelper.ApiException as error:
        logger.error(f'Ошибка отправки запроса в telegram {error}')
        return False
    except requests.RequestException as error:
        logger.error(f'Ошибка при отпрваке запроса {error}')
        return False
    except Exception as error:
        logging.exception(f'Ошибка отправки сообщения: {error}')
    else:
        logger.debug('Сообщение отправлено')
    return True


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    try:
        payload = {'from_date': timestamp}
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
    except requests.RequestException as error:
        logger.error(f'Ошибка при запросе к API-сервиса: {error}'
                     f'Url запроса {ENDPOINT}'
                     f'Заголовок запрса {HEADERS}'
                     f'Параметры запроса {payload}'
                     )
    if homework_statuses.status_code != HTTPStatus.OK:
        logger.error('Ошибка при запросе к API-сервиса')
        raise ValueError(f'При запросе к API-сервиса возникла ошибка: '
                         f'{homework_statuses.status_code}')
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(f'Ожидался словарь, но получен другой тип данных '
                        f'{type(response)}')
    if response.get('homeworks') == []:
        logger.debug('Статус домашней работы не изменился')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError(f'Ожидался список, но получен другой тип данных '
                        f'{type(response)}')


def parse_status(homework):
    """Извлекает статус работы."""
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)
    if 'homework_name' not in homework:
        raise KeyError('Отсутсвуют ключ homework_name')
    homework_name = homework.get('homework_name')
    if not verdict:
        raise KeyError(f'Неопределенный статус домашнего задания {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(
            'Отсутсвует обязательная переменная окружения'
        )
        sys.exit()

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    prev_status = None

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework = response.get('homeworks')[0]
            if prev_status != homework.get('status'):
                message = parse_status(homework)
                send_message(bot, message)
                prev_status = homework.get('status')
                timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename=(__file__) + '.log',
    )

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    main()
