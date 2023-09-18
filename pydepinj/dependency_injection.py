from typing import Type, Callable
from abc import ABCMeta
from functools import wraps
from inspect import signature
from threading import local
from contextlib import contextmanager

from pprint import pprint

_thread_local = local()

class DependencyInjection:
    """
        Simple Dependency Injection Framework for Python
    """
    _singleton_cache: dict[ABCMeta, any]
    _singleton_types: dict[ABCMeta, ABCMeta]
    _scoped_types: dict[ABCMeta, ABCMeta]
    _transient_types: dict[ABCMeta, ABCMeta]
    
    def __init__(self) -> None:
        self._singleton_cache = {}
        self._singleton_types = {}
        self._scoped_types = {}
        self._transient_types = {}

    @contextmanager
    def di_scope(self):
        """
        Scope Context Helper

        Example:
            with di.di_scope():
                foo = di.get_instance(IFoo)
                foo.test()
        """
        try:
            scoped_cache = getattr(_thread_local, 'di_scoped_cache', None)
            if scoped_cache is not None:
                # TODO something
                pass
            _thread_local.di_scoped_cache = {}
            yield
        finally:
            _thread_local.di_scoped_cache = None

    def inject(self, func: Callable):
        """Wraps functions/classes to auto inject dependencies"""
        @wraps(func)
        def inner(*args, **kwargs):
            s = signature(func)
            new_kwargs = {
                **kwargs
            }
            for name, info in s.parameters.items():
                instance = self.get_instance(info.annotation)
                if instance is not None:
                    new_kwargs[name] = instance

            return func(*args, **new_kwargs)
        return inner
    
    def scoped_inject(self, func: Callable):
        """Wraps functions/classes to auto inject dependencies. Scope is auto generated for the functions this wraps."""
        @wraps(func)
        def inner(*args, **kwargs):
            s = signature(func)
            new_kwargs = {
                **kwargs
            }

            with self.di_scope():
                for name, info in s.parameters.items():
                    instance = self.get_instance(info.annotation)
                    if instance is not None:
                        new_kwargs[name] = instance

                return func(*args, **new_kwargs)
        return inner

    def register_singleton(self, base_type: ABCMeta, implementation_type: ABCMeta):
        self._singleton_types[base_type] = implementation_type

    def register_singleton_instance(self, base_type: ABCMeta, instance: any):
        self._singleton_cache[base_type] = instance
        self._singleton_types[base_type] = None

    def register_scoped(self, base_type: ABCMeta, implementation_type: ABCMeta):
        self._scoped_types[base_type] = implementation_type

    def register_transient(self, base_type: ABCMeta, implementation_type: ABCMeta):
        self._transient_types[base_type] = implementation_type

    def _get_scoped_instance(self, base_type: ABCMeta):
        scoped_cache = getattr(_thread_local, 'di_scoped_cache', None)
        if scoped_cache is None:
            raise Exception('Can not use scoped types outside of scope')
        if base_type in scoped_cache:
            return scoped_cache[base_type]
        if base_type in self._scoped_types:
            i = self._scoped_types[base_type]()
            scoped_cache[base_type] = i
            return i
        return None

    def get_instance(self, base_type: ABCMeta) -> any:
        if base_type == DependencyInjection:
            return self
        elif base_type in self._singleton_cache:
            return self._singleton_cache[base_type]
        elif base_type in self._singleton_types:
            i = self._singleton_types[base_type]()
            self._singleton_cache[base_type] = i
            return i
        elif base_type in self._scoped_types:
            return self._get_scoped_instance(base_type)
        elif base_type in self._transient_types:
            return self._transient_types[base_type]()
        return None