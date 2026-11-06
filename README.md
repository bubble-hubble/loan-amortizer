# loan-amortizer

Loan and mortgage amortization schedules from the command line, showing how much
interest and time you save with extra payments.

- Monthly payment, total interest and total cost
- Recurring extra payments (`-x`) and one-off lump sums (`-l`)
- Full month-by-month table, a yearly summary, or CSV export
- Exact money math with `Decimal`, rounded to cents
- Pure Python 3 standard library (tested on 3.14), no install needed

## Usage

```console
$ python3 amortize.py 350000 6.25 -y 30 -x 300
Loan amount             350,000.00
Interest rate                6.25%
Term                         30 yr
Monthly payment           2,155.01
Total interest          291,232.06
Total paid              641,232.06

With extra payments:
  Paid off in          21 yr 10 mo  (instead of 30 yr)
  Interest saved        134,571.66
  Time saved             8 yr 2 mo
```

More examples:

```bash
# 5-year car loan with a full table
python3 amortize.py 28000 7.9 -y 5 --table

# Mortgage starting Jan 2027, $10,000 lump sum in month 12, yearly summary
python3 amortize.py 350000 6.25 -y 30 -l 12:10000 -s 2027-01-01 --yearly

# Export the whole schedule to a spreadsheet
python3 amortize.py 350000 6.25 -y 30 -x 300 --csv schedule.csv
```

| Option | Meaning |
|---|---|
| `principal rate` | amount borrowed and annual interest rate in percent |
| `-y YEARS` / `-m MONTHS` | loan term |
| `-x AMOUNT` | extra principal paid every month |
| `-l MONTH:AMOUNT` | one-off extra payment in a given month (repeatable) |
| `-s YYYY-MM-DD` | first payment date (adds dates to the tables) |
| `--table` / `--yearly` | monthly or yearly table |
| `--csv FILE` | write the full schedule to CSV (`-` for stdout) |

It can also be used as a library:

```python
from decimal import Decimal
from amortize import monthly_payment, schedule

payment = monthly_payment(Decimal("350000"), Decimal("6.25"), 360)
result = schedule(Decimal("350000"), Decimal("6.25"), 360, extra_monthly=Decimal("300"))
print(len(result.rows), "months,", result.total_interest, "interest")
```

## Tests

```bash
python3 -m unittest -v
```

## Notes

Uses the standard fixed-rate formula with monthly compounding. Real loans can
differ slightly because of day-count rules, fees or escrow. This is not
financial advice.

## License

MIT
