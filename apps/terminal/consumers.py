import asyncio
import json
import logging
import os
import pty
import select
import signal
import subprocess

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

SHELL = os.environ.get('SHELL', '/bin/bash')
READ_SIZE = 4096
POLL_INTERVAL = 0.02


class TerminalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs'].get('session_id', '')
        self.master_fd = None
        self.pid = None
        self.reader_task = None
        await self.accept()

    async def disconnect(self, code):
        await self._kill_process()

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = payload.get('type', '')

        if msg_type == 'start':
            await self._start_shell(payload.get('cwd'))
        elif msg_type == 'input':
            await self._write_input(payload.get('data', ''))
        elif msg_type == 'resize':
            self._resize(payload.get('cols', 80), payload.get('rows', 24))

    async def _start_shell(self, cwd: str | None = None):
        if self.master_fd is not None:
            return

        master_fd, slave_fd = pty.openpty()
        env = {**os.environ, 'TERM': 'xterm-256color', 'COLORTERM': 'truecolor'}
        work_dir = cwd or os.path.expanduser('~')

        pid = subprocess.Popen(
            [SHELL, '-l'],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            preexec_fn=os.setsid,
            cwd=work_dir,
            env=env,
        ).pid

        os.close(slave_fd)

        self.master_fd = master_fd
        self.pid = pid

        await self.send(text_data=json.dumps({'type': 'ready'}))

        self.reader_task = asyncio.get_event_loop().create_task(self._read_loop())

    async def _read_loop(self):
        loop = asyncio.get_event_loop()
        try:
            while self.master_fd is not None:
                readable, _, _ = await loop.run_in_executor(
                    None,
                    lambda: select.select([self.master_fd], [], [], POLL_INTERVAL),
                )
                if not readable:
                    continue
                try:
                    data = os.read(self.master_fd, READ_SIZE)
                except OSError:
                    break
                if not data:
                    break
                await self.send(text_data=json.dumps({
                    'type': 'data',
                    'data': data.decode('utf-8', errors='replace'),
                }))
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception('Terminal read loop error')
        finally:
            await self._send_exit()

    async def _write_input(self, data: str):
        if self.master_fd is None:
            return
        try:
            os.write(self.master_fd, data.encode('utf-8'))
        except OSError:
            pass

    def _resize(self, cols: int, rows: int):
        if self.master_fd is None:
            return
        try:
            import struct
            import fcntl
            import termios
            winsize = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

    async def _send_exit(self):
        exit_code = 0
        if self.pid:
            try:
                _, status = os.waitpid(self.pid, os.WNOHANG)
                if os.WIFEXITED(status):
                    exit_code = os.WEXITSTATUS(status)
            except ChildProcessError:
                pass
        try:
            await self.send(text_data=json.dumps({'type': 'exit', 'exitCode': exit_code}))
        except Exception:
            pass

    async def _kill_process(self):
        if self.reader_task:
            self.reader_task.cancel()
            try:
                await self.reader_task
            except asyncio.CancelledError:
                pass
            self.reader_task = None

        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None

        if self.pid:
            try:
                os.killpg(os.getpgid(self.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            self.pid = None
