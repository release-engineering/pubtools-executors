try:
    import mock
except ImportError:
    from unittest import mock
import paramiko
import pytest

from pubtools._executors import (
    LocalExecutorBearer,
    RemoteExecutorBearer,
    ContainerExecutorBearer,
)


def test_local_executor_init():
    """Test local executor initializer."""
    executor = LocalExecutorBearer({"some_param": "value"})

    assert executor.params["some_param"] == "value"
    assert executor.params["universal_newlines"] is True
    assert executor.params["stderr"] == -1
    assert executor.params["stdout"] == -1
    assert executor.params["stdin"] == -1


@mock.patch("pubtools._executors.subprocess.Popen")
def test_local_executor_run(mock_popen):
    """Test local executor running a command."""
    executor = LocalExecutorBearer({"some_param": "value"})

    mock_communicate = mock.MagicMock()
    mock_communicate.return_value = ("outlog", "errlog")
    mock_popen.return_value.communicate = mock_communicate
    mock_popen.return_value.returncode = 0

    out, err = executor._run_cmd("pwd", stdin="input")
    assert out == "outlog"
    assert err == "errlog"
    mock_popen.assert_called_once_with(
        ["pwd"],
        some_param="value",
        universal_newlines=True,
        stderr=-1,
        stdout=-1,
        stdin=-1,
    )
    mock_communicate.assert_called_once_with(input="input")


@mock.patch("pubtools._executors.subprocess.Popen")
def test_local_executor_context_manager(mock_popen):
    """Test local executor used as context manager."""
    mock_communicate = mock.MagicMock()
    mock_communicate.return_value = ("outlog", "errlog")
    mock_popen.return_value.communicate = mock_communicate
    mock_popen.return_value.returncode = 0

    with LocalExecutorBearer({"some_param": "value"}) as executor:
        out, err = executor._run_cmd("pwd", stdin="input")
    assert out == "outlog"
    assert err == "errlog"
    mock_popen.assert_called_once_with(
        ["pwd"],
        some_param="value",
        universal_newlines=True,
        stderr=-1,
        stdout=-1,
        stdin=-1,
    )
    mock_communicate.assert_called_once_with(input="input")


@mock.patch("pubtools._executors.subprocess.Popen")
def test_local_executor_run_error(mock_popen):
    """Test local executor running command which fails."""
    executor = LocalExecutorBearer({"some_param": "value"})

    mock_communicate = mock.MagicMock()
    mock_communicate.return_value = ("outlog", "errlog")
    mock_popen.return_value.communicate = mock_communicate
    mock_popen.return_value.returncode = -1

    with pytest.raises(RuntimeError, match="An error has occured when executing.*"):
        executor._run_cmd("pwd", stdin="input")


@mock.patch("pubtools._executors.subprocess.Popen")
def test_local_executor_run_error_custom_message(mock_popen):
    """Test local executor running command which fails with custom error message."""
    executor = LocalExecutorBearer({"some_param": "value"})

    mock_communicate = mock.MagicMock()
    mock_communicate.return_value = ("outlog", "errlog")
    mock_popen.return_value.communicate = mock_communicate
    mock_popen.return_value.returncode = -1

    with pytest.raises(RuntimeError, match="Custom error"):
        executor._run_cmd("pwd", stdin="input", err_msg="Custom error")


@mock.patch("pubtools._executors.subprocess.Popen")
def test_local_executor_run_tolerate_err(mock_popen):
    """Test local executor running command tolerating command failure."""
    executor = LocalExecutorBearer({"some_param": "value"})

    mock_communicate = mock.MagicMock()
    mock_communicate.return_value = ("outlog", "errlog")
    mock_popen.return_value.communicate = mock_communicate
    mock_popen.return_value.returncode = -1

    out, err = executor._run_cmd("pwd", stdin="input", tolerate_err=True)
    assert out == "outlog"
    assert err == "errlog"
    mock_popen.assert_called_once_with(
        ["pwd"],
        some_param="value",
        universal_newlines=True,
        stderr=-1,
        stdout=-1,
        stdin=-1,
    )
    mock_communicate.assert_called_once_with(input="input")


def test_local_executor_add_file():
    """Test local executor add file method."""
    executor = LocalExecutorBearer({"some_param": "value"})
    with mock.patch("pubtools._executors.open") as mocked_open:
        executor._add_file("some-data", "some_file")
        print(mocked_open.mock_calls)
        mocked_open.assert_called_once_with("/tmp/some_file", "w")
        mocked_open.return_value.__enter__.return_value.write.assert_called_once_with(
            "some-data".encode("utf-8")
        )


