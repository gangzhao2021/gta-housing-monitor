import unittest

from housing.teranet import parse

HEADER = ('"Transaction Date",c11,,,,,on_toronto,,,,\n'
          ',Index,"SA Index","Smoothed Index","Smoothed SA Index","Sales Pair Count",'
          'Index,"SA Index","Smoothed Index","Smoothed SA Index","Sales Pair Count"\n')


class TeranetTests(unittest.TestCase):
    def test_toronto_columns_base_period_and_gaps(self):
        body = 'May-2005,,,,,,99.10,99.00,,,500\nJun-2005,,,,,,100.00,100.20,,,510\n'
        rows = parse((HEADER + body).encode())
        self.assertIn(('teranet_toronto_index', '2005-06', 100.0), rows)
        self.assertIn(('teranet_toronto_sales_pairs', '2005-05', 500.0), rows)
        with self.assertRaisesRegex(ValueError, 'gaps'):
            parse((HEADER + 'Apr-2005,,,,,,98.0,98.0,,,400\nJun-2005,,,,,,100.00,100.20,,,510\n').encode())
        with self.assertRaisesRegex(ValueError, '2005-06=100'):
            parse((HEADER + 'Jun-2005,,,,,,101.00,100.20,,,510\n').encode())
