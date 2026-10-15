import subprocess
import ctypes
import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.paths import config_dir, resource_path, resource_root
from utils.config import ConfigManager
from utils.runner import DNSRunner, _stage_windows_engine, build_windows_command, find_spoof_dpi
from utils.startup import startup_path, set_enabled


class FakeProcess:
    def __init__(self, exited=False, timeout=False):
        self.returncode = 0 if exited else None
        self.timeout = timeout
        self.events = []
        self.stdin = Mock()
        self.stdout = Mock()
        self.stderr = Mock()

    def poll(self):
        return self.returncode

    def terminate(self):
        self.events.append("terminate")

    def kill(self):
        self.events.append("kill")
        self.returncode = -9

    def wait(self, timeout=None):
        self.events.append("wait")
        if self.timeout:
            self.timeout = False
            raise subprocess.TimeoutExpired("engine", timeout)
        self.returncode = 0 if self.returncode is None else self.returncode
        return self.returncode


class RunnerStopTests(unittest.TestCase):
    def runner(self, process):
        with patch("utils.runner.atexit.register"):
            runner = DNSRunner()
        runner.process = process
        return runner

    def test_graceful_terminate_reaps_and_closes_resources(self):
        process = FakeProcess()
        runner = self.runner(process)
        output_thread = Mock()
        output_thread.is_alive.return_value = False
        runner.output_thread = output_thread
        runner.stop()
        self.assertEqual(process.events, ["terminate", "wait"])
        for pipe in (process.stdin, process.stdout, process.stderr):
            pipe.close.assert_called_once()
        self.assertIsNone(runner.process)
        output_thread.join.assert_called_once_with(timeout=3)
        runner.stop()
        self.assertEqual(process.events, ["terminate", "wait"])

    def test_timeout_kills_then_waits_again(self):
        process = FakeProcess(timeout=True)
        runner = self.runner(process)
        runner.stop()
        self.assertEqual(process.events, ["terminate", "wait", "kill", "wait"])
        self.assertIsNone(runner.process)

    def test_already_exited_is_reaped_without_terminate(self):
        process = FakeProcess(exited=True)
        runner = self.runner(process)
        runner.stop()
        self.assertEqual(process.events, ["wait"])
        self.assertIsNone(runner.process)

    def test_stop_without_process_is_repeatable(self):
        runner = self.runner(None)
        runner.stop()
        runner.stop()
        self.assertIsNone(runner.process)

    def test_job_handle_is_closed_once_without_process(self):
        runner = self.runner(None)
        runner.os_type = 'windows'
        runner.job_handle = 123
        close_handle = Mock(return_value=1)
        class FakeJobAccounting(ctypes.Structure):
            _fields_ = [('ActiveProcesses', ctypes.c_ulong)]

        def query_job(handle, info_class, buffer, size, returned):
            self.assertEqual((handle, info_class), (123, 1))
            self.assertEqual(size, ctypes.sizeof(FakeJobAccounting))
            ctypes.cast(buffer, ctypes.POINTER(FakeJobAccounting)).contents.ActiveProcesses = 0
            return 1
        query = Mock(side_effect=query_job)
        fake_windll = SimpleNamespace(kernel32=SimpleNamespace(
            QueryInformationJobObject=query, CloseHandle=close_handle))
        with patch("utils.runner.ctypes.windll", fake_windll, create=True), \
             patch("utils.runner.JOBOBJECT_BASIC_ACCOUNTING_INFORMATION",
                   FakeJobAccounting, create=True):
            runner.stop()
            runner.stop()
        query.assert_called_once()
        close_handle.assert_called_once_with(123)
        self.assertIsNone(runner.job_handle)

    def test_broken_stream_does_not_skip_other_cleanup(self):
        process = FakeProcess()
        process.stdin.close.side_effect = OSError("already closed")
        runner = self.runner(process)
        with self.assertLogs("utils.runner", level="WARNING"):
            runner.stop()
        process.stdout.close.assert_called_once()
        process.stderr.close.assert_called_once()
        self.assertIsNone(runner.process)

    def test_terminate_error_still_waits_and_reaps(self):
        process = FakeProcess()
        process.terminate = Mock(side_effect=ProcessLookupError())
        runner = self.runner(process)
        runner.stop()
        self.assertEqual(process.events, ["wait"])
        self.assertIsNone(runner.process)

    def test_second_wait_is_bounded_and_keeps_unreaped_process(self):
        process = FakeProcess()
        process.wait = Mock(side_effect=subprocess.TimeoutExpired("engine", 3))
        runner = self.runner(process)
        with self.assertLogs("utils.runner", level="WARNING"):
            runner.stop()
        self.assertEqual(process.wait.call_count, 3)
        self.assertTrue(all(call.kwargs == {"timeout": 3} for call in process.wait.call_args_list))
        self.assertIs(runner.process, process)

    def test_explicit_close_unregisters_atexit_fallback(self):
        process = FakeProcess()
        runner = self.runner(process)
        with patch("utils.runner.atexit.unregister") as unregister:
            runner.close()
        unregister.assert_called_once_with(runner.stop)
        self.assertIsNone(runner.process)

    def test_unreaped_process_keeps_atexit_fallback(self):
        process = FakeProcess()
        process.wait = Mock(side_effect=subprocess.TimeoutExpired("engine", 3))
        runner = self.runner(process)
        with patch("utils.runner.atexit.unregister") as unregister, \
             self.assertLogs("utils.runner", level="WARNING"):
            runner.close()
        unregister.assert_not_called()
        self.assertIs(runner.process, process)

    def test_windows_job_waits_for_all_members_before_closing(self):
        process = FakeProcess()
        process._handle = Mock()
        runner = self.runner(process)
        runner.os_type = 'windows'
        runner.job_handle = 123
        counts = iter((1, 0))
        def active_processes():
            process._handle.Close.assert_called_once()
            return next(counts)
        runner._job_active_processes = Mock(side_effect=active_processes)
        with patch.object(runner, '_close_job_handle') as close, \
             patch('utils.runner.threading.Event') as event:
            runner.stop()
        close.assert_called_once()
        self.assertEqual(runner._job_active_processes.call_count, 2)
        event.return_value.wait.assert_called_once()

    def test_windows_job_timeout_retains_handle_for_retry(self):
        runner = self.runner(FakeProcess())
        runner.os_type = 'windows'
        runner.job_handle = 123
        runner._wait_for_job_empty = Mock(side_effect=[False, False])
        terminate = Mock(return_value=1)
        windll = SimpleNamespace(kernel32=SimpleNamespace(TerminateJobObject=terminate))
        with patch('utils.runner.ctypes.windll', windll, create=True), \
             self.assertLogs('utils.runner', level='WARNING'):
            runner.stop()
        terminate.assert_called_once_with(123, 1)
        self.assertEqual(runner.job_handle, 123)
        self.assertIsNotNone(runner.process)

    def test_windows_handle_closes_after_job_finishes_unreaped_process(self):
        process = FakeProcess()
        process._handle = Mock()
        process.wait = Mock(side_effect=[subprocess.TimeoutExpired('engine', 3),
                                         subprocess.TimeoutExpired('engine', 3), 0])
        runner = self.runner(process)
        runner.os_type = 'windows'
        runner.job_handle = 123
        runner._wait_for_job_empty = Mock(return_value=True)
        with patch.object(runner, '_close_job_handle', side_effect=lambda: setattr(
                runner, 'job_handle', None)):
            runner.stop()
        process._handle.Close.assert_called_once()
        self.assertIsNone(runner.process)

    def test_windows_handle_close_failure_retains_process_for_retry(self):
        process = FakeProcess()
        process._handle = Mock()
        process._handle.Close.side_effect = [OSError('busy'), None]
        runner = self.runner(process)
        runner.os_type = 'windows'
        with self.assertLogs('utils.runner', level='WARNING'):
            runner.stop()
        self.assertIs(runner.process, process)
        runner.stop()
        self.assertIsNone(runner.process)
        self.assertEqual(process._handle.Close.call_count, 2)

    def test_start_rejects_previous_resources_that_did_not_clear(self):
        runner = self.runner(FakeProcess(exited=True))
        runner.job_handle = 123
        with patch.object(runner, 'stop') as stop:
            with self.assertRaisesRegex(RuntimeError, 'still active'):
                runner.start()
        stop.assert_called_once()


