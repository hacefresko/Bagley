import threading, shutil

class Module (threading.Thread):
    def __init__(self, dependences, stop, rps=None, active_modules=None, lock=None):
        super().__init__()
        self.dependences = dependences
        self.stop = stop
        if rps is not None and active_modules is not None and lock is not None:
            self.rps = rps
            self.active = False
            self.active_modules = active_modules
            self.lock = lock

    def checkDependences(self):
        for d in self.dependences:
            if not shutil.which(d):
                msg = '%s not found in PATH' % d
                raise Exception(msg)

    def getDelay(self):
        if self.active_modules is not None and self.rps is not None:
            return self.active_modules/self.rps
        else:
            return None

    def setInactive(self):
        if self.active is not None and self.active_modules is not None and self.lock is not None and self.active == True:
            self.active = False
            self.lock.acquire()
            self.active_modules -= 1
            self.lock.release()

    def setActive(self):
        if self.active is not None and self.active_modules is not None and self.lock is not None and self.active == False:
            self.active = True
            self.lock.acquire()
            self.active_modules += 1
            self.lock.release()