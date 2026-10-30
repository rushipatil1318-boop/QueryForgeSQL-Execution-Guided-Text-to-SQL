import unittest
from exercises.lesson01 import bag_equal


class LearnerBagTests(unittest.TestCase):
    def test_order_does_not_matter(self):
        self.assertTrue(bag_equal([(1,), (2,)], [(2,), (1,)]))

    def test_duplicates_do_matter(self):
        self.assertFalse(bag_equal([(1,)], [(1,), (1,)]))

    def test_empty(self):
        self.assertTrue(bag_equal([], []))

    def test_input_is_unchanged(self):
        predicted, reference = [(2,), (1,)], [(1,), (2,)]
        bag_equal(predicted, reference)
        self.assertEqual(predicted, [(2,), (1,)])
        self.assertEqual(reference, [(1,), (2,)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
