"""Parallel building utilities."""

import traceback
import multiprocessing
import multiprocessing.context
import multiprocessing.connection
import multiprocessing.pool
from typing import Any, Callable, List, Sequence

from sphinx.errors import SphinxParallelError
from sphinx.util import logging, status_iterator
from sphinx.locale import __
from sphinx.util.console import bold  # type: ignore

logger = logging.getLogger(__name__)


class SerialTasks:
    """Has the same interface as ParallelTasks, but executes tasks directly."""

    def __init__(self, nproc: int = 1) -> None:
        pass

    def add_task(self, task_func: Callable, arg: Any = None, result_func: Callable = None) -> None:  # NOQA
        if arg is not None:
            res = task_func(arg)
        else:
            res = task_func()
        if result_func:
            result_func(res)

    def join(self) -> None:
        pass


def _process(func: Callable, *args: Any):
    collector = logging.LogCollector()
    with collector.collect():
        ret = func(*args)
        raise SystemError("!!!")
    logging.convert_serializable(collector.logs)
    return {'logs': collector.logs, 'value': ret, 'arg': args[-1]}


def make_chunks(arguments: Sequence[str], nproc: int) -> List[Any]:
    nargs = len(arguments)
    chunksize = min(1, nargs // nproc)
    nchunks = -(nargs // -chunksize)  # upside-down floor division
    return [arguments[i * chunksize:(i + 1) * chunksize] for i in range(nchunks)]


def parallel_status_iterator(nproc: int, docnames: Sequence[str], status_message: str, colour: str, verbosity: int, chunk_preprocessor, task_func, callback, extra_args=()):
    if chunk_preprocessor is None:
        def chunk_preprocessor(chunk):
            return chunk

    with multiprocessing.pool.Pool(nproc, context=multiprocessing.context.SpawnContext()) as pool:
        results = [
            pool.apply_async(_process, (task_func, chunk_preprocessor(chunk), *extra_args), {}, callback)
            for chunk in status_iterator(make_chunks(docnames, nproc), status_message, colour, verbosity=verbosity)
        ]

        # make sure all threads have finished
        logger.info(bold(__('waiting for workers...')))
        processing = len(results)
        while processing > 0:
            for result in results:
                result.wait(0.01)
                if not result.ready():
                    continue

                try:
                    ret = result.get(timeout=0)
                except Exception as err:
                    raise SphinxParallelError(
                        traceback.format_exception_only(None, err)[0].strip(),
                        "".join(traceback.format_exception(err))
                    ) from err

                if not result.successful():
                    err: BaseException = ret  # type: ignore
                    raise SphinxParallelError(
                        traceback.format_exception_only(None, err)[0].strip(),
                        "".join(traceback.format_exception(err))
                    ) from ret

                for log in ret["logs"]:
                    logger.handle(log)

                processing -= 1
