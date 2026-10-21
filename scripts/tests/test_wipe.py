import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class WipeTests(unittest.TestCase):
    def run_wipe(self, failure="", services="db\nredis\nplatform\nqueue\nscheduler\nweb\n"):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            docker = temp / "docker"
            docker.write_text('''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ['WIPE_LOG'], 'a') as log:
    log.write(json.dumps(args) + '\\n')
if args[1:2] == ['ps']:
    print(os.environ['WIPE_SERVICES'], end='')
elif 'pg_dump' in args:
    if os.environ['WIPE_FAILURE'] == 'backup': sys.exit(7)
    print('-- database backup')
elif 'psql' in args and os.environ['WIPE_FAILURE'] == 'reset':
    sys.exit(8)
''')
            docker.chmod(0o755)
            (temp / "calls.jsonl").touch()
            env = {**os.environ, "PATH": f"{temp}:{os.environ['PATH']}", "TMPDIR": directory,
                   "WIPE_LOG": str(temp / "calls.jsonl"), "WIPE_FAILURE": failure, "WIPE_SERVICES": services}
            result = subprocess.run(["make", "wipe"], cwd=ROOT, env=env, capture_output=True, text=True)
            calls = [json.loads(line) for line in (temp / "calls.jsonl").read_text().splitlines()]
            self.assertTrue(calls, result.stderr)
            backups = [path.read_text() for path in temp.glob('content-before-reset-*.sql')]
            return result, calls, backups

    def test_reset_backs_up_before_truncating_and_restores_running_services(self):
        result, calls, backups = self.run_wipe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[1], ['compose', 'stop', 'platform', 'queue', 'scheduler'])
        self.assertIn('pg_dump', calls[2])
        self.assertIn('psql', calls[3])
        self.assertIn('RESTART IDENTITY', calls[3][-1])
        self.assertNotIn('migrations', calls[3][-1])
        self.assertNotIn('users', calls[3][-1])
        self.assertEqual(calls[4][:4], ['compose', 'exec', '-T', 'redis'])
        self.assertIn('queues:', calls[4][-1])
        self.assertEqual(calls[-1], ['compose', 'start', 'platform', 'queue', 'scheduler'])
        self.assertEqual(backups, ['-- database backup\n'])

    def test_backup_failure_prevents_reset_and_restores_services(self):
        result, calls, _ = self.run_wipe(failure='backup')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any('psql' in call for call in calls))
        self.assertEqual(calls[-1], ['compose', 'start', 'platform', 'queue', 'scheduler'])

    def test_reset_failure_still_restores_services_and_keeps_backup(self):
        result, calls, backups = self.run_wipe(failure='reset')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls[-1], ['compose', 'start', 'platform', 'queue', 'scheduler'])
        self.assertEqual(backups, ['-- database backup\n'])

    def test_previously_stopped_services_are_not_started(self):
        result, calls, _ = self.run_wipe(services='db\nredis\nplatform\nweb\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[1], ['compose', 'stop', 'platform'])
        self.assertEqual(calls[-1], ['compose', 'start', 'platform'])

    def test_stopped_database_prevents_all_mutations(self):
        result, calls, backups = self.run_wipe(services='web\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Kontener db nie działa', result.stderr)
        self.assertEqual(len(calls), 1)
        self.assertEqual(backups, [])

    def test_database_only_does_not_start_application_services(self):
        result, calls, _ = self.run_wipe(services='db\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(call[1] in ('stop', 'start') for call in calls))


if __name__ == '__main__':
    unittest.main()
