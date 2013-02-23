from datetime import timedelta

def compare_datetimes(this, other, max_seconds_difference=1):
    if this == other:
        return
    delta = timedelta(seconds=max_seconds_difference)
    return this + delta > other and this - delta < other
