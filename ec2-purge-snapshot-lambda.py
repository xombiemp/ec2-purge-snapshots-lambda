from __future__ import print_function
from datetime import timedelta
from dateutil import parser, relativedelta, tz
from boto3 import resource

# You must populate either the VOLUMES variable or the
# TAGS variable, but not both.
# You must populate the HOURS, DAYS, WEEKS and MONTHS variables.

# List of volume-ids, or "all" for all volumes
# eg. ["vol-12345678", "vol-87654321"] or ["all"]
VOLUMES = []

# Dictionary of tags to use to filter the snapshots. May specify multiple
# eg. {'key': 'value'} or {'key1': 'value1', 'key2': 'value2', ...}
TAGS = {}

# The number of hours to keep ALL snapshots
HOURS = 0

# The number of days to keep ONE snapshot per day
DAYS = 0

# The number of weeks to keep ONE snapshot per week
WEEKS = 0

# The number of months to keep ONE snapshot per month
MONTHS = 0

# AWS region in which the snapshots exist
REGION = "us-east-1"

# The timezone in which daily snapshots will be kept at midnight
TIMEZONE = "UTC"


def purge_snapshots(id, snaps, counts):
    newest = snaps[-1]
    prev_start_date = None
    delete_count = 0
    keep_count = 0

    print("---- RESULTS FOR {} ({} snapshots) ----".format(id, len(snaps)))

    for snap in snaps:
        snap_date = snap.start_time.astimezone(tz.gettz(TIMEZONE))
        snap_age = NOW - snap_date
        # Hourly
        if snap_age > timedelta(hours=HOURS):
            # Daily
            if snap_age <= timedelta(hours=START_WEEKS_AFTER):
                type_str = "day"
                start_date_str = snap_date.strftime("%Y-%m-%d")
                start_date = parser.parse(start_date_str)
            else:
                # Weekly
                if snap_age <= timedelta(hours=START_MONTHS_AFTER):
                    type_str = "week"
                    week_day = int(snap_date.strftime("%w"))
                    start_date = snap_date - timedelta(days=week_day)
                    start_date_str = start_date.strftime("%Y-%m-%d")
                else:
                    # Monthly
                    type_str = "month"
                    start_date_str = snap_date.strftime("%Y-%m")
                    start_date = parser.parse(start_date_str + "-01")
            if (start_date_str != prev_start_date and
                    snap_date > DELETE_BEFORE_DATE):
                # Keep it
                prev_start_date = start_date_str
                print("Keeping {}: {}, {} days old - {} of {}".format(
                      snap.snapshot_id, snap_date, snap_age.days,
                      type_str, start_date_str)
                      )
                keep_count += 1
            else:
                # Never delete the newest snapshot
                if snap.snapshot_id == newest.snapshot_id:
                    print(("Keeping {}: {}, {} hours old - will never"
                          " delete newest snapshot").format(
                          snap.snapshot_id, snap_date,
                          snap_age.seconds/3600)
                          )
                    keep_count += 1
                else:
                    # Delete it
                    print("- Deleting{} {}: {}, {} days old".format(
                          NOT_REALLY_STR, snap.snapshot_id,
                          snap_date, snap_age.days)
                          )
                    if NOOP is False:
                        snap.delete()
                    delete_count += 1
        else:
            print("Keeping {}: {}, {} hours old - {}-hour threshold".format(
                  snap.snapshot_id, snap_date, snap_age.seconds/3600, HOURS)
                  )
            keep_count += 1
    counts[id] = [delete_count, keep_count]


def get_vol_snaps(ec2, account_id, volume):
    if len(VOLUMES) == VOLUMES.count("all"):
        collection_filter = [
            {
                "Name": "owner-id",
                "Values": [account_id]
            },
            {
                "Name": "status",
                "Values": ["completed"]
            }
        ]
    else:
        collection_filter = [
            {
                "Name": "volume-id",
                "Values": [volume]
            },
            {
                "Name": "owner-id",
                "Values": [account_id]
            },
            {
                "Name": "status",
                "Values": ["completed"]
            }
        ]
    collection = ec2.snapshots.filter(Filters=collection_filter)
    return sorted(collection, key=lambda x: x.start_time)


def get_tag_snaps(ec2, account_id):
    collection_filter = [
        {
            "Name": "owner-id",
            "Values": [account_id]
        },
        {
            "Name": "status",
            "Values": ["completed"]
        }
    ]
    for key, value in TAGS.iteritems():
        collection_filter.append(
            {
                "Name": "tag:" + key,
                "Values": [value]
            }
        )
    collection = ec2.snapshots.filter(Filters=collection_filter)
    return sorted(collection, key=lambda x: x.start_time)


def print_summary(counts):
    print("\nSUMMARY:\n")
    for id, (deleted, kept) in counts.iteritems():
        print("{}:".format(id))
        print("  deleted: {}{}".format(
              deleted, NOT_REALLY_STR if deleted > 0 else "")
              )
        print("  kept:    {}".format(kept))
        print("-------------------------------------------\n")


def main(event, context):
    global NOW
    global START_WEEKS_AFTER
    global START_MONTHS_AFTER
    global DELETE_BEFORE_DATE
    global NOOP
    global NOT_REALLY_STR

    NOW = parser.parse(event['time']).astimezone(tz.gettz(TIMEZONE))
    START_WEEKS_AFTER = HOURS + (DAYS * 24)
    START_MONTHS_AFTER = START_WEEKS_AFTER + (WEEKS * 24 * 7)
    DELETE_BEFORE_DATE = ((NOW - timedelta(hours=START_MONTHS_AFTER)) -
                          relativedelta.relativedelta(months=MONTHS)
                          )
    NOOP = event['noop'] if 'noop' in event else False
    NOT_REALLY_STR = " (not really)" if NOOP is not False else ""
    ec2 = resource("ec2", region_name=REGION)

    if VOLUMES and not TAGS:
        for volume in VOLUMES:
            volume_counts = {}
            snapshots = get_vol_snaps(ec2, event['account'], volume)
            if snapshots:
                purge_snapshots(volume, snapshots, volume_counts)
                print_summary(volume_counts)
            else:
                print("No snapshots found with volume id: {}".format(volume))
    elif TAGS and not VOLUMES:
        tag_counts = {}
        tag_string = " ".join("{}={}".format(key, val) for
                                            (key, val) in TAGS.iteritems())
        snapshots = get_tag_snaps(ec2, event['account'])
        if snapshots:
            purge_snapshots(tag_string, snapshots, tag_counts)
            print_summary(tag_counts)
        else:
            print("No snapshots found with tags: {}".format(tag_string))
    else:
        print("You must populate either the VOLUMES OR the TAGS variable.")
