from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


MONEY_PLACES = Decimal('0.01')


def to_money(value, default='0.00'):
    if value is None or value == '':
        value = default
    if isinstance(value, Decimal):
        amount = value
    else:
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            amount = Decimal(default)
    return amount.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def format_money(value):
    return '{:.2f}'.format(to_money(value))


def normalize_money_data(value):
    if isinstance(value, Decimal):
        return format_money(value)
    if isinstance(value, dict):
        return {k: normalize_money_data(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_money_data(v) for v in value]
    if isinstance(value, tuple):
        return [normalize_money_data(v) for v in value]
    return value
