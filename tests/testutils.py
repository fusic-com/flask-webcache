from datetime import timedelta

def compare_datetimes(this, other, max_seconds_difference=1):
    if this == other:
        return True
    delta = timedelta(seconds=max_seconds_difference)
    return this + delta > other and this - delta < other

def compare_numbers(this, other, max_difference):
    if this == other:
        return True
    return abs(this - other) < max_difference
