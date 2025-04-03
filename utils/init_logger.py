import logging
import os
from logging.handlers import TimedRotatingFileHandler

CUR_DIR = os.path.abspath(os.path.dirname(__file__))

formatter = logging.Formatter("[%(asctime)s.%(msecs)03d] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
                              datefmt="%Y-%m-%d %H:%M:%S")

logger = logging.getLogger()
logger.setLevel(logging.INFO)  # logger.setLevel(logging.ERROR)

# base_log_dir = os.path.join(CUR_DIR, '../logs')
# if not os.path.exists(base_log_dir):
#     os.makedirs(base_log_dir)
# file_handler = TimedRotatingFileHandler(filename=os.path.join(base_log_dir, 'asr.log'),
#                                         when='MIDNIGHT',
#                                         interval=1,
#                                         backupCount=7,
#                                         encoding='utf-8')
# file_handler.setFormatter(formatter)
# logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
