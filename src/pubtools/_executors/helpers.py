import functools
import logging
import time

LOG = logging.getLogger("pubtools.executors")
MAX_RETRY_WAIT = 120


def run_with_retries(function, message, tries=4, wait_time_increase=10):
    """
    Run the specified function until it succeeds or maximum retries are reached.

    Wait time will increase after every retry, up to a point defined by MAX_RETRY_WAIT.

    Args:
        function (callable):
            Function that should be retried. It must be able to run with 0 parameters.
        message (str):
            Message describing the action performed by the function. For example, "tag images".
        tries (int):
            Numbers of times to run the function before giving up.
        wait_time_increase (int):
            Time increase (in seconds) to wait before running the function again. Example (default):
            RUN -> WAIT 0 -> RUN -> WAIT 10 -> RUN -> WAIT 20 -> RUN
    """
    wait_time = 0
    for i in range(tries):
        try:
            result = function()
            if i != 0:
                LOG.info("%s succeeded [try: %s/%s]" % (message, i + 1, tries))
            return result
        except Exception as e:
            if i < tries - 1:
                wait_time = i * wait_time_increase if wait_time < MAX_RETRY_WAIT else MAX_RETRY_WAIT
                LOG.warning(
                    "%s failed. Will retry in %d seconds [try %s/%s]: %s"
                    % (message, wait_time, i + 1, tries, str(e))
                )
                time.sleep(wait_time)
                continue
            LOG.error("%s repeatedly fails" % message)
            raise


def retry(message, tries=4, wait_time_increase=10):
    """
    Retry decorated function.

    Args:
        message (str):
            Message describing the action performed by the function. For example, "tag images".
        tries (int):
            Numbers of times to run the function before giving up.
        wait_time_increase (int):
            Time increase (in seconds) to wait before running the function again. Example (default):
            RUN -> WAIT 0 -> RUN -> WAIT 10 -> RUN -> WAIT 20 -> RUN
    """

    def inner_retry(func):
        @functools.wraps(func)
        def wrapper_func(*args, **kwargs):
            bound = functools.partial(func, *args, **kwargs)
            return run_with_retries(bound, message, tries, wait_time_increase)

        return wrapper_func

    return inner_retry
