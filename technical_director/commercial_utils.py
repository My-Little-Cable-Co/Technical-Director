import random

from decimal import Decimal
from scheduler_client import SchedulerClient
from video import Video


# NOTE: The intention is to move the commercial selection logic to the
# Scheduler application. Technical Director ideally just says "Give me 1m45s
# of commercials for listing <id>", and the scheduler intelligently constructs
# as close to 1m45s of commercials that are relevant to the listing
# (appropriate for the content being played). For now we'll just make sure we
# don't show a bunch of repeats or commercials for the same subject.
def get_commercial_break(target_duration_in_seconds):
    commercials = all_commercials()
    actual_duration = Decimal(0)
    commercial_break = []
    # Keep track of the amount of times we tried to get closer to our time
    # budget and couldn't. If we exceed 5 attempts, just grab whatever. We just
    # make our best effort at filling the time budget without exceeding it too
    # much, but we'd rather exceed it than underfill. No dead air!
    attempts = 0
    subjects_portrayed = []
    while actual_duration < target_duration_in_seconds and commercials:
        # Pick a random commercial
        random_index = random.choice(range(0, len(commercials)))

        # If the randomly selected commercial has a subject specified, make
        # sure we haven't already included a commercial about that subject
        # this break.
        if commercials[random_index]['subject'] is not None and commercials[random_index]['subject'] in subjects_portrayed:
            continue

        # If the chosen commercial would put us more than ten seconds over our
        # time budget, do not use it. If we exceed five attempts just give up
        # and use whatever.
        if ((actual_duration + Decimal(commercials[random_index]['duration'])) - target_duration_in_seconds) > 10:
            attempts += 1
            if attempts > 5:
                commercial = commercials.pop(random_index)
                decimal_duration = Decimal(commercial['duration'])
                actual_duration += decimal_duration
                subjects_portrayed.append(commercial['subject'])
                commercial_video = Video(commercial['file_path'], duration_in_seconds=decimal_duration)
                commercial_break.append(commercial_video)
        else:
            commercial = commercials.pop(random_index)
            decimal_duration = Decimal(commercial['duration'])
            actual_duration += decimal_duration
            subjects_portrayed.append(commercial['subject'])
            commercial_video = Video(commercial['file_path'], duration_in_seconds=decimal_duration)
            commercial_break.append(commercial_video)
    # TODO: Is there a chance the target duration exceeds the total duration
    # of all commercials? In that case, we would need to repeat. >=-/
    return commercial_break


def all_commercials() -> list:
    client = SchedulerClient()
    return client.get_all_commercials()
