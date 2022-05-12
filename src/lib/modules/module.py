import threading, shutil, datetime, time, traceback

class Module (threading.Thread):
    def __init__(self, dependencies, controller, stop, rps=None, active_modules=None, lock=None, submodules=[]):
        super().__init__()
        self.dependencies = dependencies    # List of dependencies that the module has
        self.controller = controller        # Controller instance
        self.stop = stop                    # External global variable to used to stop module
        self.submodules = submodules        # Submodules available in this module
        
        # All this variables must be valid. If one of them is None, all of them will be None
        if (rps is not None) and (active_modules is not None) and (lock is not None):
            self.rps = rps                          # Limit of requests per second of the system (to compute delay)
            self.active = False                     # Indicates if module is active or not
            self.active_modules = active_modules    # External counter of active modules
            self.lock = lock                        # External lock for active_modules variable
            self.t = datetime.datetime.now()        # Initialize last time that the module made a request
        else:
            self.rps = None                  
            self.active = None            
            self.active_modules = None
            self.lock = None

    # Check dependencies of the modules
    def checkDependencies(self):
        for d in self.dependencies:
            if not shutil.which(d):
                msg = '%s not found in PATH' % d
                raise Exception(msg)


    # Methods regarding traffic control

    # Compute the delay that must be applied between each request based on which modules are active
    # and the requests per second
    def getDelay(self):
        if (self.active_modules is not None) and (self.rps is not None):
            return self.active_modules/self.rps
        else:
            return None

    # Apply delay
    def applyDelay(self):
        if (self.active_modules is not None) and (self.rps is not None):
            # If the time elpased between last request is less than the delay, apply the difference
            if (datetime.datetime.now() - self.t).total_seconds() < self.getDelay():
                t = self.getDelay() - (datetime.datetime.now() - self.t).total_seconds()
                if t > 0:
                    time.sleep(t)

    # Update delay timer (must be done after every call to applyDelay())
    def updateLastRequest(self):
        self.t = datetime.datetime.now()

    # Set module as innactive
    def setInactive(self):
        if (self.active is not None) and (self.active_modules is not None) and (self.lock is not None) and (self.active):
            self.active = False
            self.lock.acquire()
            self.active_modules -= 1
            self.lock.release()

    # Set module as active
    def setActive(self):
        if (self.active is not None) and (self.active_modules is not None) and (self.lock is not None) and (not self.active):
            self.active = True
            self.lock.acquire()
            self.active_modules += 1
            self.lock.release()


    # Methods to communicate with controller

    # Send message to controller
    def send_msg(self, msg, channel):
        self.controller.send_msg(msg, channel)

    # Send error message to controller
    def send_error_msg(self, msg, channel):
        self.controller.send_error_msg(msg, channel)

    # Send vulnerability message to controller
    def send_vuln_msg(self, msg, channel):
        self.controller.send_vuln_msg(msg, channel)

    # Send file to controller
    def send_file(self, filename, channel):
        self.controller.send_file(filename, channel)
    