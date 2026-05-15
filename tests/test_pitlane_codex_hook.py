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


def payload(command: str, cwd: Path) -> str:
    return json.dumps(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "cwd": str(cwd),
            "tool_input": {"command": command},
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
        fake_bin = cwd / ".test-bin"
        fake_bin.mkdir(exist_ok=True)
        fake_pitlane = fake_bin / "pitlane"
        if not fake_pitlane.exists():
            fake_pitlane.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf8")
            fake_pitlane.chmod(fake_pitlane.stat().st_mode | stat.S_IXUSR)

        process_env = {
            **os.environ,
            "PITLANE_CODEX_COMMAND": "pitlane",
            "PITLANE_CODEX_ASSUME_INDEXED": "1",
            "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
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
                "cat src/app.py | head -n 20",
                "rg --files",
                "rg --json needle",
                "rg -l needle .",
                "rg foo.bar src",
                "rg foo-bar src",
                "grep -c needle src/app.py",
                "grep -R foo.bar src",
                "grep -R foo-bar src",
                "git status --short",
                "make test",
                "pytest -q",
                "docker ps",
                "ssh toma hostname",
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

        self.assert_no_output(result)

    def test_missing_pitlane_cli_does_not_try_container_fallback(self) -> None:
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

    def test_rejects_container_pitlane_command_override(self) -> None:
        with project_dir() as root:
            source = root / "src" / "app.py"
            source.parent.mkdir()
            source.write_text("print('x')\n", encoding="utf8")

            result = self.run_hook(
                "cat src/app.py",
                cwd=root,
                env={"PITLANE_CODEX_COMMAND": " ".join(["docker", "exec", "pitlane-cli", "pitlane"])},
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
