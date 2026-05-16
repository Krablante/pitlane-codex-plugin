#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
HOOK = PLUGIN_ROOT / "hooks" / "pitlane-codex-hook"
BYPASS_ENV = [
    "PITLANE_CODEX_HOOK_DISABLE",
    "PITLANE_CODEX_BYPASS",
    "PITLANE_DISABLE",
    "PITLANE_DISABLED",
]


def payload(
    command: str,
    cwd: Path,
    *,
    input_key: str = "command",
    tool_name: str = "Bash",
) -> str:
    return json.dumps(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "cwd": str(cwd),
            "tool_input": {input_key: command},
        }
    )


class PitlaneCodexHookTest(unittest.TestCase):
    def run_hook(
        self,
        command: str,
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        process_env = {
            **os.environ,
            "PITLANE_CODEX_COMMAND": "pitlane",
            "PITLANE_CODEX_ASSUME_INDEXED": "1",
            "PITLANE_CODEX_TELEMETRY": "0",
        }
        for name in BYPASS_ENV:
            process_env.pop(name, None)
        if env:
            process_env.update(env)

        return subprocess.run(
            [str(HOOK)],
            input=payload(command, cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            env=process_env,
            timeout=5,
        )

    def assert_no_output(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def rewritten_command(self, result: subprocess.CompletedProcess[str]) -> str:
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)["hookSpecificOutput"]["updatedInput"]["command"]

    def hook_output(self, result: subprocess.CompletedProcess[str]) -> dict:
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)["hookSpecificOutput"]

    def test_rewrites_cat_source_file_to_pitlane_lines(self) -> None:
        with project_dir() as root:
            source = root / "src" / "app.py"
            source.parent.mkdir()
            source.write_text("print('one')\nprint('two')\n", encoding="utf8")

            result = self.run_hook("cat src/app.py", cwd=root)

        self.assertEqual(
            self.rewritten_command(result),
            "pitlane lines PROJECT src/app.py 1 2".replace("PROJECT", str(root)),
        )
        self.assertIn("additionalContext", json.loads(result.stdout)["hookSpecificOutput"])

    def test_counts_source_file_without_final_newline(self) -> None:
        with project_dir() as root:
            source = root / "src" / "app.py"
            source.parent.mkdir()
            source.write_text("print('one')\nprint('two')", encoding="utf8")

            result = self.run_hook("cat src/app.py", cwd=root)

        self.assertEqual(
            self.rewritten_command(result),
            "pitlane lines PROJECT src/app.py 1 2".replace("PROJECT", str(root)),
        )

    def test_rewrites_sed_and_head_source_ranges(self) -> None:
        with project_dir() as root:
            source = root / "src" / "lib.rs"
            source.parent.mkdir()
            source.write_text("\n".join(f"line {index}" for index in range(1, 80)), encoding="utf8")

            cases = {
                "sed -n '10,30p' src/lib.rs": f"pitlane lines {root} src/lib.rs 10 30",
                "head -n 5 src/lib.rs": f"pitlane lines {root} src/lib.rs 1 5",
            }
            for command, expected in cases.items():
                with self.subTest(command=command):
                    result = self.run_hook(command, cwd=root)
                    self.assertEqual(self.rewritten_command(result), expected)

    def test_adapts_exec_command_cmd_shape_and_safe_shell_unwrap(self) -> None:
        with project_dir() as root:
            source = root / "src" / "app.py"
            source.parent.mkdir()
            source.write_text("print('one')\nprint('two')\n", encoding="utf8")
            process_env = {
                **os.environ,
                "PITLANE_CODEX_COMMAND": "pitlane",
                "PITLANE_CODEX_ASSUME_INDEXED": "1",
            }

            result = subprocess.run(
                [str(HOOK)],
                input=payload(
                    "bash -lc 'cat src/app.py'",
                    root,
                    input_key="cmd",
                    tool_name="exec_command",
                ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                env=process_env,
                timeout=5,
            )

        output = self.hook_output(result)
        self.assertEqual(set(output["updatedInput"]), {"cmd"})
        self.assertEqual(
            output["updatedInput"]["cmd"],
            "pitlane lines PROJECT src/app.py 1 2".replace("PROJECT", str(root)),
        )

    def test_rewrites_extensionless_executable_shebang_source(self) -> None:
        with project_dir() as root:
            source = root / "hooks" / "pitlane-codex-hook"
            source.parent.mkdir()
            source.write_text("#!/usr/bin/env python3\nprint('ok')\n", encoding="utf8")
            source.chmod(source.stat().st_mode | stat.S_IXUSR)

            result = self.run_hook("cat hooks/pitlane-codex-hook", cwd=root)

        self.assertEqual(
            self.rewritten_command(result),
            f"pitlane lines {root} hooks/pitlane-codex-hook 1 2",
        )

    def test_passes_through_extensionless_non_shebang_file(self) -> None:
        with project_dir() as root:
            source = root / "hooks" / "notes"
            source.parent.mkdir()
            source.write_text("plain text\n", encoding="utf8")
            source.chmod(source.stat().st_mode | stat.S_IXUSR)

            result = self.run_hook("cat hooks/notes", cwd=root)

        self.assert_no_output(result)

    def test_caps_broad_cat_reads(self) -> None:
        with project_dir() as root:
            source = root / "src" / "big.ts"
            source.parent.mkdir()
            source.write_text("\n".join(f"line {index}" for index in range(1, 400)), encoding="utf8")

            result = self.run_hook("cat src/big.ts", cwd=root)

        self.assertEqual(self.rewritten_command(result), f"pitlane lines {root} src/big.ts 1 220")

    def test_passes_through_exact_output_and_non_source_commands(self) -> None:
        with project_dir() as root:
            (root / "README.md").write_text("# readme\n", encoding="utf8")
            (root / "data.json").write_text('{"ok": true}\n', encoding="utf8")
            for command in [
                "cat README.md",
                "cat data.json",
                "rg --files",
                "rg --json needle",
                "rg -l needle .",
                "rg TODO src",
                "rg FIXME src",
                "rg class src",
                "rg return src",
                "rg import src",
                "rg parse_rg_symbol_search hooks",
                "rg CommandRunner dist",
                "rg CommandRunner generated",
                "rg foo.bar src",
                "rg foo-bar src",
                "grep -c needle src/app.py",
                "grep -R TODO src",
                "grep -R FIXME src",
                "grep -R class src",
                "grep -R import src",
                "grep -R parse_rg_symbol_search hooks",
                "grep -R CommandRunner data",
                "grep -R CommandRunner generated",
                "grep -R foo.bar src",
                "grep -R foo-bar src",
                "git status --short",
                "make test",
                "pytest -q",
                "docker ps",
                "ssh example-host hostname",
            ]:
                with self.subTest(command=command):
                    result = self.run_hook(command, cwd=root)
                    self.assert_no_output(result)

    def test_shell_control_source_navigation_stays_quiet(self) -> None:
        with project_dir() as root:
            source = root / "src" / "app.py"
            source.parent.mkdir()
            source.write_text("print('x')\n", encoding="utf8")

            result = self.run_hook("cat src/app.py | head -n 20", cwd=root)

        self.assert_no_output(result)

    def test_shell_control_literal_search_does_not_emit_source_navigation_hint(self) -> None:
        with project_dir() as root:
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('x')\n", encoding="utf8")

            for command in [
                "rg TODO src | head -20",
                "grep -R TODO src | wc -l",
                "rg CommandRunner src | head -20",
                "cat /tmp/runtime-state/session.py | head -20",
                "cat src/app.py > /tmp/pitlane-out.txt",
            ]:
                with self.subTest(command=command):
                    result = self.run_hook(command, cwd=root)
                    self.assert_no_output(result)

    def test_rewrites_symbol_search_and_recursive_listing_when_indexed(self) -> None:
        with project_dir() as root:
            (root / "src").mkdir()
            cases = {
                "rg CommandRunner src": f"pitlane search {root} CommandRunner --limit 30 --mode fuzzy --file src",
                "grep -R CommandRunner src": f"pitlane search {root} CommandRunner --limit 30 --mode fuzzy --file src",
                "ls -R src": f"pitlane outline {root} --depth 2 --summary --path src",
                "tree src": f"pitlane outline {root} --depth 2 --summary --path src",
            }
            for command, expected in cases.items():
                with self.subTest(command=command):
                    result = self.run_hook(command, cwd=root)
                    self.assertEqual(self.rewritten_command(result), expected)

    def test_symbol_search_is_not_rewritten_without_index(self) -> None:
        with project_dir() as root, tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "pitlane"
            fake.write_text("#!/usr/bin/env sh\nexit 1\n", encoding="utf8")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

            result = self.run_hook(
                "rg CommandRunner src",
                cwd=root,
                env={
                    "PITLANE_CODEX_COMMAND": str(fake),
                    "PITLANE_CODEX_ASSUME_INDEXED": "0",
                },
            )

        output = self.hook_output(result)
        self.assertNotIn("updatedInput", output)
        self.assertIn("missed source-navigation opportunity", output["additionalContext"])

    def test_missed_opportunity_telemetry_uses_hash_not_command_by_default(self) -> None:
        with project_dir() as root, tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "pitlane"
            fake.write_text("#!/usr/bin/env sh\nexit 1\n", encoding="utf8")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            telemetry = Path(tmp) / "telemetry.jsonl"

            result = self.run_hook(
                "rg SecretToken src",
                cwd=root,
                env={
                    "PITLANE_CODEX_COMMAND": str(fake),
                    "PITLANE_CODEX_ASSUME_INDEXED": "0",
                    "PITLANE_CODEX_TELEMETRY": "1",
                    "PITLANE_CODEX_TELEMETRY_PATH": str(telemetry),
                },
            )
            records = [json.loads(line) for line in telemetry.read_text(encoding="utf8").splitlines()]

        self.assertEqual(result.returncode, 0)
        self.assertTrue(any(record["event"] == "missed_opportunity" for record in records))
        self.assertTrue(all(record.get("command_preview") is None for record in records))
        self.assertTrue(any(record.get("command_hash") for record in records))

    def test_missed_opportunity_telemetry_is_opt_in(self) -> None:
        with project_dir() as root, tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "pitlane"
            fake.write_text("#!/usr/bin/env sh\nexit 1\n", encoding="utf8")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            telemetry = Path(tmp) / "telemetry.jsonl"

            result = self.run_hook(
                "rg SecretToken src",
                cwd=root,
                env={
                    "PITLANE_CODEX_COMMAND": str(fake),
                    "PITLANE_CODEX_ASSUME_INDEXED": "0",
                    "PITLANE_CODEX_TELEMETRY": "",
                    "PITLANE_CODEX_TELEMETRY_PATH": str(telemetry),
                },
            )

        self.assertEqual(result.returncode, 0)
        self.assertFalse(telemetry.exists())

    def test_decision_telemetry_is_compact_and_opt_in(self) -> None:
        with project_dir() as root, tempfile.TemporaryDirectory() as tmp:
            (root / "src").mkdir()
            telemetry = Path(tmp) / "telemetry.jsonl"
            env = {
                "PITLANE_CODEX_TELEMETRY": "1",
                "PITLANE_CODEX_TELEMETRY_DECISIONS": "1",
                "PITLANE_CODEX_TELEMETRY_PATH": str(telemetry),
            }

            literal = self.run_hook("rg TODO src", cwd=root, env=env)
            rewrite = self.run_hook("rg CommandRunner src", cwd=root, env=env)
            records = [json.loads(line) for line in telemetry.read_text(encoding="utf8").splitlines()]

        self.assert_no_output(literal)
        self.assertIn("updatedInput", self.hook_output(rewrite))
        decisions = [record for record in records if record["event"] == "decision"]
        self.assertTrue(any(
            record.get("decision") == "pass" and record.get("command_class") == "literal-search"
            for record in decisions
        ))
        self.assertTrue(any(
            record.get("decision") == "rewrite" and record.get("command_class") == "symbol-search"
            for record in decisions
        ))
        self.assertTrue(all(record.get("command_preview") is None for record in decisions))

    def test_missed_opportunity_telemetry_covers_find_and_git_grep(self) -> None:
        with project_dir() as root, tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "pitlane"
            fake.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf8")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            telemetry = Path(tmp) / "telemetry.jsonl"

            for command in ["find . -name '*.py'", "git grep CommandRunner"]:
                result = self.run_hook(
                    command,
                    cwd=root,
                    env={
                        "PITLANE_CODEX_COMMAND": str(fake),
                        "PITLANE_CODEX_ASSUME_INDEXED": "1",
                        "PITLANE_CODEX_TELEMETRY": "1",
                        "PITLANE_CODEX_TELEMETRY_PATH": str(telemetry),
                    },
                )
                output = self.hook_output(result)
                self.assertNotIn("updatedInput", output)
                self.assertIn("missed source-navigation opportunity", output["additionalContext"])

            records = [json.loads(line) for line in telemetry.read_text(encoding="utf8").splitlines()]

        self.assertEqual(len(records), 2)
        self.assertTrue(all(record["event"] == "missed_opportunity" for record in records))
        self.assertTrue(all(record.get("command_hash") for record in records))

    def test_excluded_scopes_are_not_counted_as_missed_navigation(self) -> None:
        with project_dir() as root, tempfile.TemporaryDirectory() as tmp:
            (root / "generated").mkdir()
            (root / "generated" / "Thing.py").write_text("class CommandRunner: pass\n", encoding="utf8")
            (root / "log").mkdir()
            (root / "log" / "event.py").write_text("class CommandRunner: pass\n", encoding="utf8")
            runtime_state = root / "runtime-state"
            runtime_state.mkdir()
            (runtime_state / "session.py").write_text("class CommandRunner: pass\n", encoding="utf8")
            nested = root / "nested"
            nested.mkdir()
            telemetry = Path(tmp) / "telemetry.jsonl"
            env = {
                "PITLANE_CODEX_TELEMETRY": "1",
                "PITLANE_CODEX_TELEMETRY_PATH": str(telemetry),
            }
            for command in [
                "find /tmp/runtime-state -name '*.py'",
                "ls -R dist",
                "ls -R generated",
                "find generated -name '*.py'",
                "cat generated/Thing.py",
                "cat /tmp/runtime-state/session.py",
                "cat runtime-state/session.py",
                "cat log/event.py",
                "find log -name '*.py'",
            ]:
                with self.subTest(command=command):
                    result = self.run_hook(command, cwd=root, env=env)
                    self.assert_no_output(result)

            result = self.run_hook("cat ../runtime-state/session.py", cwd=nested, env=env)
            self.assert_no_output(result)

        self.assertFalse(telemetry.exists())

    def test_excluded_scope_cwd_is_not_source_navigation(self) -> None:
        for scope in ["runtime-state", "log", "generated", "data", "archive", "state"]:
            with self.subTest(scope=scope), project_dir() as root, tempfile.TemporaryDirectory() as tmp:
                scope_dir = root / scope
                scope_dir.mkdir()
                (scope_dir / "session.py").write_text("class CommandRunner: pass\n", encoding="utf8")
                telemetry = Path(tmp) / "telemetry.jsonl"
                env = {
                    "PITLANE_CODEX_TELEMETRY": "1",
                    "PITLANE_CODEX_TELEMETRY_PATH": str(telemetry),
                }
                for command in [
                    "cat session.py",
                    "find . -name '*.py'",
                    "rg CommandRunner .",
                    "grep -R CommandRunner .",
                    "git grep CommandRunner",
                ]:
                    result = self.run_hook(command, cwd=scope_dir, env=env)
                    self.assert_no_output(result)
                self.assertFalse(telemetry.exists())

    def test_missing_pitlane_cli_does_not_fallback_to_docker_mcp(self) -> None:
        with project_dir() as root, tempfile.TemporaryDirectory() as tmp:
            source = root / "src" / "app.py"
            source.parent.mkdir()
            source.write_text("print('x')\n", encoding="utf8")
            fake_docker = Path(tmp) / "docker"
            fake_docker.write_text("#!/usr/bin/env sh\nprintf 'true\\n'\n", encoding="utf8")
            fake_docker.chmod(fake_docker.stat().st_mode | stat.S_IXUSR)

            result = self.run_hook(
                "cat src/app.py",
                cwd=root,
                env={
                    "PATH": f"{tmp}:/usr/bin:/bin",
                    "PITLANE_CODEX_COMMAND": "",
                },
            )

        self.assert_no_output(result)

    def test_rejects_docker_pitlane_command_override(self) -> None:
        with project_dir() as root:
            source = root / "src" / "app.py"
            source.parent.mkdir()
            source.write_text("print('x')\n", encoding="utf8")

            result = self.run_hook(
                "cat src/app.py",
                cwd=root,
                env={"PITLANE_CODEX_COMMAND": "docker exec pitlane-cli pitlane"},
            )

        self.assert_no_output(result)

    def test_bypass_envs_disable_hook(self) -> None:
        with project_dir() as root:
            source = root / "src" / "app.py"
            source.parent.mkdir()
            source.write_text("print('x')\n", encoding="utf8")
            for name in BYPASS_ENV:
                with self.subTest(env=name):
                    result = self.run_hook("cat src/app.py", cwd=root, env={name: "1"})
                    self.assert_no_output(result)

    def test_command_prefix_bypass_disables_hook(self) -> None:
        with project_dir() as root:
            source = root / "src" / "app.py"
            source.parent.mkdir()
            source.write_text("print('x')\n", encoding="utf8")

            for command in [
                "PITLANE_DISABLE=1 cat src/app.py",
                "env PITLANE_CODEX_BYPASS=1 cat src/app.py",
            ]:
                with self.subTest(command=command):
                    result = self.run_hook(command, cwd=root)
                    self.assert_no_output(result)


class project_dir:
    def __enter__(self) -> Path:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(
            ["git", "init", "-q", "-b", "main"],
            cwd=self.root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return self.root

    def __exit__(self, exc_type, exc, tb) -> None:
        self.tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
