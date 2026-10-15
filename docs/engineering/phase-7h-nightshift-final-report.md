# Kervan DPI — Phase 7H Nightshift 01–06 final audit

Date: 2026-10-13 (Europe/Istanbul). Status: **CONDITIONAL OFFLINE**.
The queue ends here. No Phase 7H-B1 native NFQUEUE test was begun, and no
privileged test approval was granted. The Master Blueprint was not edited.

## 1. Starting state and six checkpoints

The Nightshift began on `main` at
`a5d4cbcc42bd214aafe3284afc691a319cbd2160` with pre-existing Phase
7A–8C and Windows/rebranding edits in the working tree. STEP 01 recorded a
**217/217** local baseline; the earlier security-hardening session had
reported **188/188**. No previous phase was reset, recommitted or repeated.

| Step | Offline result | Evidence and scope |
| --- | --- | --- |
| 01 — systemd supervisor | CONDITIONAL | Fixed unit D-Bus adapter, explicit gate barrier, cgroup/boot/ownership checks; **223/223** full tests. Native systemd pending. |
| 02 — IPC authorization | CONDITIONAL | Root:root 0666 connection socket, kernel peer credentials and socket pidfd, per-action polkit boundary; **229/229** full tests. Native polkit pending. |
| 03 — trusted deployment | CONDITIONAL | Disposable 20-file package layout, root-trust checks, release marker, isolated Python import path, legacy package coexistence; **239/239** full tests. Root-owned install pending. |
| 04 — service integration | CONDITIONAL | Durable start/stop/recovery composition and post-firewall ownership recheck; **243/243** full tests. Privileged entry remains inert. |
| 05 — nft inventory | CONDITIONAL | Strict synthetic JSON model, guarded fixed plans, `create` collision behavior and explicit no-CAS limit; **255/255** full tests. Native nft reader/transaction pending. |
| 06 — watchdog/final audit | CONDITIONAL | GUI-independent, read-only decision foundation plus absent-journal queue/inventory correction; **270/270** full tests. No independent daemon installed. |

All six statuses describe **offline** evidence. They are not native deployment
or stable Linux product approval. Earlier STEP records remain in
`nightshift-7h-checkpoints.md`.

## 2. Source and deployment changes

Nightshift-created or modified backend sources include
`zapret2_systemd.py`, `zapret2_systemd_transport.py`, `zapret2_gate.py`,
`zapret2_process.py`, `zapret2_ipc.py`, `zapret2_service.py`,
`zapret2_helper.py`, `zapret2_journal.py`, `zapret2_trust.py`,
`zapret2_nft_plan.py`, `zapret2_nft_inventory.py` and
`zapret2_watchdog.py`. Corresponding `tests/test_zapret2_*.py` files cover
the fixed interfaces and failure paths. STEP 06 specifically added the
watchdog module and its 13 tests, changed the helper's no-journal absence
checks, added two helper regression tests, and refreshed the local staged
source hash list. The STEP 05 nft inventory module and STEP 06 watchdog
module are **not** part of the staged 20-file helper payload; neither is a
deployable production backend.

Packaging work resides under `packaging/linux/kervan-dpi/`, with staging in
`tools/stage_kervan_helper.py` and the future Debian split described in
`packaging/debian/zapret2-experimental.md`. The existing installed GUI package
identity remains `goodbyedpi-turkey`, with its XDG and SpoofDPI fallback
paths. The proposed root helper executable intentionally exits. No watchdog
unit or timer was installed or enabled; no separate root watchdog executable
has been approved. Existing Windows lifecycle and GUI edits were preserved.

## 3. Implemented behavior versus mocks/native gaps

| Boundary | Implemented offline | Missing native proof |
| --- | --- | --- |
| systemd process | Fixed unit/token validation, D-Bus transport code, gate handoff, boot/cgroup checks, bounded job decisions and no PID-only stop. | Real unit properties, job attribution, gate timing, full descendant cgroup teardown and restart behavior on target systemd. Mutating calls were injected in tests. |
| IPC/polkit | `SO_PEERCRED`, socket-bound `SO_PEERPIDFD`, bounded frames, fixed operation schema, observe/control actions and one authorization per socket dispatch. | Real unprivileged GUI connection, active/inactive/multi-user polkit decisions and worker-exhaustion behavior. `pkcheck` results were mocked. |
| trusted files | Fixed candidate/release paths, pinned artifact hashes, no-follow/single-link/mode/owner checks, fsynced publication and explicit rollback under disposable roots. | Independently approved package hashes, actual root and dpkg ownership, dependency mapping and safe upgrade while a service runs. |
| nftables | Strict fixture parser, exact table/rule ownership requirements, queue/mark conflict refusal where visible, fixed setup/teardown plans and post-submit reconciliation. | Exact native JSON translation, complete nft/iptables/namespace inventory, kernel generation-safe conditional submission, queue listener attribution and real rollback. |
| watchdog | Pure `assess()` decision function imports no GUI and performs no privileged effects. It models helper, worker, journal, nft, queue, cgroup, boot and generation evidence. | Independently scheduled root monitor, authoritative collectors, journal snapshot/locking protocol, real liveness and pressure telemetry, and action authorization. |

