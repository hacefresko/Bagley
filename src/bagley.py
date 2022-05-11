import urllib3
import logging, config, lib.controller

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

# Disable SSL requests warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create logger
logger = logging.getLogger("bagley")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s'))
logger.addHandler(handler)
logger.info(title)

# Init bot
lib.controller.Controller(logger)