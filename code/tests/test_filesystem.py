"""Tests du mini systeme de fichiers bonus d'ESINOS."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import threading
import unittest
from pathlib import Path


CODE_ROOT = Path(__file__).resolve().parents[1]
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from esinos.cli import main  # noqa: E402
from esinos.filesystem import (  # noqa: E402
    DiskAlreadyExistsError,
    DiskFullError,
    InvalidFileNameError,
    VirtualFileNotFoundError,
    VirtualFileSystem,
)


class VirtualFileSystemTests(unittest.TestCase):
    """Les images temporaires isolent chaque scenario d'allocation."""

    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.disk_path = Path(self._temporary_directory.name) / "esinos.disk.json"

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def test_create_read_and_persist_after_reopening(self) -> None:
        filesystem = VirtualFileSystem(
            self.disk_path, block_count=8, block_size=4, inode_count=4, create=True
        )
        inode = filesystem.create_file("notes.txt", "Bonjour é")

        self.assertEqual(inode.inode_id, 1)
        self.assertEqual(filesystem.read_file("notes.txt"), "Bonjour é")
        self.assertGreaterEqual(len(inode.blocks), 2)
        self.assertTrue(self.disk_path.exists())

        reopened = VirtualFileSystem(self.disk_path)
        self.assertEqual(reopened.read_file("notes.txt"), "Bonjour é")
        self.assertEqual(reopened.list_files()[0], inode)

    def test_delete_releases_blocks_for_a_new_file(self) -> None:
        filesystem = VirtualFileSystem(
            self.disk_path, block_count=2, block_size=4, inode_count=3, create=True
        )
        first = filesystem.create_file("a.txt", "ABCD")
        filesystem.create_file("b.txt", "EFGH")
        self.assertEqual(filesystem.status()["free_blocks"], 0)

        filesystem.delete_file("a.txt")
        self.assertEqual(filesystem.status()["free_blocks"], 1)
        replacement = filesystem.create_file("c.txt", "IJKL")

        self.assertEqual(first.blocks, (0,))
        self.assertEqual(replacement.blocks, (0,))
        self.assertEqual(filesystem.read_file("b.txt"), "EFGH")
        self.assertEqual(filesystem.read_file("c.txt"), "IJKL")
        self.assertTrue(filesystem.inode_table()[0]["allocated"])
        with self.assertRaises(VirtualFileNotFoundError):
            filesystem.read_file("a.txt")

    def test_disk_full_and_invalid_name_are_reported(self) -> None:
        filesystem = VirtualFileSystem(
            self.disk_path, block_count=1, block_size=4, inode_count=2, create=True
        )
        filesystem.create_file("plein.txt", "ABCD")

        with self.assertRaises(DiskFullError):
            filesystem.create_file("autre.txt", "E")
        with self.assertRaises(InvalidFileNameError):
            filesystem.create_file("nom avec espace.txt", "E")
        with self.assertRaises(InvalidFileNameError):
            filesystem.create_file("../sortie.txt", "E")

    def test_cli_init_uses_requested_geometry_and_never_overwrites(self) -> None:
        arguments = [
            "fs",
            "--disk",
            str(self.disk_path),
            "--blocks",
            "3",
            "--block-size",
            "7",
            "--inodes",
            "2",
            "init",
        ]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(arguments), 0)

        filesystem = VirtualFileSystem(self.disk_path)
        self.assertEqual(
            filesystem.status(),
            {
                "disk_path": str(self.disk_path),
                "block_size": 7,
                "block_count": 3,
                "used_blocks": 0,
                "free_blocks": 3,
                "max_inodes": 2,
                "used_inodes": 0,
                "free_inodes": 2,
            },
        )
        filesystem.create_file("garde.txt", "a conserver")
        before = self.disk_path.read_bytes()

        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            self.assertEqual(main(arguments), 2)
        self.assertIn("Refus d'ecraser", stderr.getvalue())
        self.assertEqual(self.disk_path.read_bytes(), before)
        self.assertEqual(VirtualFileSystem(self.disk_path).read_file("garde.txt"), "a conserver")

    def test_initialize_new_refuses_an_invalid_existing_image_without_writing(self) -> None:
        corrupt_bytes = b"ceci n'est pas une image disque ESINOS\n"
        self.disk_path.write_bytes(corrupt_bytes)

        with self.assertRaises(DiskAlreadyExistsError):
            VirtualFileSystem.initialize_new(
                self.disk_path, block_count=9, block_size=9, inode_count=9
            )
        self.assertEqual(self.disk_path.read_bytes(), corrupt_bytes)

    def test_simultaneous_exclusive_initializations_have_one_winner(self) -> None:
        barrier = threading.Barrier(2)
        outcomes = []
        lock = threading.Lock()

        def initialize() -> None:
            barrier.wait()
            try:
                VirtualFileSystem.initialize_new(
                    self.disk_path, block_count=5, block_size=8, inode_count=3
                )
            except DiskAlreadyExistsError:
                outcome = "exists"
            except Exception as error:  # pragma: no cover - useful failure detail
                outcome = error
            else:
                outcome = "created"
            with lock:
                outcomes.append(outcome)

        threads = [threading.Thread(target=initialize), threading.Thread(target=initialize)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertCountEqual(outcomes, ["created", "exists"])
        filesystem = VirtualFileSystem(self.disk_path)
        self.assertEqual(
            (filesystem.block_count, filesystem.block_size, filesystem.max_inodes),
            (5, 8, 3),
        )
        self.assertEqual(list(self.disk_path.parent.glob(".esinos.disk.json.*.tmp")), [])

    def test_create_true_still_opens_an_existing_image_without_reformatting(self) -> None:
        initial = VirtualFileSystem.initialize_new(
            self.disk_path, block_count=4, block_size=5, inode_count=2
        )
        initial.create_file("stable.txt", "contenu")

        reopened = VirtualFileSystem(
            self.disk_path, block_count=99, block_size=99, inode_count=99, create=True
        )
        self.assertEqual(reopened.read_file("stable.txt"), "contenu")
        self.assertEqual(
            (reopened.block_count, reopened.block_size, reopened.max_inodes), (4, 5, 2)
        )


if __name__ == "__main__":
    unittest.main()
