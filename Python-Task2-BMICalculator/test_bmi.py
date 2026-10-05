import unittest
import os
import tempfile
from pathlib import Path
import database
import main


class TestBMICalculatorLogic(unittest.TestCase):

    def test_bmi_calculation(self):
        self.assertEqual(main.calculate_bmi(70, 1.75), 22.86)
        self.assertEqual(main.calculate_bmi(50, 1.60), 19.53)
        self.assertEqual(main.calculate_bmi(95, 1.80), 29.32)

    def test_bmi_categories(self):
        cat, meta = main.get_bmi_category(17.2)
        self.assertEqual(cat, "Underweight")
        self.assertEqual(meta["color"], "#0284C7")

        cat, _ = main.get_bmi_category(18.49)
        self.assertEqual(cat, "Underweight")

        cat, meta = main.get_bmi_category(18.5)
        self.assertEqual(cat, "Normal")
        self.assertEqual(meta["color"], "#16A34A")

        cat, _ = main.get_bmi_category(22.86)
        self.assertEqual(cat, "Normal")

        cat, _ = main.get_bmi_category(24.9)
        self.assertEqual(cat, "Normal")

        cat, meta = main.get_bmi_category(25.0)
        self.assertEqual(cat, "Overweight")
        self.assertEqual(meta["color"], "#D97706")

        cat, _ = main.get_bmi_category(28.4)
        self.assertEqual(cat, "Overweight")

        cat, _ = main.get_bmi_category(29.9)
        self.assertEqual(cat, "Overweight")

        cat, meta = main.get_bmi_category(30.0)
        self.assertEqual(cat, "Obese")
        self.assertEqual(meta["color"], "#DC2626")

        cat, _ = main.get_bmi_category(35.5)
        self.assertEqual(cat, "Obese")


class TestDatabaseOperations(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_bmi.db")
        database.init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_and_retrieve_user_records(self):
        id1 = database.add_record("Alice", 60.0, 1.65, 22.04, "Normal", timestamp="2026-01-01 10:00:00", db_path=self.db_path)
        id2 = database.add_record("Alice", 62.0, 1.65, 22.77, "Normal", timestamp="2026-02-01 10:00:00", db_path=self.db_path)
        self.assertGreater(id1, 0)
        self.assertGreater(id2, id1)

        database.add_record("Bob", 88.0, 1.75, 28.73, "Overweight", timestamp="2026-01-15 11:00:00", db_path=self.db_path)

        alice_records = database.get_user_records("Alice", db_path=self.db_path)
        self.assertEqual(len(alice_records), 2)
        self.assertEqual(alice_records[0]["weight"], 60.0)
        self.assertEqual(alice_records[1]["weight"], 62.0)
        self.assertEqual(alice_records[0]["bmi"], 22.04)

        users = database.get_all_users(db_path=self.db_path)
        self.assertListEqual(sorted(users), ["Alice", "Bob"])

    def test_validation_in_db(self):
        with self.assertRaises(ValueError):
            database.add_record("", 70, 1.75, 22.86, "Normal", db_path=self.db_path)

        with self.assertRaises(ValueError):
            database.add_record("Charlie", -10, 1.75, 22.86, "Normal", db_path=self.db_path)

        with self.assertRaises(ValueError):
            database.add_record("Charlie", 70, 0, 22.86, "Normal", db_path=self.db_path)

    def test_delete_record(self):
        rec_id = database.add_record("David", 75.0, 1.80, 23.15, "Normal", db_path=self.db_path)
        self.assertTrue(database.delete_record(rec_id, db_path=self.db_path))
        david_records = database.get_user_records("David", db_path=self.db_path)
        self.assertEqual(len(david_records), 0)

    def test_user_stats(self):
        database.add_record("Eve", 50.0, 1.60, 19.53, "Normal", timestamp="2026-01-01 09:00:00", db_path=self.db_path)
        database.add_record("Eve", 52.0, 1.60, 20.31, "Normal", timestamp="2026-02-01 09:00:00", db_path=self.db_path)
        database.add_record("Eve", 48.0, 1.60, 18.75, "Normal", timestamp="2026-03-01 09:00:00", db_path=self.db_path)

        stats = database.get_user_stats("Eve", db_path=self.db_path)
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["min_bmi"], 18.75)
        self.assertEqual(stats["max_bmi"], 20.31)
        self.assertEqual(stats["latest_bmi"], 18.75)


if __name__ == "__main__":
    unittest.main()
