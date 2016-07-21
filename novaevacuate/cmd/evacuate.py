from novaevacuate.app import manage
import time
import os

def main():
    """use main function load manage.manager functiong,
    the program until background running

    """
    pid = os.fork()
    if pid == 0:
        os.setsid()
        pid = os.fork()

        if pid == 0:
            os.chdir("/")
            os.umask(0)

            while True:
                manage.manager()
                time.sleep(30)
        else:
            os._exit(0)
    else:
        os._exit(0)

if __name__ == "__main__":
    main()