class WindowsStagingTests(unittest.TestCase):
    def test_goodbyedpi_arguments_are_unchanged_by_branding(self):
        self.assertEqual(build_windows_command(r"C:\engine\goodbyedpi.exe", "77.88.8.8", "1253"),
                         [r"C:\engine\goodbyedpi.exe", "-5", "--set-ttl", "5",
                          "--dns-addr", "77.88.8.8", "--dns-port", "1253",
                          "--dnsv6-addr", "2a02:6b8::feed:0ff", "--dnsv6-port", "1253"])

    def test_driver_image_is_staged_outside_onefile_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / '_MEI123' / 'bin' / 'x86_64'
            source.mkdir(parents=True)
            for name in ('goodbyedpi.exe', 'WinDivert.dll', 'WinDivert64.sys'):
                (source / name).write_bytes(name.encode())
            with patch('utils.runner._program_files', return_value=root / 'Program Files'):
                executable = _stage_windows_engine(source, 'x86_64')
                self.assertEqual(_stage_windows_engine(source, 'x86_64'), executable)
            self.assertEqual(executable.read_bytes(), b'goodbyedpi.exe')
            self.assertEqual((executable.parent / 'WinDivert64.sys').read_bytes(),
                             b'WinDivert64.sys')
            self.assertNotIn('_MEI123', str(executable))

    def test_staged_engine_detects_modified_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.mkdir()
            for name in ('goodbyedpi.exe', 'WinDivert.dll', 'WinDivert32.sys',
                         'WinDivert64.sys'):
                (source / name).write_bytes(name.encode())
            with patch('utils.runner._program_files', return_value=root / 'Program Files'):
                executable = _stage_windows_engine(source, 'x86')
                (executable.parent / 'WinDivert.dll').write_bytes(b'tampered')
                with self.assertRaisesRegex(OSError, 'differs'):
                    _stage_windows_engine(source, 'x86')

    def test_staging_rejects_existing_file_and_removes_failed_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.mkdir()
            for name in ('goodbyedpi.exe', 'WinDivert.dll', 'WinDivert64.sys'):
                (source / name).write_bytes(name.encode())
            program_files = root / 'Program Files'
            with patch('utils.runner._program_files', return_value=program_files):
                executable = _stage_windows_engine(source, 'x86_64')
                destination = executable.parent
                for child in destination.iterdir():
                    child.unlink()
                destination.rmdir()
                destination.write_text('occupied')
                with self.assertRaisesRegex(OSError, 'not a directory'):
                    _stage_windows_engine(source, 'x86_64')
                destination.unlink()
                with patch('utils.runner.shutil.copyfile', side_effect=OSError('copy failed')):
                    with self.assertRaisesRegex(OSError, 'copy failed'):
                        _stage_windows_engine(source, 'x86_64')
            self.assertEqual(list(destination.parent.iterdir()), [])

    def test_staging_rejects_linked_engine_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.mkdir()
            for name in ('goodbyedpi.exe', 'WinDivert.dll', 'WinDivert64.sys'):
                (source / name).write_bytes(name.encode())
            program_files = root / 'Program Files'
            app_directory = program_files / 'GoodbyeDPI-Turkey'
            app_directory.parent.mkdir()
            try:
                app_directory.symlink_to(source, target_is_directory=True)
            except OSError:
                self.skipTest('Creating a directory link requires Windows developer privileges')
            with patch('utils.runner._program_files', return_value=program_files):
                with self.assertRaisesRegex(OSError, 'reparse point'):
                    _stage_windows_engine(source, 'x86_64')


