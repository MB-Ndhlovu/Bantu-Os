"""
Tests for bantu_os.core.init_bridge module.
"""

from bantu_os.core.init_bridge import InitBridge, SOCKET_PATH


class TestInitBridge:
    def test_default_values(self):
        """Bridge initialises with correct defaults."""
        bridge = InitBridge()
        assert bridge.service_name == "ai-engine"
        assert bridge.socket_path == SOCKET_PATH
        assert bridge.sock is None
        assert bridge._registered is False

    def test_custom_service_name(self):
        """Service name can be overridden."""
        bridge = InitBridge(service_name="test-service")
        assert bridge.service_name == "test-service"
        assert bridge.socket_path == SOCKET_PATH

    def test_custom_socket_path(self):
        """Socket path can be overridden."""
        bridge = InitBridge(socket_path="/tmp/test.sock")
        assert bridge.socket_path == "/tmp/test.sock"

    def test_shutdown_event_property(self):
        """shutdown_event returns the internal asyncio.Event."""
        import asyncio

        bridge = InitBridge()
        assert isinstance(bridge.shutdown_event, asyncio.Event)

    def test_register_fails_gracefully_without_socket(self):
        """
        register() returns False when C init socket is not present.
        This is the expected behaviour outside the init environment.
        """
        bridge = InitBridge()
        # Socket path does not exist outside init environment — should return False
        result = bridge.register()
        assert result is False
