import os

import arrow
import requests


class SchedulerClient:
    def __init__(self):
        self.scheduler_url = os.getenv('SCHEDULER_URL')
        if self.scheduler_url is None:
            raise RuntimeError('SCHEDULER_URL not found in ENV. Example: "export SCHEDULER_URL=http://mlcc-03.local"')

    def get_all_commercials(self):
        response = requests.get(f'{self.scheduler_url}/commercials.json')
        response.raise_for_status()
        commercials = response.json()
        return commercials

    def whats_on(self, channel_number, querytime):
        channel_schedule = requests.get(f'{self.scheduler_url}/channels/ch{channel_number}/schedule.json')
        target_listing = None
        for listing in channel_schedule.json()['lineup']:
            # Warning!! We ignore timezones. Make sure the timezone of your
            # technical director and your scheduler match!!
            listing_start_time = arrow.get(listing['start_time']).datetime.replace(tzinfo=None)
            if(querytime == listing_start_time):
                target_listing = listing
        if target_listing is None:
            return None
        start_time = arrow.get(target_listing['start_time']).datetime.replace(tzinfo=None)
        end_time = arrow.get(target_listing['end_time']).datetime.replace(tzinfo=None)
        block_data = {
            'label': target_listing['title'],
            'listing_id': target_listing['listing_id'],
            'file_path': target_listing.get('file_path'),
            'show_commercials': True,
            'block_start': start_time,
            'block_duration_in_minutes': int((end_time - start_time).seconds / 60),
        }
        return block_data
