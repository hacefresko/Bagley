import threading, shutil

class Module (threading.Thread):
    def __init__(self, dependences, stop, delay=None):
        super().__init__()
        self.dependences = dependences
        self.stop = stop
        if delay:
            self.delay = delay

    def checkDependences(self):
        for d in self.dependences:
            if not shutil.which(d):
                msg = '%s not found in PATH' % d
                raise Exception(msg)