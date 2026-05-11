import json
import gzip
import base64
import unittest
from unittest.mock import patch, MagicMock, call

# Environment variables must be set before importing the module
ENV_VARS = {
    "AMQ_CONNECTION": "10.0.0.1:61613,10.0.0.2:61613",
    "AMQ_QUEUE_PREFIX": "test.queue",
    "RULE_INIT": "rule1",
    "RULE_EXCLUDE_LIST": "excluded_component,another_excluded",
    "LOG_LEVEL": "DEBUG",
}


def make_event(log_events: list) -> dict:
    """Helper to build a Lambda CloudWatch Logs event."""
    payload = {
        "logEvents": log_events,
        "logGroup": "/aws/lambda/test",
        "logStream": "test-stream",
    }
    compressed = gzip.compress(json.dumps(payload).encode("utf-8"))
    encoded = base64.b64encode(compressed).decode("utf-8")
    return {"awslogs": {"data": encoded}}


def make_log_event(event_id: str, component: str, extra: dict = None) -> dict:
    """Helper to build a single CloudWatch log event entry."""
    message = {"component": component, **(extra or {})}
    return {"id": event_id, "message": json.dumps(message)}


@patch.dict("os.environ", ENV_VARS)
@patch("stomp.Connection11")
class TestLambdaHandler(unittest.TestCase):

    def _get_handler(self):
        """Import handler fresh (module already loaded with patched env)."""
        import importlib
        import src.lambda as lm
        importlib.reload(lm)
        return lm.handler

    # ------------------------------------------------------------------
    # Connection building
    # ------------------------------------------------------------------

    def test_builds_connection_list_from_env(self, mock_conn_cls):
        """AMQ_CONNECTION is parsed into a list of (host, port) tuples."""
        mock_amq = MagicMock()
        mock_conn_cls.return_value = mock_amq

        handler = self._get_handler()
        event = make_event([make_log_event("id1", "comp_a")])
        handler(event, {})

        mock_conn_cls.assert_called_once_with(
            [("10.0.0.1", 61613), ("10.0.0.2", 61613)],
            auto_content_length=False,
        )

    def test_connects_with_wait_true(self, mock_conn_cls):
        """stomp.connect is called with wait=True."""
        mock_amq = MagicMock()
        mock_conn_cls.return_value = mock_amq

        handler = self._get_handler()
        event = make_event([make_log_event("id1", "comp_a")])
        handler(event, {})

        mock_amq.connect.assert_called_once_with(wait=True)

    # ------------------------------------------------------------------
    # Queue name construction
    # ------------------------------------------------------------------

    def test_queue_name_is_prefix_plus_ruleid_plus_events(self, mock_conn_cls):
        """Queue name follows the pattern <prefix>.<ruleid>events."""
        mock_amq = MagicMock()
        mock_conn_cls.return_value = mock_amq

        handler = self._get_handler()
        event = make_event([make_log_event("id1", "comp_a")])
        handler(event, {})

        # Expected queue: "test.queue.rule1events"
        send_call = mock_amq.send.call_args
        self.assertEqual(send_call[0][0], "test.queue.rule1events")

    # ------------------------------------------------------------------
    # Message forwarding
    # ------------------------------------------------------------------

    def test_sends_message_for_non_excluded_component(self, mock_conn_cls):
        """Messages whose component is NOT in the exclude list are forwarded."""
        mock_amq = MagicMock()
        mock_conn_cls.return_value = mock_amq

        handler = self._get_handler()
        log_event = make_log_event("evt-001", "allowed_component")
        event = make_event([log_event])
        handler(event, {})

        mock_amq.send.assert_called_once()
        args, kwargs = mock_amq.send.call_args
        self.assertEqual(args[1], log_event["message"])

    def test_does_not_send_message_for_excluded_component(self, mock_conn_cls):
        """Messages whose component IS in the exclude list are skipped."""
        mock_amq = MagicMock()
        mock_conn_cls.return_value = mock_amq

        handler = self._get_handler()
        event = make_event([make_log_event("evt-002", "excluded_component")])
        handler(event, {})

        mock_amq.send.assert_not_called()

    def test_sends_correct_jms_headers(self, mock_conn_cls):
        """JMSXGroupID and elasticId headers are set correctly."""
        mock_amq = MagicMock()
        mock_conn_cls.return_value = mock_amq

        handler = self._get_handler()
        log_event = make_log_event("evt-003", "comp_b")
        event = make_event([log_event])
        handler(event, {})

        _, kwargs = mock_amq.send.call_args
        headers = kwargs.get("headers") or mock_amq.send.call_args[0][2] if len(mock_amq.send.call_args[0]) > 2 else mock_amq.send.call_args[1]["headers"]
        self.assertEqual(headers["JMSXGroupID"], "comp_b")
        self.assertEqual(headers["elasticId"], "evt-003")

    def test_processes_multiple_log_events(self, mock_conn_cls):
        """All non-excluded log events in a batch are forwarded."""
        mock_amq = MagicMock()
        mock_conn_cls.return_value = mock_amq

        handler = self._get_handler()
        log_events = [
            make_log_event("id-1", "comp_x"),
            make_log_event("id-2", "comp_y"),
            make_log_event("id-3", "comp_z"),
        ]
        event = make_event(log_events)
        handler(event, {})

        self.assertEqual(mock_amq.send.call_count, 3)

    def test_mixed_excluded_and_allowed_events(self, mock_conn_cls):
        """Only non-excluded events are forwarded in a mixed batch."""
        mock_amq = MagicMock()
        mock_conn_cls.return_value = mock_amq

        handler = self._get_handler()
        log_events = [
            make_log_event("id-1", "allowed_component"),
            make_log_event("id-2", "excluded_component"),   # excluded
            make_log_event("id-3", "another_excluded"),     # excluded
            make_log_event("id-4", "also_allowed"),
        ]
        event = make_event(log_events)
        handler(event, {})

        self.assertEqual(mock_amq.send.call_count, 2)

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def test_handler_logs_error_on_exception(self, mock_conn_cls):
        """Exceptions are caught and logged; handler does not re-raise."""
        mock_conn_cls.side_effect = Exception("connection failed")

        handler = self._get_handler()
        event = make_event([make_log_event("id-1", "comp_a")])

        # Should not raise
        try:
            handler(event, {})
        except Exception:
            self.fail("handler() raised an exception instead of logging it")

    def test_handler_handles_malformed_event_gracefully(self, mock_conn_cls):
        """A missing 'awslogs' key is caught and logged without crashing."""
        mock_amq = MagicMock()
        mock_conn_cls.return_value = mock_amq

        handler = self._get_handler()

        try:
            handler({}, {})  # no 'awslogs' key
        except Exception:
            self.fail("handler() raised an exception on malformed event")

    def test_handler_handles_invalid_base64_gracefully(self, mock_conn_cls):
        """Invalid base64 data is caught and logged without crashing."""
        mock_amq = MagicMock()
        mock_conn_cls.return_value = mock_amq

        handler = self._get_handler()
        event = {"awslogs": {"data": "!!!not-valid-base64!!!"}}

        try:
            handler(event, {})
        except Exception:
            self.fail("handler() raised an exception on invalid base64")


if __name__ == "__main__":
    unittest.main()
