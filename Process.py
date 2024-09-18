from threading import Lock, Thread

from time import sleep

#from geeteventbus.subscriber import subscriber
#from geeteventbus.eventbus import eventbus
#from geeteventbus.event import event

#from EventBus import EventBus
from Bidule import Bidule

from pyeventbus3.pyeventbus3 import *


class Process(Thread):
        
    nbProcessCreated = 0
    def __init__(self, name, npProcess):
        Thread.__init__(self)

        self.npProcess = npProcess
        self.myId = Process.nbProcessCreated
        Process.nbProcessCreated +=1
        self.myProcessName = name
        self.setName("MainThread-" + name)

        PyBus.Instance().register(self, self)

        self.alive = True
        self.start()
        


    @subscribe(threadMode = Mode.PARALLEL, onEvent=Bidule)
    def process(self, event):        
        print(threading.current_thread().name + ' Processes event: ' + event.getMachin())

    def run(self):
        loop = 0
        while self.alive:
            print(self.getName() + " Loop: " + str(loop))
            sleep(1)

            if self.myProcessName == "P1":
                b1 = Bidule("ga")
                b2 = Bidule("bu")
                print(self.getName() + " send: " + b1.getMachin())
                PyBus.Instance().post(b1)
                

            loop+=1
        print(self.getName() + " stopped")

    def stop(self):
        self.alive = False

    def waitStopped(self):
        self.join()
