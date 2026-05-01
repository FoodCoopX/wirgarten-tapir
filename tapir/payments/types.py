from typing import Callable

type TokenReplacers = dict[str, Callable[[], str]]
