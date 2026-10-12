from pathlib import Path
import tempfile
import unittest

import pandas as pd

from data_loader import load_csv, schema_context
from database import create_dataset_database, execute_read_only_query, validate_query_against_database
from query_validator import validate_sql
from visualization import suggest_chart


ROOT = Path(__file__).parents[1]

class GenericSystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "dataset.db"

    def tearDown(self): self.temp.cleanup()

    def prepare(self, source, name):
        info = load_csv(source, name)
        create_dataset_database(info.frame, self.db_path)
        return info

    def test_sales_csv_loads_and_is_queryable(self):
        info = self.prepare(ROOT / "sales_data.csv", "sales_data.csv")
        self.assertEqual(len(info.frame), 1000)
        self.assertEqual(len(info.frame.columns), 14)
        checks = [
            'SELECT SUM("Sales_Amount") AS total FROM dataset;',
            'SELECT "Region", SUM("Sales_Amount") AS total FROM dataset GROUP BY "Region" ORDER BY total DESC LIMIT 1;',
            'SELECT AVG("Quantity_Sold") AS average_quantity FROM dataset;',
        ]
        for sql in checks:
            self.assertTrue(validate_sql(sql)[0])
            self.assertTrue(validate_query_against_database(self.db_path, sql)[0])
            self.assertFalse(execute_read_only_query(self.db_path, sql).empty)

    def test_second_dataset_has_no_sales_assumptions(self):
        frame = pd.DataFrame({"Employee_ID": [1, 2, 3], "Department": ["Engineering", "Engineering", "Design"], "Salary": [100, 120, 90], "Age": [29, 34, 26]})
        path = Path(self.temp.name) / "employees.csv"; frame.to_csv(path, index=False)
        info = self.prepare(path, "employees.csv")
        sql = 'SELECT "Department", AVG("Salary") AS average_salary FROM dataset GROUP BY "Department";'
        self.assertTrue(validate_sql(sql)[0])
        result = execute_read_only_query(self.db_path, sql)
        self.assertEqual(set(result["Department"]), {"Engineering", "Design"})
        self.assertIn('"Salary"', schema_context(info))
        self.assertEqual(suggest_chart(result), ("bar", "Department", "average_salary"))

    def test_unsafe_and_invalid_sql_are_rejected(self):
        self.prepare(ROOT / "sales_data.csv", "sales_data.csv")
        for sql in ["DELETE FROM dataset", "DROP TABLE dataset", "UPDATE dataset SET x=1", "SELECT * FROM dataset; DELETE FROM dataset"]:
            self.assertFalse(validate_sql(sql)[0])
        self.assertFalse(validate_query_against_database(self.db_path, 'SELECT missing_column FROM dataset')[0])

if __name__ == "__main__": unittest.main()
