import unittest

from nextgen_test_automation.core.models import StepAction, TestCase, TestStep, TestSuite
from nextgen_test_automation.core.test_case_manager import InMemoryTestCaseManager


class ManagerTests(unittest.TestCase):
    def test_suite_and_test_case_crud(self):
        manager = InMemoryTestCaseManager()
        suite = manager.create_suite(TestSuite(name="Core Suite"))

        test_case = TestCase(
            name="Login works",
            industry="BFSI",
            steps=[TestStep(action=StepAction.NAVIGATE, description="Navigate to login")],
        )
        manager.add_test_case(suite.id, test_case)

        fetched = manager.get_suite(suite.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(len(fetched.test_cases), 1)

        manager.update_test_case(suite.id, test_case.id, {"name": "Login flow works"})
        fetched = manager.get_suite(suite.id)
        self.assertEqual(fetched.test_cases[0].name, "Login flow works")

        manager.delete_test_case(suite.id, test_case.id)
        fetched = manager.get_suite(suite.id)
        self.assertEqual(len(fetched.test_cases), 0)


if __name__ == "__main__":
    unittest.main()
