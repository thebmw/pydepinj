from typing import Type, Callable, TypeVar
from abc import ABCMeta, ABC
from functools import wraps
from inspect import signature
from threading import local
from contextlib import contextmanager

from pprint import pprint

T = TypeVar('T')

_thread_local = local()

class ScopeHandler:
    def setup_cache(self):
        _thread_local.di_scoped_cache = {}

    def get_cache(self) -> dict:
        scoped_cache = getattr(_thread_local, 'di_scoped_cache', None)
        return scoped_cache
    
    def del_cache(self):
        scoped_cache = getattr(_thread_local, 'di_scoped_cache', None)
        if scoped_cache is not None:
            del _thread_local.di_scoped_cache

class DependencyInjection:
    """
        Simple Dependency Injection Framework for Python
    """
    _singleton_cache: dict[ABCMeta, any]
    _singleton_types: dict[ABCMeta, ABCMeta]
    _scoped_types: dict[ABCMeta, ABCMeta]
    _transient_types: dict[ABCMeta, ABCMeta]
    _scope_cache: ScopeHandler

    _locked: bool = False
    
    def __init__(self) -> None:
        self._singleton_cache = {}
        self._singleton_types = {}
        self._scoped_types = {}
        self._transient_types = {}
        self._scope_cache = ScopeHandler()

    def set_scope_cache_handler(self, scope_cache: ScopeHandler):
        self._scope_cache = scope_cache

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
            self._scope_cache.setup_cache()
            yield
        finally:
            self._scope_cache.del_cache()

    def make_injected_call(self, func: Callable, *args, **kwargs):
        s = signature(func)
        new_kwargs = {
            **kwargs
        }
        for name, info in s.parameters.items():
            instance = self.get_instance(info.annotation)
            if instance is not None:
                new_kwargs[name] = instance

        return func(*args, **new_kwargs)

    def inject(self, func: Callable):
        """Wraps functions/classes to auto inject dependencies"""
        @wraps(func)
        def inner(*args, **kwargs):
            return self.make_injected_call(func, *args, **kwargs)
        return inner
    
    def scoped_inject(self, func: Callable):
        """Wraps functions/classes to auto inject dependencies. Scope is auto generated for the functions this wraps."""
        @wraps(func)
        def inner(*args, **kwargs):
            with self.di_scope():
                return self.make_injected_call(func, *args, **kwargs)
        return inner

    def register_singleton(self, base_type: Type[T], implementation_type: Type[T]):
        assert not self._locked
        self._singleton_types[base_type] = implementation_type

    def register_singleton_instance(self, base_type: Type[T], instance: T):
        assert not self._locked
        self._singleton_cache[base_type] = instance
        self._singleton_types[base_type] = None

    def register_scoped(self, base_type: Type[T], implementation_type: Type[T]):
        assert not self._locked
        self._scoped_types[base_type] = implementation_type

    def register_transient(self, base_type: Type[T], implementation_type: Type[T]):
        assert not self._locked
        self._transient_types[base_type] = implementation_type

    def _get_scoped_instance(self, base_type: Type[T]):
        scoped_cache = self._scope_cache.get_cache()
        if scoped_cache is None:
            raise Exception('Can not use scoped types outside of scope')
        if base_type in scoped_cache:
            return scoped_cache[base_type]
        if base_type in self._scoped_types:
            i = self._scoped_types[base_type]()
            scoped_cache[base_type] = i
            return i
        return None

    def get_instance(self, base_type: Type[T]) -> T:
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
    
    def validate_and_lock(self):
        self._locked = True

        for interface, impl in self._singleton_types.items():
            s = signature(impl)
            for name, info in s.parameters.items():
                if info.annotation in self._scoped_types.keys() or info.annotation in self._transient_types.keys():
                    raise Exception('Singleton Types can not depend on Scoped or Transient Types')
                
        for interface, impl in self._scoped_types.items():
            s = signature(impl)
            for name, info in s.parameters.items():
                if info.annotation in self._transient_types.keys():
                    raise Exception('Scoped Types can not depend on Transient Types')