def test_remote_executor_init():
    """Test remote executor initializer."""
    executor = RemoteExecutorBearer(
        "127.0.0.1",
        username="dummy",
        key_filename="path/to/file.key",
        password="123456",
        accept_unknown_host=False,
    )

    assert executor.hostname == "127.0.0.1"
    assert executor.username == "dummy"
    assert executor.key_filename == "path/to/file.key"
    assert executor.password == "123456"
    assert isinstance(executor.missing_host_policy, paramiko.client.RejectPolicy)

    executor2 = RemoteExecutorBearer("127.0.0.1")

    assert isinstance(executor2.missing_host_policy, paramiko.client.WarningPolicy)


@mock.patch("pubtools._executors.paramiko.client.SSHClient")
def test_remote_executor_run(mock_sshclient):
    """Test remote executor running a command."""
    executor = RemoteExecutorBearer(
        "127.0.0.1",
        username="dummy",
        key_filename="path/to/file.key",
        password="123456",
        accept_unknown_host=True,
    )

    mock_load_host_keys = mock.MagicMock()
    mock_sshclient.return_value.load_system_host_keys = mock_load_host_keys
    mock_set_keys = mock.MagicMock()
    mock_sshclient.return_value.set_missing_host_key_policy = mock_set_keys
    mock_connect = mock.MagicMock()
    mock_sshclient.return_value.connect = mock_connect

    mock_in = mock.MagicMock()
    mock_out = mock.MagicMock()
    mock_out.read.return_value = b"outlog"
    mock_recv_exit_status = mock.MagicMock()
    mock_recv_exit_status.return_value = 0
    mock_out.channel.recv_exit_status = mock_recv_exit_status
    mock_err = mock.MagicMock()
    mock_err.read.return_value = b"errlog"
    mock_send = mock.MagicMock()
    mock_shutdown_write = mock.MagicMock()
    mock_in.channel.send = mock_send
    mock_in.channel.shutdown_write = mock_shutdown_write
    mock_exec_command = mock.MagicMock()
    mock_exec_command.return_value = (mock_in, mock_out, mock_err)
    mock_sshclient.return_value.exec_command = mock_exec_command

    out, err = executor._run_cmd("pwd", stdin="input")

    mock_load_host_keys.assert_called_once()
    assert mock_set_keys.call_count == 1
    assert isinstance(mock_set_keys.call_args[0][0], paramiko.client.WarningPolicy)
    # mock_set_keys.assert_called_once_with(paramiko.client.WarningPolicy)
    mock_connect.assert_called_once_with(
        "127.0.0.1",
        username="dummy",
        password="123456",
        port=22,
        key_filename="path/to/file.key",
    )
    mock_exec_command.assert_called_once_with("pwd")
    mock_send.assert_called_once_with("input")
    mock_shutdown_write.assert_called_once()
    mock_recv_exit_status.assert_called_once()

    assert out == "outlog"
    assert err == "errlog"


@mock.patch("pubtools._executors.paramiko.client.SSHClient")
def test_remote_executor_run_error(mock_sshclient):
    """Test remote executor running a command which fails."""
    executor = RemoteExecutorBearer(
        "127.0.0.1",
        username="dummy",
        key_filename="path/to/file.key",
        password="123456",
        accept_unknown_host=True,
    )

    mock_load_host_keys = mock.MagicMock()
    mock_sshclient.return_value.load_system_host_keys = mock_load_host_keys
    mock_set_keys = mock.MagicMock()
    mock_sshclient.return_value.set_missing_host_key_policy = mock_set_keys
    mock_connect = mock.MagicMock()
    mock_sshclient.return_value.connect = mock_connect

    mock_in = mock.MagicMock()
    mock_out = mock.MagicMock()
    mock_out.read.return_value = b"outlog"
    mock_recv_exit_status = mock.MagicMock()
    mock_recv_exit_status.return_value = -1
    mock_out.channel.recv_exit_status = mock_recv_exit_status
    mock_err = mock.MagicMock()
    mock_err.read.return_value = b"errlog"
    mock_send = mock.MagicMock()
    mock_shutdown_write = mock.MagicMock()
    mock_in.channel.send = mock_send
    mock_in.channel.shutdown_write = mock_shutdown_write
    mock_exec_command = mock.MagicMock()
    mock_exec_command.return_value = (mock_in, mock_out, mock_err)
    mock_sshclient.return_value.exec_command = mock_exec_command

    with pytest.raises(RuntimeError, match="An error has occured when executing.*"):
        executor._run_cmd("pwd", stdin="input")


