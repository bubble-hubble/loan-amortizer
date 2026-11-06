#!/usr/bin/env python3
"""loan-amortizer: loan / mortgage amortization schedules with extra payments.

Pure Python 3 standard library. Money math uses Decimal and rounds to cents.
"""
from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")


def money(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def fmt(x: Decimal) -> str:
    return f"{x:,.2f}"


@dataclass
class Row:
    month: int
    date: str
    payment: Decimal
    interest: Decimal
    principal: Decimal
    extra: Decimal
    balance: Decimal


@dataclass
class Result:
    monthly_payment: Decimal
    rows: list[Row]

    @property
    def total_interest(self) -> Decimal:
        return sum((r.interest for r in self.rows), Decimal(0))

    @property
    def total_paid(self) -> Decimal:
        return sum((r.payment + r.extra for r in self.rows), Decimal(0))

    @property
    def months(self) -> int:
        return len(self.rows)


def monthly_payment(principal: Decimal, annual_rate_pct: Decimal, months: int) -> Decimal:
    """Standard annuity payment, rounded to cents."""
    if months <= 0:
        raise ValueError("term must be at least 1 month")
    r = annual_rate_pct / Decimal(1200)
    if r == 0:
        return money(principal / months)
    factor = (1 + r) ** months
    return money(principal * r * factor / (factor - 1))


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    # clamp day to month length
    for day in (d.day, 30, 29, 28):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    raise ValueError("bad date")


def schedule(
    principal: Decimal,
    annual_rate_pct: Decimal,
    months: int,
    extra_monthly: Decimal = Decimal(0),
    lump_sums: dict[int, Decimal] | None = None,
    start: date | None = None,
) -> Result:
    if principal <= 0:
        raise ValueError("principal must be positive")
    if annual_rate_pct < 0:
        raise ValueError("rate cannot be negative")
    lump_sums = lump_sums or {}
    pmt = monthly_payment(principal, annual_rate_pct, months)
    r = annual_rate_pct / Decimal(1200)
    balance = money(principal)
    rows: list[Row] = []
    month = 0
    # hard stop guards against pathological input
    while balance > 0 and month < months + 1200:
        month += 1
        interest = money(balance * r)
        scheduled_principal = pmt - interest
        if scheduled_principal <= 0 and extra_monthly <= 0 and not lump_sums:
            raise ValueError("payment does not cover interest; loan never pays off")
        payment = pmt
        if scheduled_principal >= balance or month >= months and extra_monthly == 0 and not lump_sums:
            # final payment: pay off whatever is left (absorbs rounding drift)
            scheduled_principal = balance
            payment = balance + interest
        extra = extra_monthly + lump_sums.get(month, Decimal(0))
        extra = min(extra, balance - scheduled_principal)
        balance = balance - scheduled_principal - extra
        when = add_months(start, month - 1).isoformat() if start else ""
        rows.append(Row(month, when, payment, interest, scheduled_principal, extra, balance))
    return Result(pmt, rows)


def years_months(n: int) -> str:
    y, m = divmod(n, 12)
    parts = []
    if y:
        parts.append(f"{y} yr")
    if m:
        parts.append(f"{m} mo")
    return " ".join(parts) or "0 mo"


def parse_decimal(s: str) -> Decimal:
    try:
        return Decimal(s.replace(",", "").replace("_", ""))
    except InvalidOperation:
        raise argparse.ArgumentTypeError(f"not a number: {s!r}")


def parse_lump(s: str) -> tuple[int, Decimal]:
    try:
        m, amt = s.split(":", 1)
        return int(m), parse_decimal(amt)
    except ValueError:
        raise argparse.ArgumentTypeError(f"lump sum must look like MONTH:AMOUNT, got {s!r}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="amortize",
        description="Loan / mortgage amortization schedule with extra-payment savings.",
    )
    p.add_argument("principal", type=parse_decimal, help="amount borrowed, e.g. 350000")
    p.add_argument("rate", type=parse_decimal, help="annual interest rate in percent, e.g. 6.25")
    term = p.add_mutually_exclusive_group(required=True)
    term.add_argument("-y", "--years", type=int, help="term in years")
    term.add_argument("-m", "--months", type=int, help="term in months")
    p.add_argument("-x", "--extra", type=parse_decimal, default=Decimal(0),
                   help="extra principal paid every month")
    p.add_argument("-l", "--lump", type=parse_lump, action="append", default=[],
                   metavar="MONTH:AMOUNT", help="one-off extra payment in a given month (repeatable)")
    p.add_argument("-s", "--start", type=date.fromisoformat, help="first payment date, YYYY-MM-DD")
    p.add_argument("--table", action="store_true", help="print the full month-by-month table")
    p.add_argument("--yearly", action="store_true", help="print a year-by-year summary table")
    p.add_argument("--csv", metavar="FILE", help="write the full schedule to a CSV file ('-' = stdout)")
    a = p.parse_args(argv)

    months = a.months if a.months else a.years * 12
    lumps: dict[int, Decimal] = {}
    for m, amt in a.lump:
        lumps[m] = lumps.get(m, Decimal(0)) + amt

    try:
        base = schedule(a.principal, a.rate, months, start=a.start)
        res = schedule(a.principal, a.rate, months, a.extra, lumps, a.start)
    except ValueError as e:
        p.error(str(e))

    out = sys.stdout
    if a.csv:
        fh = sys.stdout if a.csv == "-" else open(a.csv, "w", newline="")
        w = csv.writer(fh)
        w.writerow(["month", "date", "payment", "interest", "principal", "extra", "balance"])
        for r in res.rows:
            w.writerow([r.month, r.date, r.payment, r.interest, r.principal, r.extra, r.balance])
        if fh is not sys.stdout:
            fh.close()
            print(f"wrote {len(res.rows)} rows to {a.csv}", file=sys.stderr)
        else:
            return 0

    print(f"Loan amount       {fmt(money(a.principal)):>16}", file=out)
    print(f"Interest rate     {a.rate:>15}%", file=out)
    print(f"Term              {years_months(months):>16}", file=out)
    print(f"Monthly payment   {fmt(res.monthly_payment):>16}", file=out)
    print(f"Total interest    {fmt(res.total_interest):>16}", file=out)
    print(f"Total paid        {fmt(res.total_paid):>16}", file=out)
    if res.rows and res.rows[-1].date:
        print(f"Paid off on       {res.rows[-1].date:>16}", file=out)
    if a.extra or lumps:
        saved = base.total_interest - res.total_interest
        print(file=out)
        print("With extra payments:", file=out)
        print(f"  Paid off in     {years_months(res.months):>16}  (instead of {years_months(base.months)})", file=out)
        print(f"  Interest saved  {fmt(saved):>16}", file=out)
        print(f"  Time saved      {years_months(base.months - res.months):>16}", file=out)

    if a.yearly:
        print(file=out)
        print(f"{'Year':>4} {'Paid':>14} {'Interest':>14} {'Principal':>14} {'Balance':>16}", file=out)
        for y in range(0, res.months, 12):
            chunk = res.rows[y:y + 12]
            paid = sum((r.payment + r.extra for r in chunk), Decimal(0))
            intr = sum((r.interest for r in chunk), Decimal(0))
            prin = sum((r.principal + r.extra for r in chunk), Decimal(0))
            print(f"{y // 12 + 1:>4} {fmt(paid):>14} {fmt(intr):>14} {fmt(prin):>14} {fmt(chunk[-1].balance):>16}",
                  file=out)

    if a.table:
        print(file=out)
        print(f"{'#':>4} {'Date':>10} {'Payment':>12} {'Interest':>12} {'Principal':>12} {'Extra':>10} {'Balance':>14}",
              file=out)
        for r in res.rows:
            print(f"{r.month:>4} {r.date:>10} {fmt(r.payment):>12} {fmt(r.interest):>12} "
                  f"{fmt(r.principal):>12} {fmt(r.extra):>10} {fmt(r.balance):>14}", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
