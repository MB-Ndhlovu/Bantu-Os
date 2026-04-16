"""
Tests for services/network_service.py — NetworkService
"""
import pytest

from bantu_os.services.network_service import NetworkService


class TestNetworkService:
    def test_http_get_success(self):
        svc = NetworkService(timeout=10)
        result = svc.http_get("https://httpbin.org/get")
        assert result.status == 200
        assert "headers" in result.body

    def test_http_get_invalid_url(self):
        svc = NetworkService()
        result = svc.http_get("not-a-url")
        assert result.status == 0

    def test_http_get_disallowed_host(self):
        svc = NetworkService()
        result = svc.http_get("https://malicious-site.fake/")
        assert result.status == 0

    def test_check_connectivity(self):
        svc = NetworkService(timeout=5)
        result = svc.check_connectivity()
        assert isinstance(result, dict)
        assert "internet" in result

    def test_dns_lookup(self):
        svc = NetworkService()
        result = svc.dns_lookup("github.com")
        assert result is not None

    def test_request_log(self):
        svc = NetworkService()
        assert len(svc.get_request_log()) == 0