@mock.patch("pubtools._executors.paramiko.client.SSHClient")
def test_remote_executor_add_file(mock_client):
    """Test remote executor adding a file."""
    executor = RemoteExecutorBearer(
        "127.0.0.1",
        username="dummy",
        key_filename="path/to/file.key",
        password="123456",
        accept_unknown_host=True,
    )
    executor._add_file("some-data", "some_file")
    mock_client.return_value.open_sftp.assert_called_once()
    mock_client.return_value.open_sftp.return_value.put.assert_called_once_with(
        mock.ANY, remote_path="/tmp/some_file"
    )
    mock_client.return_value.open_sftp.return_value.chmod.assert_called_once_with(
        "/tmp/some_file", 600
    )


@mock.patch("pubtools._executors.os.path.isdir")
@mock.patch("pubtools._executors.docker.tls.TLSConfig")
@mock.patch("pubtools._executors.APIClient")
def test_container_executor_init(mock_api_client, mock_tls_config, mock_isdir):
    """Test container executor initializer."""
    mock_create_container = mock.MagicMock()
    mock_create_container.return_value = {"Id": "123"}
    mock_api_client.return_value.create_container = mock_create_container
    mock_start = mock.MagicMock()
    mock_api_client.return_value.start = mock_start
    mock_remove_container = mock.MagicMock()
    mock_api_client.return_value.remove_container = mock_remove_container
    mock_isdir.return_value = True

    with ContainerExecutorBearer(
        "quay.io/some/image:1",
        base_url="some-url.com",
        timeout=120,
        verify_tls=True,
        cert_path="/some/path",
    ):
        pass

    mock_tls_config.assert_called_once_with(
        client_cert=("/some/path/cert.pem", "/some/path/key.pem"),
        verify="/some/path/ca.pem",
    )
    mock_api_client.assert_called_once_with(
        base_url="some-url.com",
        version="auto",
        timeout=120,
        tls=mock_tls_config.return_value,
    )
    mock_create_container.assert_called_once_with("quay.io/some/image:1", detach=True, tty=True)
    mock_start.assert_called_once_with("123")
    mock_remove_container.assert_called_once_with("123", force=True)


@mock.patch("pubtools._executors.os.path.isdir")
@mock.patch("pubtools._executors.docker.tls.TLSConfig")
@mock.patch("pubtools._executors.APIClient")
def test_container_executor_run_cmd(mock_api_client, mock_tls_config, mock_isdir):
    """Test container executor running a command."""
    mock_create_container = mock.MagicMock()
    mock_create_container.return_value = {"Id": "123"}
    mock_api_client.return_value.create_container = mock_create_container
    mock_start = mock.MagicMock()
    mock_api_client.return_value.start = mock_start
    mock_remove_container = mock.MagicMock()
    mock_api_client.return_value.remove_container = mock_remove_container
    mock_isdir.return_value = True

    mock_exec_create = mock.MagicMock()
    mock_exec_create.return_value = {"Id": "321"}
    mock_api_client.return_value.exec_create = mock_exec_create
    mock_exec_start = mock.MagicMock()
    mock_exec_start.return_value = b"some output"
    mock_api_client.return_value.exec_start = mock_exec_start
    mock_exec_inspect = mock.MagicMock()
    mock_exec_inspect.return_value = {"ExitCode": 0}
    mock_api_client.return_value.exec_inspect = mock_exec_inspect

    with ContainerExecutorBearer(
        "quay.io/some/image:1",
        base_url="some-url.com",
        timeout=120,
        verify_tls=True,
        cert_path="/some/path",
    ) as executor:
        stdout, stderr = executor._run_cmd("cat file.txt")

    assert stdout == "some output"
    assert stderr == "some output"

    mock_exec_create.assert_called_once_with("123", "cat file.txt")
    mock_exec_start.assert_called_once_with("321")
    mock_exec_inspect.assert_called_once_with("321")


