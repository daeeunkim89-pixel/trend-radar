import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import run_discovery as d


class DiscoveryEnvironmentTests(unittest.TestCase):
    def test_missing_dependencies_are_installed_and_rechecked_before_collection(self):
        root = Path.cwd() / "work/test-collector-environment"
        python = root / "work/collector-runtime" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        events = []
        def probe(value):
            events.append(("probe", str(value)))
            return len([e for e in events if e[0] == "probe"]) == 3
        def process(args, **kwargs):
            events.append(("install" if "pip" in args else "collect", args))
            return Mock(returncode=0)
        with patch.object(d.Path, "exists", return_value=True), \
                patch.object(d, "ready", side_effect=probe), \
                patch.object(d.subprocess, "run", side_effect=process):
            self.assertEqual(d.run(480, root), 0)
        self.assertEqual([e[0] for e in events], ["probe", "probe", "install", "probe", "collect"])
        self.assertEqual(events[-2][1], str(python))
        self.assertEqual(events[-1][1][0], str(python))

    def test_environment_failure_never_becomes_a_successful_empty_collection(self):
        with patch.object(d, "runtime", side_effect=RuntimeError("missing dependencies")), \
                patch.object(d.subprocess, "run") as child:
            self.assertEqual(d.run(), 2)
            child.assert_not_called()

    def test_ready_runtime_needs_no_install_and_child_has_no_telegram_credentials(self):
        with patch.object(d, "ready", return_value=True), \
                patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "synthetic", "TELEGRAM_CHAT_ID": "synthetic"}), \
                patch.object(d.subprocess, "run", return_value=Mock(returncode=0)) as child:
            self.assertEqual(d.run(), 0)
            self.assertEqual(child.call_count, 1)
            self.assertNotIn("TELEGRAM_BOT_TOKEN", child.call_args.kwargs["env"])
            self.assertNotIn("TELEGRAM_CHAT_ID", child.call_args.kwargs["env"])
