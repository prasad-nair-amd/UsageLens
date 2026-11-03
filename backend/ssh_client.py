"""Paramiko connection helper, including jump-host support.

Two jump-host strategies:
1. jump_alias set: connect to jump host, run commands on target via
   `ssh <alias> <command>` (the jump host's ~/.ssh/config handles auth/routing).
2. jump_alias NOT set (legacy): open a direct-tcpip tunnel through the jump host
   and do a second SSH handshake to the target through the tunnel.
"""

import re
import paramiko


def _to_wsl_path(path):
    """Convert a Windows path (C:\\foo\\bar) to WSL /mnt/c/foo/bar if needed."""
    if not path:
        return path
    m = re.match(r"^([A-Za-z]):[/\\]", path)
    if m:
        drive = m.group(1).lower()
        rest = path[len(m.group(0)):].replace("\\", "/")
        return f"/mnt/{drive}/{rest}"
    return path


class SSHConnectError(Exception):
    pass


def _connect_direct(host_cfg, sock=None):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    kwargs = dict(
        hostname=host_cfg["hostname"],
        port=int(host_cfg.get("port") or 22),
        username=host_cfg["username"],
        timeout=15,
        banner_timeout=15,
        auth_timeout=15,
    )
    if sock is not None:
        kwargs["sock"] = sock

    if host_cfg.get("auth_method") == "password":
        kwargs["password"] = host_cfg.get("password") or ""
    else:
        identity_file = host_cfg.get("identity_file")
        if not identity_file:
            raise SSHConnectError("No identity file configured for key-based auth")
        pkey = _load_private_key(identity_file, host_cfg.get("identity_passphrase"))
        kwargs["pkey"] = pkey
        kwargs["look_for_keys"] = False
        kwargs["allow_agent"] = False

    try:
        client.connect(**kwargs)
    except Exception as exc:
        raise SSHConnectError(f"{host_cfg.get('hostname')}: {exc}") from exc
    return client


def _load_private_key(path, passphrase=None):
    path = _to_wsl_path(path)
    last_err = None
    key_types = [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey]
    if hasattr(paramiko, "DSSKey"):
        key_types.append(paramiko.DSSKey)
    for key_cls in key_types:
        try:
            return key_cls.from_private_key_file(path, password=passphrase)
        except Exception as exc:
            last_err = exc
    raise SSHConnectError(f"Could not load identity file '{path}': {last_err}")


def _shell_quote(s):
    """Single-quote a string for safe use in a remote shell command."""
    return "'" + s.replace("'", "'\\''") + "'"


def connect(host_cfg, jump_host_cfg=None):
    """Connect to host_cfg, optionally hopping through jump_host_cfg.

    If host_cfg has a jump_alias, returns (jump_client, None) — commands should
    be run via run_command_via_jump(). Otherwise returns (target_client, jump_client_or_None).
    """
    if jump_host_cfg is None:
        return _connect_direct(host_cfg), None

    jump_alias = host_cfg.get("jump_alias")

    try:
        jump_client = _connect_direct(jump_host_cfg)
    except SSHConnectError as exc:
        raise SSHConnectError(f"Jump host ({jump_host_cfg.get('hostname')}): {exc}") from exc

    if jump_alias:
        return jump_client, None

    transport = jump_client.get_transport()
    if transport is None or not transport.is_active():
        jump_client.close()
        raise SSHConnectError(
            f"Jump host ({jump_host_cfg.get('hostname')}): connected but SSH transport "
            "is not active — the jump host may have closed the session after auth"
        )

    dest_addr = (host_cfg["hostname"], int(host_cfg.get("port") or 22))
    src_addr = ("127.0.0.1", 0)
    try:
        channel = transport.open_channel("direct-tcpip", dest_addr, src_addr, timeout=15)
    except Exception as exc:
        jump_client.close()
        raise SSHConnectError(
            f"Jump host ({jump_host_cfg.get('hostname')}) connected, but could not open "
            f"tunnel to {dest_addr[0]}:{dest_addr[1]} — is the target reachable from the "
            f"jump host? Detail: {exc}"
        ) from exc

    if channel is None:
        jump_client.close()
        raise SSHConnectError(
            f"Jump host ({jump_host_cfg.get('hostname')}) refused the tunnel to "
            f"{dest_addr[0]}:{dest_addr[1]}"
        )

    try:
        target_client = _connect_direct(host_cfg, sock=channel)
    except SSHConnectError as exc:
        jump_client.close()
        raise SSHConnectError(
            f"Tunnel through jump host opened, but connecting to target "
            f"({host_cfg.get('hostname')}) failed: {exc}"
        ) from exc
    except Exception:
        jump_client.close()
        raise
    return target_client, jump_client


