"""Uninstalled composition root for a future socket-activated helper.

The production nft port and privileged entry point are absent. A constrained
systemd adapter exists but is not installed or natively exercised. This root
accepts only explicit privileged ports; importing it has no side effects.
"""

from .zapret2_helper import OfflineHelper, RecoveryRequired
from .zapret2_ipc import PkcheckAuthorizer, SocketBoundary, serve_systemd_socket
from .zapret2_journal import ServiceLock
from .zapret2_process import ReservedProcessPort


class ServiceRuntime:
    def __init__(self, *, journal, artifacts, firewall, process, authorizer=None):
        if not isinstance(process, ReservedProcessPort):
            raise TypeError("Stable supervised process port required")
        self.journal = journal
        self.authorizer = authorizer or PkcheckAuthorizer()
        self.helper = OfflineHelper(self.authorizer, artifacts, journal,
                                    firewall, process)
        self.boundary = SocketBoundary(
            self.helper, self.authorizer,
            authorized_dispatch=self.helper._dispatch_authorized)
        self._guard = None

    def __enter__(self):
        if self._guard is not None:
            raise RuntimeError("Service already entered")
        if self.journal.boot != self.helper.process.boot_id:
            raise RecoveryRequired("Journal and supervisor boot identities differ")
        guard = ServiceLock(self.journal)
        guard.__enter__()
        try:
            # Fail closed on uncertain state before admitting clients.
            entry = self.journal.read()
            if self.helper.process.unclaimed_units(
                    entry.process_token if entry is not None else None):
                raise RecoveryRequired("Unclaimed supervised unit requires recovery")
            self.helper.watchdog_tick()
        except BaseException:
            guard.__exit__(None, None, None)
            raise
        self._guard = guard
        return self

    def __exit__(self, *exc):
        if self._guard is not None:
            self._guard.__exit__(*exc)
            self._guard = None

    def serve(self, *, descriptor=3):
        if self._guard is None:
            raise RuntimeError("Service lock is not held")
        serve_systemd_socket(self.boundary, descriptor=descriptor)