@mock.patch("pubtools._executors.os.path.isdir")
@mock.patch("pubtools._executors.docker.tls.TLSConfig")
@mock.patch("pubtools._executors.APIClient")
def test_container_executor_run_cmd_error(mock_api_client, mock_tls_config, mock_isdir):
    """Test container executor running a command which fails."""
    mock_create_container = mock.MagicMock()
    mock_create_container.return_value = {"Id": "123"}
    mock_api_client.return_value.create_container = mock_create_container
    mock_start = mock.MagicMock()
    mock_api_client.return_value.start = mock_start
    mock_remove_container = mock.MagicMock()
    mock_api_client.return_value.remove_container = mock_remove_container
    mock_isdir.return_value = True

    mock_exec_create = mock.MagicMock()
    mock_exec_create.return_value = {"Id": "321"}
    mock_api_client.return_value.exec_create = mock_exec_create
    mock_exec_start = mock.MagicMock()
    mock_exec_start.return_value = b"some output"
    mock_api_client.return_value.exec_start = mock_exec_start
    mock_exec_inspect = mock.MagicMock()
    mock_exec_inspect.return_value = {"ExitCode": 1}
    mock_api_client.return_value.exec_inspect = mock_exec_inspect

    with ContainerExecutorBearer(
        "quay.io/some/image:1",
        base_url="some-url.com",
        timeout=120,
        verify_tls=True,
        cert_path="/some/path",
    ) as executor:
        with pytest.raises(RuntimeError, match="An error has occured when executing a command."):
            stdout, stderr = executor._run_cmd("cat file.txt")


@mock.patch("pubtools._executors.os.path.isdir")
@mock.patch("pubtools._executors.docker.tls.TLSConfig")
@mock.patch("pubtools._executors.APIClient")
def test_container_executor_run_cmd_error_tolerate_error(
    mock_api_client, mock_tls_config, mock_isdir
):
    """Test container executor tolerating command failure."""
    mock_create_container = mock.MagicMock()
    mock_create_container.return_value = {"Id": "123"}
    mock_api_client.return_value.create_container = mock_create_container
    mock_start = mock.MagicMock()
    mock_api_client.return_value.start = mock_start
    mock_remove_container = mock.MagicMock()
    mock_api_client.return_value.remove_container = mock_remove_container
    mock_isdir.return_value = True

    mock_exec_create = mock.MagicMock()
    mock_exec_create.return_value = {"Id": "321"}
    mock_api_client.return_value.exec_create = mock_exec_create
    mock_exec_start = mock.MagicMock()
    mock_exec_start.return_value = b"some output"
    mock_api_client.return_value.exec_start = mock_exec_start
    mock_exec_inspect = mock.MagicMock()
    mock_exec_inspect.return_value = {"ExitCode": 1}
    mock_api_client.return_value.exec_inspect = mock_exec_inspect

    with ContainerExecutorBearer(
        "quay.io/some/image:1",
        base_url="some-url.com",
        timeout=120,
        verify_tls=True,
        cert_path="/some/path",
    ) as executor:
        executor._run_cmd("cat file.txt", tolerate_err=True)


@mock.patch("pubtools._executors.os.path.isdir")
@mock.patch("pubtools._executors.docker.tls.TLSConfig")
@mock.patch("pubtools._executors.APIClient")
def test_container_executor_run_cmd_no_output(mock_api_client, mock_tls_config, mock_isdir):
    """Test container executor running command producing no output."""
    mock_create_container = mock.MagicMock()
    mock_create_container.return_value = {"Id": "123"}
    mock_api_client.return_value.create_container = mock_create_container
    mock_start = mock.MagicMock()
    mock_api_client.return_value.start = mock_start
    mock_remove_container = mock.MagicMock()
    mock_api_client.return_value.remove_container = mock_remove_container
    mock_isdir.return_value = True

    mock_exec_create = mock.MagicMock()
    mock_exec_create.return_value = {"Id": "321"}
    mock_api_client.return_value.exec_create = mock_exec_create
    mock_exec_start = mock.MagicMock()
    mock_exec_start.return_value = None
    mock_api_client.return_value.exec_start = mock_exec_start
    mock_exec_inspect = mock.MagicMock()
    mock_exec_inspect.return_value = {"ExitCode": 0}
    mock_api_client.return_value.exec_inspect = mock_exec_inspect

    with ContainerExecutorBearer(
        "quay.io/some/image:1",
        base_url="some-url.com",
        timeout=120,
        verify_tls=True,
        cert_path="/some/path",
    ) as executor:
        stdout, stderr = executor._run_cmd("cat file.txt")

    assert stdout == ""
    assert stderr == ""


