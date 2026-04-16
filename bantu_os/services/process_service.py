# Bantu-OS Process Service
# AI-native process management with safety controls

from __future__ import annotations

import os
import signal
import subprocess
import psutil
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ProcessInfo:
    '''Process information container.'''
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_mb: float
    create_time: float
    cmdline: List[str]


class ProcessService:
    '''
    System service for AI-powered process management.
    
    Handles process listing, monitoring, control (start/stop/kill),
    and resource tracking with safety constraints.
    '''
    
    def __init__(self, max_concurrent: int = 50):
        self.max_concurrent = max_concurrent
        self._managed_processes: Dict[int, subprocess.Popen] = {}
        self._operation_log: List[Dict[str, Any]] = []
    
    def list_processes(
        self,
        *,
        name_filter: Optional[str] = None,
        user_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        '''List running processes with optional filtering.'''
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'status', 'username', 'cmdline', 'create_time']):
            try:
                pinfo = proc.info
                if name_filter and name_filter.lower() not in pinfo['name'].lower():
                    continue
                if user_filter and pinfo['username'] != user_filter:
                    continue
                
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'status': pinfo['status'],
                    'username': pinfo.get('username', 'unknown'),
                    'cmdline': ' '.join(pinfo.get('cmdline') or []),
                    'create_time': datetime.fromtimestamp(pinfo['create_time']).isoformat(),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return sorted(processes, key=lambda x: x['pid'])[:limit]
    
    def get_process_info(self, pid: int) -> Dict[str, Any]:
        '''Get detailed information about a specific process.'''
        try:
            proc = psutil.Process(pid)
            with proc.oneshot():
                return {
                    'pid': proc.pid,
                    'name': proc.name(),
                    'status': proc.status(),
                    'username': proc.username(),
                    'cmdline': proc.cmdline(),
                    'create_time': datetime.fromtimestamp(proc.create_time()).isoformat(),
                    'cpu_percent': proc.cpu_percent(),
                    'memory_info': {
                        'rss_mb': proc.memory_info().rss / 1024 / 1024,
                        'vms_mb': proc.memory_info().vms / 1024 / 1024,
                    },
                    'num_threads': proc.num_threads(),
                    'open_files': [f.path for f in proc.open_files()],
                    'connections': len(proc.connections()),
                    'is_running': proc.is_running(),
                    'nice': proc.nice(),
                }
        except psutil.NoSuchProcess:
            raise ProcessLookupError(f'Process {pid} not found')
        except psutil.AccessDenied:
            raise PermissionError(f'Access denied to process {pid}')
    
    def start_process(
        self,
        command: str | List[str],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        shell: bool = False,
        stdin: Optional[str] = None,
    ) -> Dict[str, Any]:
        '''Start a new process with optional configuration.'''
        if len(self._managed_processes) >= self.max_concurrent:
            raise RuntimeError(f'Max concurrent processes ({self.max_concurrent}) reached')
        
        # Security: disallow certain dangerous commands
        if isinstance(command, str):
            dangerous = ['rm -rf', ':(){:|:&};:', 'fork bomb']
            if any(d in command for d in dangerous):
                raise PermissionError(f'Dangerous command blocked: {command[:50]}...')
        
        try:
            if isinstance(command, str) and not shell:
                cmd_list = command.split()
            else:
                cmd_list = command
            
            proc = subprocess.Popen(
                cmd_list,
                cwd=cwd,
                env=env or None,
                shell=shell,
                stdin=subprocess.PIPE if stdin else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            self._managed_processes[proc.pid] = proc
            
            self._log_operation('start', proc.pid, command)
            
            return {
                'pid': proc.pid,
                'command': command if isinstance(command, str) else ' '.join(command),
                'status': 'running',
                'start_time': datetime.now().isoformat(),
            }
        except Exception as e:
            raise RuntimeError(f'Failed to start process: {e}')
    
    def stop_process(self, pid: int, *, force: bool = False) -> Dict[str, Any]:
        '''Stop a process gracefully (SIGTERM) or forcefully (SIGKILL).'''
        try:
            proc = psutil.Process(pid)
            sig = signal.SIGKILL if force else signal.SIGTERM
            
            proc.send_signal(sig)
            proc.wait(timeout=10 if not force else 2)
            
            status = 'killed' if force else 'terminated'
            self._log_operation(status, pid, proc.name())
            
            # Clean up from managed
            self._managed_processes.pop(pid, None)
            
            return {
                'pid': pid,
                'status': status,
                'signal': 'SIGKILL' if force else 'SIGTERM',
                'timestamp': datetime.now().isoformat(),
            }
        except psutil.NoSuchProcess:
            raise ProcessLookupError(f'Process {pid} not found')
        except psutil.TimeoutExpired:
            raise TimeoutError(f'Process {pid} did not respond to {sig.name}')
    
    def kill_process(self, pid: int) -> Dict[str, Any]:
        '''Forcefully kill a process.'''
        return self.stop_process(pid, force=True)
    
    def get_managed_processes(self) -> List[Dict[str, Any]]:
        '''Get list of processes managed by this service.'''
        result = []
        for pid in list(self._managed_processes.keys()):
            if psutil.pid_exists(pid):
                try:
                    proc = psutil.Process(pid)
                    result.append({
                        'pid': pid,
                        'name': proc.name(),
                        'status': proc.status(),
                    })
                except psutil.NoSuchProcess:
                    pass
            else:
                self._managed_processes.pop(pid, None)
        return result
    
    def get_system_stats(self) -> Dict[str, Any]:
        '''Get overall system resource statistics.'''
        return {
            'cpu': {
                'percent': psutil.cpu_percent(interval=0.1),
                'count': psutil.cpu_count(),
                'per_cpu': psutil.cpu_percent(interval=0.1, percpu=True),
            },
            'memory': {
                'total_mb': psutil.virtual_memory().total / 1024 / 1024,
                'available_mb': psutil.virtual_memory().available / 1024 / 1024,
                'percent': psutil.virtual_memory().percent,
            },
            'disk': {
                'total_gb': psutil.disk_usage('/').total / 1024 / 1024 / 1024,
                'used_gb': psutil.disk_usage('/').used / 1024 / 1024 / 1024,
                'free_gb': psutil.disk_usage('/').free / 1024 / 1024 / 1024,
                'percent': psutil.disk_usage('/').percent,
            },
            'process_count': len(psutil.pids()),
            'managed_count': len(self._managed_processes),
            'timestamp': datetime.now().isoformat(),
        }
    
    def check_process_exists(self, pid: int) -> bool:
        '''Check if a process exists.'''
        return psutil.pid_exists(pid)
    
    def get_operation_log(self) -> List[Dict[str, Any]]:
        '''Get history of process operations.'''
        return self._operation_log.copy()
    
    def _log_operation(self, operation: str, pid: int, details: Any) -> None:
        self._operation_log.append({
            'operation': operation,
            'pid': pid,
            'details': str(details),
            'timestamp': datetime.now().isoformat(),
        })