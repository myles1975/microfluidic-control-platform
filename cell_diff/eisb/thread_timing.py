# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 11:06:43 2019

@author: joeld
"""

from threading import Thread
from queue import Queue
import time
import datetime

def timed_execution(func, interval, *func_args, num_intervals=None, 
                    **func_kwargs):
    '''
    Executes a function at periodic intervals.
    
    Parameters
    ----------
    func : callable
        `func` will be called every `interval` seconds and passed the 
        `func_args` and `func_kwargs` parameters.
    interval : float
        The number of seconds between calls to `func`.
    func_args : iterable, optional
        A list of arguments passed on to `func`.
    num_intervals : int, optional
        The number of executions of `func`. Default is None, in which case the
        loop will continue indefinitely until the user enter "q" in stdin.
    
    Notes
    -----
    In testing, timing seems accurate to hundredths of seconds
    '''
    if num_intervals is not None and num_intervals < 1:
        raise ValueError('max_intervals must be a positive integer')
    q = Queue()
    threads = []
    threads.append( Thread(target=timing_thread, args=(q, interval), 
                kwargs={'max_intervals':num_intervals}) )
    threads.append( Thread(target=execute_thread, args=(q, func)+func_args,
                kwargs=func_kwargs) )
    if num_intervals is None:
        threads.append( Thread(target=wait_for_interrupt, args=(q,)) )
    
    for t in threads:
        t.start()
    
    q.join()
    for t in threads:
        t.join()

def timing_thread(q, interval, max_intervals=None):
    '''
    Adds an "execute" command to the queue at fixed time intervals.
        
    Adds "execute" to queue every `interval` seconds or until `max_intervals` 
    if specified.
    
    Parameters
    ----------
    q : queue.Queue object
        A queue.Queue object will share control signals between threads
    interval : float
        The number of seconds to wait between executes.
    max_intervals : int, optional
        The maximum number of executions to schedule (default is None in which
        case the thread will run indefinitely until a 'quit' signal is on the 
        queue)
        
    Notes
    -----
    If the function called in response to 'execute' commands takes longer to 
    complete than `interval`, the timing will not be preserved.
    '''
    i = 0
    while True:
        if not q.empty():
            task = q.get()
            q.task_done()
            if task == 'quit':
                q.put('quit')
                break
        
        if max_intervals is not None:
            if i >= max_intervals:
                q.put('quit')
                break
        
        q.put('execute')
        i += 1
        time.sleep(interval)

def execute_thread(q, func, *args, sleep_interval=0.001, **kwargs):
    '''
    Executes a function when signalled by the queue.
    
    In a loop, checks the queue for the 'execute' signal. On detection, calls 
    `func` and passes in `args` and `kwargs`.
    
    Parameters
    ----------
    q : queue.Queue object
        A queue.Queue object will to share control signals between threads.
    func : callable
        `func` will be executed on detection of 'execute' signal in `q`.
    args : iterable, optional
        A list of arguments to be passed into `func`.
    sleep_interval : float, optional
        Seconds to wait between loop iterations (the default is 0.001s).
    kwargs : dict, optional
        Keyword argument dict to be passed into `func`.
    '''
    while True:
        if not q.empty():
            task = q.get()
            q.task_done()
            if task == 'quit':
                q.put('quit')
                break
            elif task == 'execute':
                func(*args, **kwargs)
        time.sleep(sleep_interval)
       
def wait_for_interrupt(q, sleep_interval=0.001):
    '''
    Loop that waits for the input "q" and then adds a "quit" signal to queue.
    
    Parameters
    ----------
    q : queue.Queue object
        A queue.Queue object will to share control signals between threads.
    sleep_interval : float, optional
        Seconds to wait between loop iterations (the default is 0.001s).
    '''
    print('enter "q" to exit',end='')
    while True:
        if not q.empty():
            task = q.get()
            q.task_done()
            if task == 'quit':
                q.put('quit')
                break
        x = input("")
        if x == 'q':
            q.put('quit')
            break
        time.sleep(sleep_interval)
        


def test_func(x):
    x.append(str(datetime.datetime.now()))

if __name__ == '__main__':

#    q = Queue()
#    
#    result = [] # must be mutable!!! 
#    t1 = Thread(target=timing_thread, args=(q,2), )#kwargs={'max_intervals':5})
#    t2 = Thread(target=execute_thread, args=(q, test_func, result))
#    t3 = Thread(target=wait_for_interrupt, args=(q,))
#    t1.start()
#    t2.start()
#    t3.start()
#    
#    q.join()
#    
#    t1.join()
#    t2.join()
#    t3.join()
    result=[]
    timed_execution(test_func, 1.0, result, max_intervals=10)
    print(result)
    timed_execution(test_func, 1.0, result)
    print(result)