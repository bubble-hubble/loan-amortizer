import unittest
from datetime import date
from decimal import Decimal as D

from amortize import add_months, monthly_payment, schedule


class PaymentTests(unittest.TestCase):
    def test_known_mortgage_payment(self):
        # 200,000 at 6% over 30 years -> 1,199.10 (standard published figure)
        self.assertEqual(monthly_payment(D(200000), D(6), 360), D("1199.10"))

    def test_zero_rate(self):
        self.assertEqual(monthly_payment(D(12000), D(0), 12), D("1000.00"))

    def test_schedule_pays_off_exactly(self):
        res = schedule(D(200000), D(6), 360)
        self.assertEqual(res.months, 360)
        self.assertEqual(res.rows[-1].balance, D("0.00"))
        principal_paid = sum(r.principal + r.extra for r in res.rows)
        self.assertEqual(principal_paid, D(200000))

    def test_extra_payments_shorten_and_save(self):
        base = schedule(D(200000), D(6), 360)
        fast = schedule(D(200000), D(6), 360, extra_monthly=D(200))
        self.assertLess(fast.months, base.months)
        self.assertLess(fast.total_interest, base.total_interest)
        self.assertEqual(fast.rows[-1].balance, D("0.00"))

    def test_lump_sum_applied_once(self):
        res = schedule(D(10000), D(5), 24, lump_sums={3: D(1000)})
        self.assertEqual(res.rows[2].extra, D(1000))
        self.assertEqual(res.rows[3].extra, D(0))

    def test_extra_never_overpays(self):
        res = schedule(D(1000), D(5), 12, extra_monthly=D(5000))
        self.assertEqual(res.months, 1)
        self.assertEqual(res.rows[0].balance, D("0.00"))

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            schedule(D(-1), D(5), 12)


class DateTests(unittest.TestCase):
    def test_month_end_clamping(self):
        self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))
        self.assertEqual(add_months(date(2026, 11, 15), 3), date(2027, 2, 15))


if __name__ == "__main__":
    unittest.main()
