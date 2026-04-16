# Bantu-OS Network Service
# AI-native networking with safety and intelligence

from __future__ import annotations

import socket
import urllib.request
import urllib.error
import urllib.parse
import json
import ssl
from typing import Optional, Dict, List, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class HTTPResponse:
    '''HTTP response container.'''
    status: int
    headers: Dict[str, str]
    body: str
    url: str
    elapsed_ms: float


class NetworkService:
    '''
    System service for AI-powered networking operations.
    
    Handles HTTP/HTTPS requests, DNS resolution, port checks,
    and network diagnostics with safety constraints.
    '''
    
    def __init__(self, timeout: int = 30, max_response_size: int = 5_000_000):
        self.timeout = timeout
        self.max_response_size = max_response_size
        self._request_log: List[Dict[str, Any]] = []
        self._blocked_hosts: set = set()
        self._allowed_hosts: set = {
            'api.openai.com',
            'github.com',
            'api.github.com',
        }
    
    def http_get(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        '''Perform HTTP GET request.'''
        self._check_url_allowed(url)
        
        start = datetime.now()
        headers = headers or {}
        
        try:
            req = urllib.request.Request(url, headers=headers, method='GET')
            
            # Create SSL context that doesn't verify in dev
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, timeout=timeout or self.timeout, context=ctx) as resp:
                body = resp.read(self.max_response_size)
                elapsed = (datetime.now() - start).total_seconds() * 1000
                
                response_headers = {k: v for k, v in resp.headers.items()}
                
                self._log_request('GET', url, resp.status)
                
                return {
                    'status': resp.status,
                    'headers': response_headers,
                    'body': body.decode('utf-8', errors='replace'),
                    'url': resp.url,
                    'elapsed_ms': round(elapsed, 2),
                }
        except urllib.error.HTTPError as e:
            self._log_request('GET', url, e.code, error=str(e))
            return {
                'status': e.code,
                'error': str(e),
                'url': url,
                'elapsed_ms': round((datetime.now() - start).total_seconds() * 1000, 2),
            }
        except Exception as e:
            self._log_request('GET', url, 0, error=str(e))
            raise RuntimeError(f'HTTP GET failed: {e}')
    
    def http_post(
        self,
        url: str,
        data: Optional[str] = None,
        *,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        '''Perform HTTP POST request.'''
        self._check_url_allowed(url)
        
        start = datetime.now()
        headers = headers or {}
        
        # Set content type
        if json_data:
            data = json.dumps(json_data)
            headers['Content-Type'] = 'application/json'
        
        encoded_data = data.encode('utf-8') if data else None
        
        try:
            req = urllib.request.Request(
                url,
                data=encoded_data,
                headers=headers,
                method='POST',
            )
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, timeout=timeout or self.timeout, context=ctx) as resp:
                body = resp.read(self.max_response_size)
                elapsed = (datetime.now() - start).total_seconds() * 1000
                
                self._log_request('POST', url, resp.status)
                
                return {
                    'status': resp.status,
                    'headers': {k: v for k, v in resp.headers.items()},
                    'body': body.decode('utf-8', errors='replace'),
                    'url': resp.url,
                    'elapsed_ms': round(elapsed, 2),
                }
        except urllib.error.HTTPError as e:
            self._log_request('POST', url, e.code, error=str(e))
            return {
                'status': e.code,
                'error': str(e),
                'url': url,
                'elapsed_ms': round((datetime.now() - start).total_seconds() * 1000, 2),
            }
        except Exception as e:
            self._log_request('POST', url, 0, error=str(e))
            raise RuntimeError(f'HTTP POST failed: {e}')
    
    def http_request(
        self,
        method: str,
        url: str,
        *,
        data: Optional[str] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        '''Generic HTTP request method.'''
        if method.upper() == 'GET':
            return self.http_get(url, headers=headers, timeout=timeout)
        elif method.upper() == 'POST':
            return self.http_post(url, data=data, json_data=json_data, headers=headers, timeout=timeout)
        else:
            raise NotImplementedError(f'HTTP method {method} not implemented')
    
    def check_url(self, url: str) -> Dict[str, Any]:
        '''Check if URL is reachable and get basic info.'''
        try:
            result = self.http_get(url)
            return {
                'url': url,
                'reachable': True,
                'status': result['status'],
                'elapsed_ms': result['elapsed_ms'],
                'timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                'url': url,
                'reachable': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
            }
    
    def dns_lookup(self, hostname: str) -> Dict[str, Any]:
        '''Perform DNS lookup.'''
        start = datetime.now()
        
        try:
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
            elapsed = (datetime.now() - start).total_seconds() * 1000
            
            addresses = []
            for family, socktype, proto, _, sockaddr in addr_info:
                addresses.append({
                    'family': 'IPv4' if family == socket.AF_INET else 'IPv6',
                    'address': sockaddr[0],
                })
            
            self._log_request('DNS', hostname, 0)
            
            return {
                'hostname': hostname,
                'addresses': addresses,
                'resolved': True,
                'elapsed_ms': round(elapsed, 2),
                'timestamp': datetime.now().isoformat(),
            }
        except socket.gaierror as e:
            return {
                'hostname': hostname,
                'resolved': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
            }
    
    def check_port(self, host: str, port: int, *, timeout: int = 5) -> Dict[str, Any]:
        '''Check if a port is open on a host.'''
        start = datetime.now()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            elapsed = (datetime.now() - start).total_seconds() * 1000
            
            self._log_request('PORT', f'{host}:{port}', result)
            
            return {
                'host': host,
                'port': port,
                'open': result == 0,
                'elapsed_ms': round(elapsed, 2),
                'timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                'host': host,
                'port': port,
                'open': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
            }
    
    def ping(self, host: str, *, count: int = 1, timeout: int = 5) -> Dict[str, Any]:
        '''Ping a host using socket connection.'''
        import time
        
        results = []
        success_count = 0
        
        for _ in range(count):
            start = time.time()
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((host, 80))
                sock.close()
                
                elapsed = (time.time() - start) * 1000
                
                if result == 0:
                    success_count += 1
                    results.append({'success': True, 'time_ms': round(elapsed, 2)})
                else:
                    results.append({'success': False, 'time_ms': None})
            except Exception as e:
                results.append({'success': False, 'error': str(e)})
        
        return {
            'host': host,
            'packets_sent': count,
            'packets_received': success_count,
            'packet_loss_percent': round((count - success_count) / count * 100, 1),
            'results': results,
            'timestamp': datetime.now().isoformat(),
        }
    
    def get_local_ip(self) -> Dict[str, Any]:
        '''Get local IP address.'''
        try:
            # Create a socket to determine local IP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(('8.8.8.8', 80))
            local_ip = sock.getsockname()[0]
            sock.close()
            
            return {
                'local_ip': local_ip,
                'timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
            }
    
    def get_public_ip(self) -> Dict[str, Any]:
        '''Get public IP address via external service.'''
        try:
            result = self.http_get('https://api.ipify.org?format=json')
            return {
                'public_ip': result['body'].get('ip', result['body']),
                'timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
            }
    
    def add_allowed_host(self, host: str) -> None:
        '''Add a host to the allowed list.'''
        self._allowed_hosts.add(host)
    
    def add_blocked_host(self, host: str) -> None:
        '''Add a host to the blocked list.'''
        self._blocked_hosts.add(host)
    
    def get_request_log(self) -> List[Dict[str, Any]]:
        '''Get history of network requests.'''
        return self._request_log.copy()
    
    def _check_url_allowed(self, url: str) -> None:
        '''Check if URL is allowed based on host restrictions.'''
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.split(':')[0]  # Remove port
        
        if host in self._blocked_hosts:
            raise PermissionError(f'Host blocked: {host}')
    
    def _log_request(self, method: str, url: str, status: int, error: Optional[str] = None) -> None:
        self._request_log.append({
            'method': method,
            'url': url,
            'status': status,
            'error': error,
            'timestamp': datetime.now().isoformat(),
        })
    
    def get_stats(self) -> Dict[str, Any]:
        '''Get network service statistics.'''
        return {
            'total_requests': len(self._request_log),
            'allowed_hosts': list(self._allowed_hosts),
            'blocked_hosts': list(self._blocked_hosts),
            'timestamp': datetime.now().isoformat(),
        }