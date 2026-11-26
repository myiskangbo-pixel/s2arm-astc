#!/usr/bin/env python3
"""iOS BC → ASTC pack delivery tests: pack manifest is updated before the game pack identity is committed."""
import contextlib
import hashlib
import json
import tempfile
import unittest
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pack/jobs"))

import astc_job
import ipa
import onerom


class FakeContext:
    def __init__(self, root):
        self.engine = ROOT
        self.logs = Path(root) / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.task = "ipa-astc-test"
        self.commands = []
        self.messages = []
        self.stages = []

    def begin(self, name, *args, **kwargs):
        self.stages.append(name)

    def emit(self, **kwargs):
        self.messages.append(kwargs)

    def env(self):
        return {}

    def run(self, args, log, env=None, **kwargs):
        self.commands.append([str(x) for x in args])
        Path(args[-1]).write_bytes(b"ASTC" * 4)


def seed_pack(root):
    pack = Path(root) / "pack"
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "game.img").write_bytes(b"IMG")
    (pack / "index.tsv").write_text("game.img\t3\tabc\n", encoding="utf-8")
    (pack / "manifest.json").write_text(
        json.dumps(dict(version=2, files=1, total=3, index_sha256="old")),
        encoding="utf-8",
    )
    return pack


class BuildPackTests(unittest.TestCase):
    def test_builds_astc_and_updates_resource_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = FakeContext(tmp)
            romfs = Path(tmp) / "romfs"
            romfs.mkdir()
            pack = seed_pack(tmp)

            astc_job.build_for_pack(c, romfs, pack, "iPhone")

            self.assertEqual((pack / "astc.pack").read_bytes(), b"ASTC" * 4)
            index = (pack / "index.tsv").read_text(encoding="utf-8")
            self.assertIn("astc.pack\t16\t" + hashlib.sha256(b"ASTC" * 4).hexdigest(), index)
            manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["files"], 2)
            self.assertEqual(manifest["total"], 19)
            self.assertEqual(manifest["index_sha256"], hashlib.sha256(index.encode()).hexdigest())
            self.assertIn("astc_pack.py", " ".join(c.commands[0]))

    def test_missing_romfs_does_not_add_or_run_astc(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = FakeContext(tmp)
            pack = seed_pack(tmp)

            self.assertIsNone(astc_job.build_for_pack(c, Path(tmp) / "missing-romfs", pack, "iPhone"))

            self.assertEqual(c.commands, [])
            self.assertFalse((pack / "astc.pack").exists())
            self.assertEqual(len(c.messages), 1)


class DeliverIntegrationTests(unittest.TestCase):
    def test_ios_deliver_registers_astc_before_committing_pack_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = FakeContext(tmp)
            root = Path(tmp) / "product"
            root.mkdir()
            romfs = Path(tmp) / "romfs"
            romfs.mkdir()
            pack = seed_pack(tmp)
            ipa_file = Path(tmp) / "game.ipa"
            ipa_file.write_bytes(b"IPA")
            seen = {}

            @contextlib.contextmanager
            def no_locks(*args, **kwargs):
                yield

            def swap(_c, _gid, pack_dir, want):
                index = (Path(pack_dir) / "index.tsv").read_text(encoding="utf-8")
                manifest = json.loads((Path(pack_dir) / "manifest.json").read_text(encoding="utf-8"))
                seen.update(index=index, manifest=manifest, want=want)

            with (
                mock.patch.object(ipa, "program_locks", no_locks),
                mock.patch("library.save_container_kit", return_value=root),
                mock.patch.object(ipa, "to_img"),
                mock.patch.object(ipa, "_swap_pack", side_effect=swap),
                mock.patch.object(onerom, "dedupe", return_value={}),
                mock.patch.object(onerom, "note"),
            ):
                ipa.deliver(c, "0100000000000000", root, pack, ipa_file, astc_romfs=romfs)

            self.assertIn("astc.pack", seen["index"])
            self.assertEqual(seen["want"], seen["manifest"]["index_sha256"])
            self.assertFalse(ipa_file.exists())


if __name__ == "__main__":
    unittest.main()