`ServiceRuntime` currently has an internal recovery tick on helper entry and
the helper service template requests `Restart=on-failure`. Neither constitutes
an independently running watchdog while the helper is unavailable. The STEP
06 decision module intentionally never kills a process, deletes a table,
starts a unit or asserts that traffic works. Its
`request_helper_reconciliation` value is a future, separately authorized
recommendation. An active helper retains the lifetime lock; an independent
monitor must not race it. The durable journal has no persisted nft generation
identifier, so a restart cannot yet prove generation continuity. Missing or
stale generation evidence blocks a healthy decision.

## 4. Recovery and fail-open matrix

| Scenario | Offline result and limit |
| --- | --- |
| GUI crash | Watchdog assessment and service ports have no PySide6 dependency. Helper/worker ownership is independent of GUI lifetime. No separate monitor process exists yet. |
| Helper crash / service restart | Known exact resources produce a request for helper reconciliation; an active helper is observed rather than raced. Existing service and supervisor tests cover restart against injected ports. |
| nfqws2 crash / lost listener | Decision becomes recovery required; mismatched worker/cgroup or foreign listener is blocked. No traffic-restoration claim follows. |
| Queue `bypass` / saturation | Decision always reports network restoration and DPI bypass as **unverified**. Saturation is degraded/operator review; unobserved pressure with an owned queue is blocked. |
| Interrupted nft setup/cleanup | `starting`/`stopping` records defer to the active helper or request later reconciliation if it failed. No watchdog-side deletion. |
| Partial rollback | Foreign/altered nft ownership is blocked. Existing helper tests retain a journal after failed rollback. |
| Corrupt/missing journal | Corruption and resources without a journal block cleanup. STEP 06 fixed `status`, `recover` and internal watchdog tick so a foreign queue or incomplete inventory cannot be reported inactive when the journal is absent. |
| Reboot / stale generation | Mismatched boot or absent/stale generation evidence blocks a healthy decision and automatic cleanup. |
| Competing units/processes | Unclaimed unit, wrong queue/worker/cgroup/table token and unknown ownership block. No numeric PID is a termination authority. |
| Repeated recovery / unavailable monitor | Repeated decisions are stable. An unavailable monitor is explicitly unavailable, not a fail-open guarantee. |