@mock.patch("pubtools._executors.time.time")
@mock.patch("pubtools._executors.tarfile.TarInfo")
@mock.patch("pubtools._executors.tarfile.TarFile")
@mock.patch("pubtools._executors.io.BytesIO")
@mock.patch("pubtools._executors.os.path.isdir")
@mock.patch("pubtools._executors.docker.tls.TLSConfig")
@mock.patch("pubtools._executors.APIClient")
def test_container_executor_add_file(
    mock_api_client,
    mock_tls_config,
    mock_isdir,
    mock_bytesio,
    mock_tarfile,
    mock_tarinfo,
    mock_time,
):
    """Test container executor adding a file."""
    mock_create_container = mock.MagicMock()
    mock_create_container.return_value = {"Id": "123"}
    mock_api_client.return_value.create_container = mock_create_container
    mock_start = mock.MagicMock()
    mock_api_client.return_value.start = mock_start
    mock_remove_container = mock.MagicMock()
    mock_api_client.return_value.remove_container = mock_remove_container
    mock_isdir.return_value = True

    mock_add_file = mock.MagicMock()
    mock_tarfile.return_value.addfile = mock_add_file
    mock_close = mock.MagicMock()
    mock_tarfile.return_value.close = mock_close
    mock_bytesio1 = mock.MagicMock()
    mock_bytesio2 = mock.MagicMock()
    mock_bytesio.side_effect = [mock_bytesio1, mock_bytesio2]
    mock_seek = mock.MagicMock()
    mock_bytesio1.seek = mock_seek
    mock_put_archive = mock.MagicMock()
    mock_put_archive.return_value = True
    mock_api_client.return_value.put_archive = mock_put_archive

    with ContainerExecutorBearer(
        "quay.io/some/image:1",
        base_url="some-url.com",
        timeout=120,
        verify_tls=True,
        cert_path="/some/path",
    ) as executor:
        executor._add_file("abcdefg", "some-file.txt")

    assert mock_bytesio.call_count == 2
    mock_tarfile.assert_called_once_with(fileobj=mock_bytesio1, mode="w")
    mock_tarinfo.assert_called_once_with(name="some-file.txt")
    mock_add_file.assert_called_once_with(mock_tarinfo.return_value, mock_bytesio2)
    mock_close.assert_called_once_with()
    mock_seek.assert_called_once_with(0)
    mock_put_archive.assert_called_once_with(container="123", path="/tmp", data=mock_bytesio1)


@mock.patch("pubtools._executors.time.time")
@mock.patch("pubtools._executors.tarfile.TarInfo")
@mock.patch("pubtools._executors.tarfile.TarFile")
@mock.patch("pubtools._executors.io.BytesIO")
@mock.patch("pubtools._executors.os.path.isdir")
@mock.patch("pubtools._executors.docker.tls.TLSConfig")
@mock.patch("pubtools._executors.APIClient")
def test_container_executor_add_file_fail(
    mock_api_client,
    mock_tls_config,
    mock_isdir,
    mock_bytesio,
    mock_tarfile,
    mock_tarinfo,
    mock_time,
):
    """Test container executor adding a file ends with failure."""
    mock_create_container = mock.MagicMock()
    mock_create_container.return_value = {"Id": "123"}
    mock_api_client.return_value.create_container = mock_create_container
    mock_start = mock.MagicMock()
    mock_api_client.return_value.start = mock_start
    mock_remove_container = mock.MagicMock()
    mock_api_client.return_value.remove_container = mock_remove_container
    mock_isdir.return_value = True

    mock_add_file = mock.MagicMock()
    mock_tarfile.return_value.addfile = mock_add_file
    mock_close = mock.MagicMock()
    mock_tarfile.return_value.close = mock_close
    mock_bytesio1 = mock.MagicMock()
    mock_bytesio2 = mock.MagicMock()
    mock_bytesio.side_effect = [mock_bytesio1, mock_bytesio2]
    mock_seek = mock.MagicMock()
    mock_bytesio1.seek = mock_seek
    mock_put_archive = mock.MagicMock()
    mock_put_archive.return_value = False
    mock_api_client.return_value.put_archive = mock_put_archive

    with ContainerExecutorBearer(
        "quay.io/some/image:1",
        base_url="some-url.com",
        timeout=120,
        verify_tls=True,
        cert_path="/some/path",
    ) as executor:
        with pytest.raises(RuntimeError, match="File was not successfully added to the container"):
            executor._add_file("abcdefg", "some-file.txt")
