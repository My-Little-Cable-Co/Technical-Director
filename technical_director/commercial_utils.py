import json
import random
from decimal import Decimal


def get_commercial_break(target_duration_in_seconds):
    commercials = all_commercials()
    actual_duration = Decimal(0)
    commercial_break = []
    # Keep track of the amount of times we tried to get closer to our time
    # budget and couldn't. If we exceed 5 attempts, just grab whatever. We just
    # make our best effort at filling the time budget without exceeding it too
    # much, but we'd rather exceed it than underfill. No dead air!
    attempts = 0
    while actual_duration < target_duration_in_seconds and commercials:
        # Pick a random commercial
        random_index = random.choice(range(0, len(commercials)))
        # If the chosen commercial would put us more than ten seconds over our
        # time budget, do not use it. If we exceed five attempts just give up
        # and use whatever.
        if ((actual_duration + Decimal(commercials[random_index]['duration'])) - target_duration_in_seconds) > 10:
            attempts += 1
            if attempts > 5:
                actual_duration += Decimal(commercials[random_index]['duration'])
                commercial_break.append(commercials.pop(random_index)['filepath'])
        else:
            actual_duration += Decimal(commercials[random_index]['duration'])
            commercial_break.append(commercials.pop(random_index)['filepath'])
    # TODO: Is there a chance the target duration exceeds the total duration
    # of all commercials? In that case, we would need to repeat. >=-/
    return commercial_break


def all_commercials() -> list:
    commercials = []
    with open('/home/pi/video/commercials/commercials.json', 'r') as commercial_database:
        commercials = json.load(commercial_database)
    return commercials
