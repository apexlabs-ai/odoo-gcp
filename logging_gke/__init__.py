# -*- coding: utf-8 -*
import json
import logging
import logging.handlers

GCP_FORMAT = (
    '{"message": %(_formatted_msg)s, '
    '"severity": "%(levelname)s", '
    '"logging.googleapis.com/labels": %(_labels_str)s, '
    '"logging.googleapis.com/trace": "%(_trace_str)s", '
    '"logging.googleapis.com/spanId": "%(_span_id_str)s", '
    '"logging.googleapis.com/sourceLocation": %(_source_location_str)s, '
    '"httpRequest": %(_http_request_str)s }'
)


class CloudLoggingFilter(logging.Filter):
    """Python standard ``logging`` Filter class to add Cloud Logging
    information to each LogRecord.

    When attached to a LogHandler, each incoming log will be modified
    to include new Cloud Logging relevant data. This data can be manually
    overwritten using the `extras` argument when writing logs.
    """

    # The subset of http_request fields have been tested to work consistently across GCP environments
    # https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry#httprequest
    _supported_http_fields = ("requestMethod", "requestUrl", "userAgent", "protocol")

    def __init__(self, project=None, default_labels=None):
        self.project = project
        self.default_labels = default_labels if default_labels else {}

    @staticmethod
    def _infer_source_location(record):
        """Helper function to infer source location data from a LogRecord.
        Will default to record.source_location if already set
        """
        if hasattr(record, "source_location"):
            return record.source_location
        else:
            name_map = [
                ("line", "lineno"),
                ("file", "pathname"),
                ("function", "funcName"),
            ]
            output = {}
            for (gcp_name, std_lib_name) in name_map:
                value = getattr(record, std_lib_name, None)
                if value is not None:
                    output[gcp_name] = value
            return output if output else None

    def filter(self, record):
        """
        Add new Cloud Logging data to each LogRecord as it comes in
        """
        user_labels = getattr(record, "labels", {})
        # infer request data from the environment
        inferred_http, inferred_trace, inferred_span = None, None, None
        if inferred_http is not None:
            # filter inferred_http to include only well-supported fields
            inferred_http = {
                k: v
                for (k, v) in inferred_http.items()
                if k in self._supported_http_fields and v is not None
            }
        if inferred_trace is not None and self.project is not None:
            # add full path for detected trace
            inferred_trace = f"projects/{self.project}/traces/{inferred_trace}"
        # set new record values
        record._resource = getattr(record, "resource", None)
        record._trace = getattr(record, "trace", inferred_trace) or None
        record._span_id = getattr(record, "span_id", inferred_span) or None
        record._http_request = getattr(record, "http_request", inferred_http)
        record._source_location = CloudLoggingFilter._infer_source_location(record)
        record._labels = {**self.default_labels, **user_labels} or None
        # create string representations for structured logging
        record._trace_str = record._trace or ""
        record._span_id_str = record._span_id or ""
        record._http_request_str = json.dumps(record._http_request or {})
        record._source_location_str = json.dumps(record._source_location or {})
        record._labels_str = json.dumps(record._labels or {})
        # break quotes for parsing through structured logging
        record._msg_str = str(record.msg).replace('"', '\\"') if record.msg else ""
        return True


class StructuredLogHandler(logging.StreamHandler):
    """Handler to format logs into the Cloud Logging structured log format,
    and write them to standard output
    """

    def __init__(self, *, labels=None, stream=None, project_id=None):
        """
        Args:
            labels (Optional[dict]): Additional labels to attach to logs.
            stream (Optional[IO]): Stream to be used by the handler.
            project (Optional[str]): Project Id associated with the logs.
        """
        super(StructuredLogHandler, self).__init__(stream=stream)
        self.project_id = project_id

        # add extra keys to log record
        log_filter = CloudLoggingFilter(project=project_id, default_labels=labels)
        self.addFilter(log_filter)

        # make logs appear in GCP structured logging format
        self._gcp_formatter = logging.Formatter(GCP_FORMAT)

    def format(self, record):
        """Format the message into structured log JSON.
        Args:
            record (logging.LogRecord): The log record.
        Returns:
            str: A JSON string formatted for GKE fluentd.
        """
        # let other formatters alter the message
        super_payload = None
        if record.msg:
            # format the message using default handler behaviors
            super_payload = super(StructuredLogHandler, self).format(record)
        # properly break any formatting in string to make it json safe
        record._formatted_msg = json.dumps(super_payload or "")
        # remove exception info to avoid duplicating it
        # https://github.com/googleapis/python-logging/issues/382
        record.exc_info = None
        record.exc_text = None
        # convert to GCP structred logging format
        gcp_payload = self._gcp_formatter.format(record)
        return gcp_payload


logging.getLogger().handlers = [StructuredLogHandler()]
