import threading, shutil

class Module (threading.Thread):
    def __init__(self, dependences, stop):
        super().__init__(self)
        self.stop = stop
        self.dependences = dependences

    def checkDependences(self):
        for d in self.dependences:
            if not shutil.which(d):
                print('%s not found in PATH', d)
                return False
        return True