#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import update_wrapper


def disable(*args, **kwargs):
    '''
    Disable a decorator by re-assigning the decorator's name
    to this function. For example, to turn off memoization:

    >>> memo = disable

    '''
    def wrapper_decorator(func):
        return func

    return wrapper_decorator


def decorator(inside_decorator):
    '''
    Decorate a decorator so that it inherits the docstrings
    and stuff from the function it's decorating.
    '''
    def wrapper_decorator(func):
        wrapper = inside_decorator(func)

        if not hasattr(func, '__wrapped__'):
            update_wrapper(wrapper, func)
            return wrapper

        def inside_wrapper(*args, **kwargs):
            res = wrapper(*args, **kwargs)
            # copy attributes of wrapper in case it has state
            update_wrapper(inside_wrapper, wrapper)
            # copy attributes of inner function
            # in case it has it's own state
            update_wrapper(inside_wrapper, func)

            return res

        # if something is 'stacked' above, __wrapped__
        # must be set to correctly copy insides
        update_wrapper(inside_wrapper, func)
        return inside_wrapper

    return wrapper_decorator


@decorator
def countcalls(func):
    '''Decorator that counts calls made to the function decorated.'''
    def wrapper(*args, **kwargs):
        wrapper.calls += 1
        return func(*args, **kwargs)

    wrapper.calls = 0

    return wrapper


@decorator
def memo(func):
    '''
    Memoize a function so that it caches all return values for
    faster future lookups.

    NB: only works with hashable args
    '''

    def wrapper(*args):
        if (*args,) in wrapper.results_memo:
            return wrapper.results_memo[(*args,)]

        ret = func(*args)
        wrapper.results_memo[(*args,)] = ret
        return ret

    wrapper.results_memo = {}

    return wrapper


@decorator
def n_ary(func):
    '''
    Given binary function f(x, y), return an n_ary function such
    that f(x, y, z) = f(x, f(y,z)), etc. Also allow f(x) = x.
    '''
    def wrapper(*args):
        if len(args) == 1:
            return args[0]

        return func(args[0], wrapper(*args[1:]))

    return wrapper


def trace(indent):
    '''Trace calls made to function decorated.

    @trace("____")
    def fib(n):
        ....

    >>> fib(3)
     --> fib(3)
    ____ --> fib(2)
    ________ --> fib(1)
    ________ <-- fib(1) == 1
    ________ --> fib(0)
    ________ <-- fib(0) == 1
    ____ <-- fib(2) == 2
    ____ --> fib(1)
    ____ <-- fib(1) == 1
     <-- fib(3) == 3

    '''
    @decorator
    def inside_decorator(func):
        def wrapper(arg):
            print(wrapper.level * indent, end=' ')
            print(f'--> {func.__name__}({arg})')
            wrapper.level += 1
            ret_value = func(arg)
            wrapper.level -= 1
            print(wrapper.level * indent, end=' ')
            print(f'<-- {func.__name__}({arg}) == {ret_value}')

            return ret_value

        wrapper.level = 0
        return wrapper

    return inside_decorator


@memo
@countcalls
@n_ary
def foo(a, b):
    return a + b


@countcalls
@memo
@n_ary
def bar(a, b):
    return a * b


@countcalls
@trace("####")
@memo
def fib(n):
    """Some doc"""
    return 1 if n <= 1 else fib(n-1) + fib(n-2)


def main():
    print(foo(4, 3))
    print(foo(4, 3, 2))
    print(foo(4, 3))
    print("foo was called", foo.calls, "times")

    print(bar(4, 3))
    print(bar(4, 3, 2))
    print(bar(4, 3, 2, 1))
    print("bar was called", bar.calls, "times")

    print(fib.__doc__)
    fib(3)
    print(fib.calls, 'calls made')


if __name__ == '__main__':
    main()
