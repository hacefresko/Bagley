import threading, shutil, datetime, time, traceback

class Module (threading.Thread):
    def __init__(self, dependences, controller, stop, rps=None, active_modules=None, lock=None, submodules=[]):
        super().__init__()
        self.dependences = dependences
        self.controller = controller
        self.stop = stop
        self.rps = None
        self.active = None
        self.active_modules = None
        self.lock = None
        self.submodules = submodules
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

    def applyDelay(self):
        if (datetime.datetime.now() - self.t).total_seconds() < self.getDelay():
            t = self.getDelay() - (datetime.datetime.now() - self.t).total_seconds()
            if t > 0:
                time.sleep(t)

    def updateDelay(self):
        self.t = datetime.datetime.now()

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

    def send_msg(self, msg, channel):
        self.controller.send_msg(msg, channel)

    def send_error_msg(self, msg, channel):
        self.controller.send_error_msg(msg, channel)

    def send_vuln_msg(self, msg, channel):
        self.controller.send_vuln_msg(msg, channel)

    def send_file(self, filename, channel):
        self.controller.send_file(filename, channel)
    