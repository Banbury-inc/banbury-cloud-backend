from io import StringIO
from typing import Any


def _parse_private_key(private_key: str, passphrase: str | None):
    try:
        import paramiko
    except ImportError:
        return None, "SSH private key authentication requires paramiko"

    key_factories = (
        paramiko.RSAKey,
        paramiko.ECDSAKey,
        paramiko.Ed25519Key,
        paramiko.DSSKey,
    )
    for key_factory in key_factories:
        try:
            parsed_key = key_factory.from_private_key(
                StringIO(private_key),
                password=passphrase or None,
            )
            return parsed_key, None
        except Exception:
            continue

    return None, "Invalid SSH private key"


def create_ssh_tunnel(connection: dict[str, Any]):
    ssh_config = connection.get("ssh")
    if not isinstance(ssh_config, dict) or not ssh_config.get("enabled"):
        return None, None

    try:
        from sshtunnel import SSHTunnelForwarder
    except ImportError:
        return None, "SSH tunneling requires sshtunnel"

    forwarder_kwargs: dict[str, Any] = {
        "ssh_address_or_host": (ssh_config["host"], ssh_config["port"]),
        "ssh_username": ssh_config["username"],
        "remote_bind_address": (connection["host"], connection["port"]),
        "local_bind_address": ("127.0.0.1", 0),
    }

    auth_method = ssh_config.get("authMethod", "password")
    if auth_method == "publicKey":
        private_key, key_error = _parse_private_key(
            ssh_config.get("privateKey", ""),
            ssh_config.get("passphrase"),
        )
        if key_error:
            return None, key_error
        forwarder_kwargs["ssh_pkey"] = private_key
    else:
        forwarder_kwargs["ssh_password"] = ssh_config["password"]

    try:
        tunnel = SSHTunnelForwarder(**forwarder_kwargs)
        tunnel.start()
        return tunnel, None
    except Exception:
        return None, "Unable to establish SSH tunnel"
