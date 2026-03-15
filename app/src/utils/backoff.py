import logging
import time
from functools import wraps

from redis.exceptions import ConnectionError as RedisError

logger = logging.getLogger(__name__)


def backoff(
    error_connection: type[RedisError],
    start_sleep_time: float = 0.1,
    factor: int = 2,
    border_sleep_time: int = 10,
    max_attempts: int = 15,
):
    """
    Функция для повторного выполнения подключения с ожиданием.
    Если возникает ошибка
    """

    def func_wrapper(func: callable):
        @wraps(func)
        def inner(*args, **kwargs):
            sleep_time = start_sleep_time
            attempts = 0

            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except error_connection as error:
                    attempts += 1
                    sleep_time = min(sleep_time * 2**factor, border_sleep_time)

                    logger.exception(
                        'Ошибка подключения в функции "%s": %s. '
                        "Повторная попытка через %s секунд... (Попытка %d/%d)",
                        func.__name__,
                        error,
                        sleep_time,
                        attempts,
                        max_attempts,
                    )

                    time.sleep(sleep_time)

            logger.error(
                "Достигнуто максимальное количество " 'попыток в функции "%s". Функция завершилась с ошибкой.',
                func.__name__,
            )
            return None

        return inner

    return func_wrapper
