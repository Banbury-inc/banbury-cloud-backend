from pathlib import Path
from unittest.mock import patch

import pytest

from apps.flows.executors import python_executor


def test_execute_inline_success_parses_json_output():
    with patch('apps.flows.executors.python_executor._run_python_script') as mock_run_python_script:
        mock_run_python_script.return_value = {
            'interpreter': 'python3',
            'exit_code': 0,
            'stdout': '{"message":"ok"}',
            'stderr': '',
            'timed_out': False,
            'truncated': False,
        }

        result = python_executor.execute(
            node_data={
                'executionMode': 'inline',
                'script': 'print("hello")',
                'timeoutSeconds': 10,
                'input': '{"name":"banbury"}',
            },
            inputs={'start': {'data': {'seed': 1}}},
            username='demo-user',
        )

    assert result['status'] == 'success'
    assert result['data']['interpreter'] == 'python3'
    assert result['data']['parsedOutput'] == {'message': 'ok'}


def test_execute_inline_requires_script():
    result = python_executor.execute(
        node_data={'executionMode': 'inline', 'script': ''},
        inputs={},
        username='demo-user',
    )

    assert result['status'] == 'failed'
    assert result['error'] == 'Inline execution requires a non-empty script'


def test_execute_file_mode_rejects_path_outside_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    allowed_root = tmp_path / 'allowed-root'
    allowed_root.mkdir(parents=True)
    monkeypatch.setenv('FLOW_PYTHON_WORKSPACE_ROOT', str(allowed_root))

    outside_file = tmp_path / 'outside.py'
    outside_file.write_text('print("outside")', encoding='utf-8')

    result = python_executor.execute(
        node_data={'executionMode': 'file', 'filePath': str(outside_file)},
        inputs={},
        username='demo-user',
    )

    assert result['status'] == 'failed'
    assert result['error'] == 'Python file path is outside the allowed workspace root'


def test_execute_file_mode_runs_resolved_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    allowed_root = tmp_path / 'workspace'
    script_dir = allowed_root / 'scripts'
    script_dir.mkdir(parents=True)
    script_file = script_dir / 'flow_task.py'
    script_file.write_text('print("ok")', encoding='utf-8')
    monkeypatch.setenv('FLOW_PYTHON_WORKSPACE_ROOT', str(allowed_root))

    with patch('apps.flows.executors.python_executor._run_python_script') as mock_run_python_script:
        mock_run_python_script.return_value = {
            'interpreter': 'python3',
            'exit_code': 0,
            'stdout': 'done',
            'stderr': '',
            'timed_out': False,
            'truncated': False,
        }
        result = python_executor.execute(
            node_data={'executionMode': 'file', 'filePath': 'scripts/flow_task.py'},
            inputs={},
            username='demo-user',
        )

    assert result['status'] == 'success'
    mock_run_python_script.assert_called_once()
    assert mock_run_python_script.call_args.kwargs['script_path'] == str(script_file.resolve())


def test_execute_timeout_returns_failed():
    with patch('apps.flows.executors.python_executor._run_python_script') as mock_run_python_script:
        mock_run_python_script.return_value = {
            'interpreter': 'python3',
            'exit_code': 1,
            'stdout': '',
            'stderr': '',
            'timed_out': True,
            'truncated': False,
        }
        result = python_executor.execute(
            node_data={'executionMode': 'inline', 'script': 'while True: pass', 'timeoutSeconds': 2},
            inputs={},
            username='demo-user',
        )

    assert result['status'] == 'failed'
    assert result['error'] == 'Python execution exceeded timeout (2s)'
