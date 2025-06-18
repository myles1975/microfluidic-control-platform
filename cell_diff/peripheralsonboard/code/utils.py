# -*- coding: utf-8 -*-
"""
Created on Tue Jun  6 13:55:47 2023

@author: joeld
"""

import time
import threading

def test_func(a,b):
    print(str(a))
    time.sleep(a)
    print(str(b))
    time.sleep(b)

class InterruptThread(threading.Thread):
    '''
    A Thread subclass that executes the target function continuously until 
    stopped by InterruptThread.stop().
    
    Note that this is not a true interrupt. Rather, the interrupt flag is 
    checked only after each successful execution of the target function.
    '''

    def __init__(self, *args, **kwargs):
        '''
        Note that target must not be a function with an argument that has a 
        member that points to this thread or a refcycle will occur
        
        Parameters
        ----------
        timeout : int
            Timeout in number of seconds. Default is None, in which case the 
            thread will execute indefinitely until stopped.
        **kwargs : dict
            keyword arguments passed on to parent constructor

        '''
        self.timeout=None
        if 'timeout' in kwargs:
            self.timeout = kwargs.pop('timeout')
        super(InterruptThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()
			
    def run(self):
        start = time.time()
		# target function of the thread class
        while True:
            if self._target is not None:
                self._target(*self._args, **self._kwargs)
                
            if self.stopped(): break
            if self.timeout and time.time()-start > self.timeout: break
		
    def interrupt(self):
        self._stop_event.set()
        
    def stopped(self):
        return self._stop_event.is_set()
    
if __name__ == '__main__':
    
    # now target just has to implement one period of PWM!
    t1 = InterruptThread(target=test_func, kwargs={'a':.5,'b':1.5})
    t1.start()
    time.sleep(10)
    t1.interrupt()
    t1.join()
    
    t1 = InterruptThread(target=test_func, kwargs={'a':.1,'b':.7})
    t1.start()
    time.sleep(10)
    t1.interrupt()
    t1.join()