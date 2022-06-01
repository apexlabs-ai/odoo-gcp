# -*- coding: utf-8 -*
import logging

from google.cloud.logging_v2.handlers.structured_log import StructuredLogHandler
logging.getLogger().handlers = [StructuredLogHandler()]
