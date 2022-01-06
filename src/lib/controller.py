import threading
import lib.modules

stopThread = threading.Event()
title = '''

                  @@@*=*@@@
               @@@%+ =*= +%@@@
           @@@@#=  *%@@@%*  =#@@@@
       @@@@%+  =#@@@@@@@@@@@#=  +%@@@@
     @@@@*=    -*@@@@@@@@@@%*-    =#@@@@ 
 @@@@%+  =#@ *@%+  =#@@@#=  +%@* @#=  +%@@@@
@@*=  *%@@@@ *@@@@@* -+- *@@@@@* @@@@%+  =#@@
@@ =@@@@@@@@ *@@@@@@@# #@@@@@@@* @@@@@@@@* @@
@@ =@@@@@@%  #@@@@@@@# #@@@@@@@#  %@@@@@@* @@
@@ =@@@#  -%@@@@@@@@@# #@@@@@@@@@#  -*%@@* @@
@@ -+  =#@@@@@@@@@@@@# #@@@@@@@@@@@@%+  == @@
@@   #@@@@@@@@@@@@@@@   @@@@@@@@@@@@@@@#   @@
@@ -+-.=*@@@@@@@@#-  %@%  -#@@@@@@@@*  =*+ @@
@@ *@@@#=  %@%+  -#@@@@@@@*-  +%@%  =#@@@* @@
@@ *@@@@@@@   +%@@@@@@@@@@@@@%+   @@@@@@@* @@
@@ *@@@@@@@% *@@@@@@@@@@@@@@@@@* @@@@@@@@* @@
@@ =@@@@@@@# #@@@@@@@#+#@@@@@@@* @@@@@@@@= @@
@@#=  +#@@@# %@@@@%+ =+= +%@@@@* @@@@%+  =#@@
  @@@%*   ** %@*=  *%@@@%+  =#@* @*   *%@@@
    @@@@@#+    +#@@@@@@@@@@@#=    +#@@@@@
       @@@@@*  -*@@@@@@@@@@@*-  *@@@@@
          @@@@@#+  +#@@@%+  +#@@@@@
              @@@@@* =*= *@@@@@
                  @@@*=*@@@

        ____              _            
       | __ )  __ _  __ _| | ___ _   _ 
       |  _ \ / _' |/ _' | |/ _ \ | | |
       | |_) | (_| | (_| | |  __/ |_| |
       |____/ \__,_|\__, |_|\___|\__, |
                    |___/        |___/ 

'''

crawler = lib.modules.Crawler(stopThread)
finder = lib.modules.Finder(stopThread, crawler)
injector = lib.modules.Injector(stopThread)
dynamic_analyzer = lib.modules.Dynamic_Analyzer(stopThread)
static_analyzer = lib.modules.Static_Analyzer(stopThread)

threads = [
    crawler,
    finder,
    injector,
    dynamic_analyzer,
    static_analyzer
]

def start():
    for t in threads:
        t.start()

def stop():
    stopThread.set()
    for thread in threads:
        thread.join()