"""Namespace-only nft batch adapter for isolated integration tests.

This is deliberately not a host production executor.  Its inventory reader
must be independently implemented and must report complete, generation-aware
snapshots.  A CLI read followed by a CLI write cannot provide kernel CAS.
"""

import os
import ctypes
import stat
import subprocess

from .zapret2_nft_plan import (CollisionError, Inventory, Transaction,
                               setup_plan, teardown_plan)

NFT = "/usr/sbin/nft"
NSENTER = "/usr/bin/nsenter"
NSFS_MAGIC = 0x6e736673


def _filesystem_magic(fd):
    # Linux statfs begins with a native long f_type. Reserve more than the
    # current struct size so libc can fill the whole structure safely.
    value = ctypes.create_string_buffer(256)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.fstatfs(fd, value) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return ctypes.c_long.from_buffer(value).value


class IsolatedNftExecutor:
    """Execute fixed plans only through a preopened, non-host network namespace."""

    def __init__(self, namespace, inventory_reader, queue_reader,
                 *, runner=subprocess.run, execute=False):
        self.inventory_reader = inventory_reader
        self.queue_reader = queue_reader
        self.runner = runner
        self.execute = execute
        self.namespace_fd = os.open(namespace, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            self._check_namespace()
        except BaseException:
            os.close(self.namespace_fd)
            raise

    def close(self):
        if self.namespace_fd is not None:
            os.close(self.namespace_fd)
            self.namespace_fd = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _check_namespace(self):
        selected = os.fstat(self.namespace_fd)
        own = os.stat("/proc/self/ns/net")
        init = os.stat("/proc/1/ns/net")
        identity = (selected.st_dev, selected.st_ino)
        if not stat.S_ISREG(selected.st_mode) or _filesystem_magic(self.namespace_fd) != NSFS_MAGIC:
            raise ValueError("Invalid namespace descriptor")
        if identity in ((own.st_dev, own.st_ino), (init.st_dev, init.st_ino)):
            raise PermissionError("Host network namespace is forbidden")

    def inventory(self):
        value = self.inventory_reader(self.namespace_fd)
        if not isinstance(value, Inventory) or value.complete is not True:
            raise CollisionError("Incomplete isolated nft inventory")
        return value

    def queue_owner(self, queue):
        return self.queue_reader(self.namespace_fd, queue)

    def apply(self, plan, timeout):
        if not self.execute:
            raise PermissionError("Isolated nft execution is not armed")
        if not isinstance(plan, Transaction) or not 0 < timeout <= 10:
            raise ValueError("Invalid nft transaction")
        self._check_namespace()
        before = self.inventory()
        if (before.generation != plan.expected_generation or
                before.table != plan.expected_table):
            raise CollisionError("Isolated ruleset changed before batch")
        table = plan.expected_after or plan.expected_table
        if table is None or not table.rules:
            raise ValueError("No owned table in transaction")
        owner = table.rules[0].owner
        expected = (setup_plan(before, owner) if plan.expected_after is not None else
                    teardown_plan(before, owner))
        if plan != expected or not plan.commands:
            raise ValueError("Nft batch differs from fixed template")
        script = "\n".join(plan.commands) + "\n"
        self._check_namespace()
        self.runner([NSENTER, f"--net=/proc/self/fd/{self.namespace_fd}",
                     NFT, "-f", "-"], input=script, text=True,
                    pass_fds=(self.namespace_fd,), timeout=timeout, check=True,
                    env={"PATH": "/usr/sbin:/usr/bin:/bin", "LANG": "C"},
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        after = self.inventory()
        if after.table != plan.expected_after:
            raise CollisionError("Nft batch result differs from fixed template")
