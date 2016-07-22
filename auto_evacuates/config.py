from ConfigParser import RawConfigParser, NoOptionError, NoSectionError
from log import logger

FILE_PATH = '/etc/autoevacuate/evacuate.conf'


class Config(RawConfigParser):
    """ Load config file"""
    def __init__(self):
        RawConfigParser.__init__()

    def read_file(self, file_name):
        file_name = file_name
        try:
            RawConfigParser.read(self, file_name)
        except TypeError:
            RawConfigParser.read(self, file_name)

    def _get(self, option, section):
        """facility for RawCOnfigParser.get"""
        try:
            return RawConfigParser.get(self, section, option)
        except (NoOptionError, NoSectionError):
            msg = (NoOptionError, NoSectionError)
            logger.warn(msg)

CONF = Config()