def run_command(client, command, timeout=30):
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return exit_code, out, err


def run_command_via_jump(jump_client, alias, command, timeout=30):
    """Run a command on a target host by executing `ssh <alias> <command>` on the jump host."""
    wrapped = f"ssh -o StrictHostKeyChecking=no -o BatchMode=yes {_shell_quote(alias)} {_shell_quote(command)}"
    return run_command(jump_client, wrapped, timeout=timeout)


def run_slurm_batch(client, salloc_cmd, setup_cmds, commands, timeout=120):
    """Run multiple commands on a Slurm-allocated node in a single allocation.

    Uses srun to execute on the allocated node (not the controller).
    The allocation is automatically released when srun completes.
    Returns (results_dict, node_name, exit_code, stderr).
    """
    parts = []
    parts.append("echo __USAGELENS_NODE__")
    parts.append("hostname")
    for i, cmd in enumerate(commands):
        parts.append(f"echo __USAGELENS_CMD_{i}__")
        parts.append(cmd)
    parts.append("echo __USAGELENS_END__")

    setup_str = "; ".join(c.strip() for c in setup_cmds if c.strip())
    if setup_str:
        inner = setup_str + "; " + "; ".join(parts)
    else:
        inner = "; ".join(parts)

    wrapped = f"{salloc_cmd} srun bash -lc {_shell_quote(inner)}"
    exit_code, out, err = run_command(client, wrapped, timeout=timeout)

    # Filter out Slurm's own messages from stdout (they start with salloc:/srun:)
    filtered_lines = [line for line in out.splitlines() if not line.startswith(("salloc:", "srun:"))]
    out = "\n".join(filtered_lines)

    err_lower = err.lower()
    if exit_code != 0:
        if "busy" in err_lower or "unable to allocate" in err_lower:
            raise SSHConnectError("Slurm allocation failed: node is currently busy (allocated by another user). Try again later.")
        if "invalid reservation" in err_lower or "reservation not found" in err_lower:
            raise SSHConnectError(f"Slurm allocation failed: reservation not found or expired. Detail: {err.strip()}")
        if "invalid account" in err_lower:
            raise SSHConnectError(f"Slurm allocation failed: invalid account. Detail: {err.strip()}")
        if "permission denied" in err_lower:
            raise SSHConnectError(f"Slurm allocation failed: permission denied. Detail: {err.strip()}")
        if "__USAGELENS_NODE__" not in out:
            raise SSHConnectError(f"Slurm salloc/srun failed (exit {exit_code}). Detail: {err.strip() or out.strip()[:300]}")

    # Extract node name
    node_name = ""
    node_start = out.find("__USAGELENS_NODE__")
    if node_start != -1:
        node_section = out[node_start + len("__USAGELENS_NODE__"):out.find("__USAGELENS_CMD_0__")].strip()
        node_name = node_section.splitlines()[0].strip() if node_section else ""

    # Parse each command's output
    results = {}
    for i, cmd in enumerate(commands):
        marker = f"__USAGELENS_CMD_{i}__"
        next_marker = f"__USAGELENS_CMD_{i+1}__" if i + 1 < len(commands) else "__USAGELENS_END__"
        start = out.find(marker)
        if start == -1:
            results[cmd] = ""
            continue
        start += len(marker) + 1
        end = out.find(next_marker, start)
        if end == -1:
            end = len(out)
        results[cmd] = out[start:end].strip()

    return results, node_name, exit_code, err, out


def test_jump_alias(jump_client, alias, timeout=15):
    """Verify the jump host can reach the target alias by running `ssh <alias> echo ok`."""
    exit_code, out, err = run_command_via_jump(jump_client, alias, "echo ok", timeout=timeout)
    if exit_code != 0 or "ok" not in out:
        detail = err.strip() or out.strip() or f"exit code {exit_code}"
        raise SSHConnectError(
            f"Jump host connected, but could not reach target via 'ssh {alias}': {detail}"
        )
