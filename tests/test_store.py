import tempfile
import unittest
from pathlib import Path

from app import TaskStore


class TaskStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "tasks.db"
        self.store = TaskStore(self.path)

    def test_starts_empty(self):
        self.assertEqual(self.store.list_tasks(), [])

    def test_create_trims_title_and_starts_pending(self):
        self.assertEqual(self.store.create_task("  Estudar CI  "), {"id": 1, "title": "Estudar CI", "done": False})

    def test_rejects_invalid_titles(self):
        for title in (None, 10, True, "", "   ", "a" * 121, []):
            with self.subTest(title=title), self.assertRaises(ValueError):
                self.store.create_task(title)

    def test_accepts_maximum_title(self):
        self.assertEqual(len(self.store.create_task("a" * 120)["title"]), 120)

    def test_mark_done_and_reopen(self):
        task = self.store.create_task("Testar")
        self.assertTrue(self.store.update_task(task["id"], True)["done"])
        self.assertFalse(self.store.update_task(task["id"], False)["done"])

    def test_rejects_non_boolean_done(self):
        task = self.store.create_task("Testar")
        for done in (1, 0, "true", None, []):
            with self.subTest(done=done), self.assertRaises(ValueError):
                self.store.update_task(task["id"], done)

    def test_delete_removes_only_selected_task(self):
        first = self.store.create_task("Primeira")
        second = self.store.create_task("Segunda")
        self.store.delete_task(first["id"])
        self.assertEqual(self.store.list_tasks(), [second])

    def test_missing_tasks_raise_key_error(self):
        for operation in (lambda: self.store.get_task(999), lambda: self.store.update_task(999, True), lambda: self.store.delete_task(999)):
            with self.subTest(operation=operation), self.assertRaises(KeyError):
                operation()

    def test_data_persists_when_store_reopens(self):
        task = self.store.create_task("Persistir")
        self.assertEqual(TaskStore(self.path).get_task(task["id"]), task)

    def test_sql_text_is_stored_as_data(self):
        title = "'); DROP TABLE tasks; --"
        self.store.create_task(title)
        self.assertEqual(self.store.list_tasks()[0]["title"], title)
        self.assertTrue(self.store.healthy())
