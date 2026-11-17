"""Send bounded JSON jobs through the user's authenticated SSH connection."""

import base64
import json
import os
import shlex
import subprocess
from pathlib import Path


def call_agent(config, payload, timeout=240):
    worker = Path(__file__).with_name("agent_worker.py").read_bytes()
    code = "import base64;exec(base64.b64decode(" + repr(base64.b64encode(worker).decode("ascii")) + "))"
    remote = shlex.join(
        [
            "docker",
            "compose",
            "--project-directory",
            "/opt/wisland-knowledge-server",
            "-f",
            "/opt/wisland-knowledge-server/compose.yaml",
            "exec",
            "-T",
            "knowledge",
            "python",
            "-c",
            code,
        ]
    )
    key = config.get("ssh_key") or str(Path.home() / ".ssh/wisland_deploy_ed25519")
    command = [
        "ssh",
        "-T",
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "LogLevel=ERROR",
        "-i",
        key,
        "-p",
        str(config.get("ssh_port", 22)),
        config.get("ssh_user", "root") + "@" + config.get("ssh_host", ""),
        remote,
    ]
    result = subprocess.run(
        command,
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        timeout=timeout,
        creationflags=0x08000000 if os.name == "nt" else 0,
    )
    try:
        value = json.loads(result.stdout.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("整理任务未返回有效结果，SSH/容器状态需要检查") from exc
    if result.returncode or "error" in value:
        raise ValueError("云端整理未完成：" + str(value.get("error", "SSH error")))
    return value
