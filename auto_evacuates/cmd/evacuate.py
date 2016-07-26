from auto_evacuates.app import manage
from auto_evacuates.novacheck.network.network import Net_Interface
from auto_evacuates.log import logger
import time
import os


def main():
    """the program until background running"""

    led = Net_Interface()
    pid = os.fork()
    if pid == 0:
        os.setsid()
        while True:
            try:
                if led.leader():
                    manage.manager()
                else:
                    logger.info("This node is not the leader,"
                                "no need to do any check")
            except Exception as e:
                logger.error("Failed to auto evacuate: %s" % e)
            time.sleep(30)
    else:
        os._exit(0)

if __name__ == "__main__":
    main()
