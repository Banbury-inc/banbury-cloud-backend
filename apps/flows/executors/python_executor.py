"""
Python Code executor: runs inline Python or a Python file path.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 300
DEFAULT_MAX_OUTPUT_BYTES = 256_000


def _coerce_timeout_seconds(value: Any) -> int:
    if isinstance(value, bool):
        return DEFAULT_TIMEOUT_SECONDS
    if isinstance(value, int):
        timeout_seconds = value
    elif isinstance(value, str):
        if not value.strip():
            return DEFAULT_TIMEOUT_SECONDS
        try:
            timeout_seconds = int(value)
        except ValueError:
            return DEFAULT_TIMEOUT_SECONDS
    else:
        return DEFAULT_TIMEOUT_SECONDS

    if timeout_seconds < 1:
        return 1
    if timeout_seconds > MAX_TIMEOUT_SECONDS:
        return MAX_TIMEOUT_SECONDS
    return timeout_seconds


def _truncate_bytes(raw: bytes, max_bytes: int) -> tuple[str, bool]:
    if len(raw) <= max_bytes:
        return raw.decode('utf-8', errors='replace'), False
    return raw[:max_bytes].decode('utf-8', errors='replace'), True


def _build_input_payload(node_data: dict, inputs: dict) -> dict:
    upstream_data: dict[str, Any] = {}
    for source_node_id, upstream_output in inputs.items():
        if not isinstance(upstream_output, dict):
            continue
        data = upstream_output.get('data', upstream_output)
        upstream_data[source_node_id] = data

    user_input = node_data.get('input')
    parsed_user_input: Any = user_input

    if isinstance(user_input, str):
        stripped = user_input.strip()
        if stripped:
            try:
                parsed_user_input = json.loads(stripped)
            except json.JSONDecodeError:
                parsed_user_input = user_input
        else:
            parsed_user_input = ''

    return {
        'input': parsed_user_input,
        'upstream': upstream_data,
    }


def _resolve_allowed_root() -> Path:
    configured_root = (
        os.getenv('FLOW_PYTHON_WORKSPACE_ROOT')
        or os.getenv('FLOW_PYTHON_ALLOWED_ROOT')
        or os.getcwd()
    )
    return Path(configured_root).resolve()


def _resolve_python_file_path(file_path: str) -> Path:
    allowed_root = _resolve_allowed_root()
    candidate_path = Path(file_path)
    resolved_path = (
        candidate_path.resolve()
        if candidate_path.is_absolute()
        else (allowed_root / candidate_path).resolve()
    )

    try:
        resolved_path.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError('Python file path is outside the allowed workspace root') from exc

    if resolved_path.suffix.lower() != '.py':
        raise ValueError('Python file must use a .py extension')
    if not resolved_path.exists() or not resolved_path.is_file():
        raise ValueError('Python file was not found')

    return resolved_path


def _run_with_interpreter(
    interpreter: str,
    script_path: str,
    payload: str,
    timeout_seconds: int,
    max_output_bytes: int,
) -> dict:
    process = subprocess.Popen(
        [interpreter, script_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            **os.environ,
            'PYTHONUNBUFFERED': '1',
            'FLOW_NODE_INPUT': payload,
        },
    )

    timed_out = False
    try:
        stdout_bytes, stderr_bytes = process.communicate(
            input=payload.encode('utf-8'),
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        process.kill()
        stdout_bytes, stderr_bytes = process.communicate()
        timed_out = True

    stdout, stdout_truncated = _truncate_bytes(stdout_bytes, max_output_bytes)
    stderr, stderr_truncated = _truncate_bytes(stderr_bytes, max_output_bytes)
    truncated = stdout_truncated or stderr_truncated

    return {
        'interpreter': interpreter,
        'exit_code': process.returncode if process.returncode is not None else 1,
        'stdout': stdout,
        'stderr': stderr,
        'timed_out': timed_out,
        'truncated': truncated,
    }


def _run_python_script(
    script_path: str,
    payload: str,
    timeout_seconds: int,
    max_output_bytes: int,
) -> dict:
    try:
        return _run_with_interpreter(
            interpreter='python3',
            script_path=script_path,
            payload=payload,
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
        )
    except FileNotFoundError:
        try:
            return _run_with_interpreter(
                interpreter='python',
                script_path=script_path,
                payload=payload,
                timeout_seconds=timeout_seconds,
                max_output_bytes=max_output_bytes,
            )
        except FileNotFoundError:
            return {
                'interpreter': 'none',
                'exit_code': 127,
                'stdout': '',
                'stderr': 'Neither python3 nor python is available on the server.',
                'timed_out': False,
                'truncated': False,
            }


def _parse_stdout_as_json(stdout: str) -> Any | None:
    if not stdout.strip():
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def execute(node_data: dict, inputs: dict, username: str) -> dict:
    del username

    execution_mode = node_data.get('executionMode', 'inline')
    timeout_seconds = _coerce_timeout_seconds(node_data.get('timeoutSeconds'))
    max_output_bytes = DEFAULT_MAX_OUTPUT_BYTES
    payload = json.dumps(_build_input_payload(node_data=node_data, inputs=inputs))

    if execution_mode not in ('inline', 'file'):
        return {'status': 'failed', 'error': 'executionMode must be either "inline" or "file"', 'data': {}}

    if execution_mode == 'inline':
        script = node_data.get('script', '')
        if not isinstance(script, str) or not script.strip():
            return {'status': 'failed', 'error': 'Inline execution requires a non-empty script', 'data': {}}

        with tempfile.TemporaryDirectory(prefix='flow-python-') as temp_dir:
            script_path = Path(temp_dir) / 'inline_script.py'
            script_path.write_text(script, encoding='utf-8')
            process_result = _run_python_script(
                script_path=str(script_path),
                payload=payload,
                timeout_seconds=timeout_seconds,
                max_output_bytes=max_output_bytes,
            )
    else:
        file_path = node_data.get('filePath', '')
        if not isinstance(file_path, str) or not file_path.strip():
            return {'status': 'failed', 'error': 'File execution requires a Python file path', 'data': {}}
        try:
            resolved_path = _resolve_python_file_path(file_path)
        except ValueError as exc:
            return {'status': 'failed', 'error': str(exc), 'data': {}}

        process_result = _run_python_script(
            script_path=str(resolved_path),
            payload=payload,
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
        )

    did_fail = process_result['timed_out'] or process_result['exit_code'] != 0
    parsed_output = _parse_stdout_as_json(process_result['stdout'])

    data = {
        'stdout': process_result['stdout'],
        'stderr': process_result['stderr'],
        'exitCode': process_result['exit_code'],
        'timedOut': process_result['timed_out'],
        'truncated': process_result['truncated'],
        'interpreter': process_result['interpreter'],
        'executionMode': execution_mode,
    }
    if parsed_output is not None:
        data['parsedOutput'] = parsed_output

    if did_fail:
        if process_result['timed_out']:
            return {
                'status': 'failed',
                'error': f'Python execution exceeded timeout ({timeout_seconds}s)',
                'data': data,
            }
        return {
            'status': 'failed',
            'error': process_result['stderr'] or f'Python exited with code {process_result["exit_code"]}',
            'data': data,
        }

    return {'status': 'success', 'data': data}