The [nftables queue documentation](https://wiki.nftables.org/wiki-nftables/index.php/Queueing_to_userspace)
describes `bypass` for a queue without a listener. The
[libnetfilter_queue documentation](https://netfilter.org/projects/libnetfilter_queue/doxygen/html/)
states that packets may be dropped when a queue is full unless a separate
fail-open queue setting is used. These are distinct failure modes. Even if
packets pass normally, that does not prove DPI circumvention. Queue capacity,
listener loss, VPN/network namespace behavior, IPv4/IPv6, TCP/UDP and real
network reachability have not been measured here.

## 5. Security integration audit

Completed checks: fixed IPC commands and strategies prevent caller-injected
paths/nft syntax; socket authorization uses kernel credentials and denies a
missing pidfd; read/control polkit actions are separate; root import paths
are fixed and Python is isolated in the staged entry points; release and
journal code reject symlinks, hardlinks, writable ancestors and corruption;
systemd ownership checks bind token, boot, fixed unit and cgroup; nft planning
requires exact ownership and never emits `flush ruleset`; helper recovery
keeps uncertain resources/journal rather than declaring success. Individual
subprocess calls have explicit timeouts in the tested boundaries. The GUI
does not import the privileged service or watchdog. The available Linux-run
Windows lifecycle and SpoofDPI regressions pass.

STEP 06 found and fixed a false inactive result when the journal/table were
absent but a queue listener remained, plus the same result for an incomplete
firewall inventory. Two targeted regression tests cover those cases. The
read-only watchdog model adds no privilege elevation path. Audit limits:
root:root 0666 permits any local account to connect, creating a bounded
worker-exhaustion risk; native polkit/DoS behavior is unverified. Filesystem
checks do not establish actual package ownership. Multiple bounded systemd
D-Bus calls do not yet prove a strict aggregate native operation deadline.
Root package upgrades and systemd/polkit policy interactions remain untested.

## 6. Test evidence and intermediate failures

STEP 06 focused run: **193/193 PASS** across helper **33**, IPC **13**,
systemd adapter **20**, D-Bus transport **5**, gate **5**, trusted release
**11**, package staging **10**, journal **5**, process supervision **10**,
nft inventory **12**, isolated nft adapter **4**, watchdog **13**, service
**7**, Zapret2 regression **19** and Windows/Linux lifecycle **26**.
The final full suite passed **270/270**. `compileall -q src tests tools`,
`git diff --check`, the final untracked-source integrity scan and the local
20-file staging hash check are recorded in STEP 06.

Earlier Nightshift intermediate failures were disclosed and resolved:
STEP 01's fake D-Bus row was incomplete (**1/17** failed initially); STEP
03's simulated legacy `/opt` mode inherited group write permission (**1/23**
failed initially); STEP 04's new test used a fixed unit instead of the
generated owner token (**1/27** failed initially). The fixtures were corrected,
with later targeted and full suites passing. STEP 02, STEP 05 and STEP 06
had no reported intermediate test failures. No timeout was enlarged or
production security check relaxed to pass a test.

## 7. Requirements before any native or privileged test

1. **Isolated environment:** a disposable VM with snapshot/restore,
   out-of-band console, no production bridge/route, known test endpoints,
   captured nft/iptables state, controlled IPv4/IPv6 and measured queue
   behavior. Network isolation must be verified before interception.
2. **systemd:** install only independently reviewed root-owned units in the
   isolated VM; verify actual D-Bus replies, gate pre-exec barrier, helper
   restart, boot identity and complete descendant cgroup cleanup under
   injected crashes and shutdown timeouts.
3. **polkit and IPC:** confirm ordinary GUI user connectivity to the 0666
   socket, kernel pidfd availability, real active/inactive/multi-user policy,
   agent cancellation, disconnect handling and service availability under
   abusive clients.
4. **Root trust:** independently approve artifact and helper hashes; verify
   dpkg ownership of every `/usr`, `/usr/libexec` and `/opt` path, dependencies,
   root-only import tree, no manual path collisions and upgrade/rollback while
   a service is running. Do not rely on the writable checkout manifest.
5. **nft/NFQUEUE:** capture exact native JSON for generated rules, prove
   complete inventory across nft/iptables and relevant namespaces, define a
   real transaction/concurrency protocol or preserve fail-closed
   reconciliation, validate listener-to-cgroup attribution, queue saturation,
   `bypass`, fail-open flags, conntrack marks and traffic outcomes.
6. **Watchdog:** review a fixed root-owned independent service/timer and
   collector, safe read-only journal snapshot protocol and serialized handoff
   to helper recovery. Prove behavior when watchdog or helper is unavailable.

No approval for privileged testing exists in this session. Preparing a
read-only Phase 7H-B1 native isolated test plan is permissible; installing
units, loading modules, modifying a firewall/route/DNS setting or activating
NFQUEUE requires a separate explicit approval for a concrete isolated plan.
Phase 7H-B1 was **not** started.

## 8. Final readiness and Git state

- **Offline engineering ready:** CONDITIONAL — models and regression gates
  support a read-only B1 preparation plan.
- **Native test environment ready:** NO — no reviewed isolated VM/package,
  complete collector or independent watchdog installation has been shown.
- **Privileged test approval granted:** NO.
- **Live network activation ready:** NO.

Git remains on `main` at
`a5d4cbcc42bd214aafe3284afc691a319cbd2160`. The preexisting 19 tracked
modified files remain, alongside the untracked Nightshift backend, tests,
packaging and documentation files: **73 untracked files** in the final
integrity scan. There was no reset/clean/stash, commit, push, tag, release, package
installation, root helper/watchdog launch, systemd mutation, firewall change,
NFQUEUE activation, kernel module load, DNS/route/NetworkManager change,
configuration migration or Master Blueprint update.
