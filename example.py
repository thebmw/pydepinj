from abc import ABC, abstractmethod
from pydepinj import DependencyInjection

di = DependencyInjection()

class ITest(ABC):
    @abstractmethod
    def test(self):
        pass

class Test(ITest):
    def test(self):
        print('hi')

di.register_singleton(ITest, Test)    

t: ITest = di.get_instance(ITest)
t.test()

@di.inject
def test(test: ITest = None):
    test.test()

test()

class IFoo(ABC):
    @abstractmethod
    def do_test(self):
        pass

@di.inject
class Foo(IFoo):
    test: ITest

    def __init__(self, test: ITest = None) -> None:
        self.test = test
    
    def do_test(self):
        self.test.test()

di.register_scoped(IFoo, Foo)

with di.di_scope():
    foo: IFoo = di.get_instance(IFoo)

    foo.do_test()

foo: IFoo = di.get_instance(IFoo)

foo.do_test()