class PlatformPathsTests(unittest.TestCase):
    def test_config_directories(self):
        home = Path("/home/user")
        self.assertEqual(config_dir("linux", {}, home), home / ".config/goodbyedpi-turkey")
        self.assertEqual(config_dir("linux", {"XDG_CONFIG_HOME": "/tmp/cfg"}, home),
                         Path("/tmp/cfg/goodbyedpi-turkey"))
        self.assertEqual(config_dir("win32", {"APPDATA": "C:/Users/u/AppData/Roaming"}, home),
                         Path("C:/Users/u/AppData/Roaming/GoodbyeDPI-Turkey"))

    def test_autostart_platform_selection(self):
        home = Path("/home/user")
        self.assertEqual(startup_path("linux", {}, home),
                         home / ".config/autostart/goodbyedpi-turkey.desktop")
        self.assertEqual(startup_path("win32", {"APPDATA": "C:/Users/u/AppData/Roaming"}, home),
                         Path("C:/Users/u/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/Kervan DPI.lnk"))

    def test_source_and_frozen_resources(self):
        with patch.object(sys, "frozen", False, create=True):
            self.assertTrue(resource_path("assets", "icon.png").is_file())
        with patch.object(sys, "frozen", True, create=True), patch.object(
            sys, "_MEIPASS", "/tmp/frozen-bundle", create=True
        ):
            self.assertEqual(resource_root(), Path("/tmp/frozen-bundle"))
            self.assertEqual(resource_path("bin", "x86_64", "goodbyedpi.exe"),
                             Path("/tmp/frozen-bundle/bin/x86_64/goodbyedpi.exe"))

    def test_config_is_written_below_user_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = ConfigManager(Path(directory) / "settings")
            settings.save_config("dns_provider", "Cloudflare")
            self.assertEqual(ConfigManager(Path(directory) / "settings").get("dns_provider"), "Cloudflare")

    def test_linux_autostart_can_be_enabled_and_removed(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(sys, "platform", "linux"), \
             patch.dict("os.environ", {"XDG_CONFIG_HOME": directory}):
            set_enabled(True)
            entry = Path(directory) / "autostart/goodbyedpi-turkey.desktop"
            self.assertIn("--minimized", entry.read_text(encoding="utf-8"))
            set_enabled(False)
            self.assertFalse(entry.exists())

    def test_spoofdpi_is_found_in_user_install_location(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / ".spoof-dpi/bin/spoof-dpi"
            binary.parent.mkdir(parents=True)
            binary.touch(mode=0o755)
            with patch("utils.runner.shutil.which", return_value=None), \
                 patch("utils.runner.Path.home", return_value=Path(directory)):
                self.assertEqual(find_spoof_dpi(), str(binary))



if __name__ == "__main__":
    unittest.main()
