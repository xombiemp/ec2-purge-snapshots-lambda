from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.tz import gettz
from boto3 import resource

# You must populate either the VOLUMES variable or the
# TAGS variable, but not both.
# You must populate the HOURS, DAYS, WEEKS and MONTHS variables.

# List of volume-ids
# eg. ["vol-12345678"] or ["vol-12345678", "vol-87654321", ...]
VOLUMES = []

# Dictionary of tags to use to filter the volumes. May specify multiple
# eg. {"key": "value"} or {"key1": "value1", "key2": "value2", ...}
TAGS = {}

# The number of hours to keep ALL snapshots
HOURS = 0

# The number of days to keep ONE snapshot per day
DAYS = 0

# The number of weeks to keep ONE snapshot per week
WEEKS = 0

# The number of months to keep ONE snapshot per month
MONTHS = 0

# AWS regions in which the snapshots exist
# eg. ["us-east-1"] or ["us-east-1", "us-west-1", ...]
REGIONS = ["us-east-1"]

# The timezone in which daily snapshots will be kept at midnight
# https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List
# eg. "America/Denver"
TIMEZONE = "UTC"


def purge_snapshots(volume, snaps, counts, region):
    newest = snaps[-1]
    prev_start_date = None
    delete_count = 0
    keep_count = 0

    print("---- RESULTS FOR {} in {} ({} snapshots) ----".format(
          volume, region, len(snaps))
          )

    for snap in snaps:
        snap_date = snap.start_time.astimezone(gettz(TIMEZONE))
        if NOW > snap_date:
            snap_age = NOW - snap_date
        else:
            snap_age = timedelta()
        if snap_age <= timedelta(hours=HOURS):
            # Hourly
            snap_age_rep = round(snap_age.total_seconds()/3600)
            print("Keeping {}: {}, {} hour{} old - {}-hour threshold".format(
                  snap.snapshot_id, snap_date, snap_age_rep,
                  "" if snap_age_rep == 1 else "s", HOURS)
                  )
            keep_count += 1
        else:
            if snap_age <= timedelta(hours=START_WEEKS_AFTER):
                # Daily
                type_str = "day"
                snap_age_rep = snap_age.days
                start_date_str = snap_date.strftime("%Y-%m-%d")
            elif snap_age <= timedelta(hours=START_MONTHS_AFTER):
                # Weekly
                type_str = "week"
                snap_age_rep = int(snap_age.total_seconds()/3600/24/7)
                week_day = int(snap_date.strftime("%w"))
                start_date = snap_date - timedelta(days=week_day)
                start_date_str = start_date.strftime("%Y-%m-%d")
            else:
                # Monthly
                type_str = "month"
                snap_age_rep = relativedelta(NOW, snap_date).months
                start_date_str = snap_date.strftime("%Y-%m")
            if (start_date_str != prev_start_date and
                    snap_date > DELETE_BEFORE_DATE):
                # Keep it
                prev_start_date = start_date_str
                print("Keeping {}: {}, {} {}{} old - {} of {}".format(
                      snap.snapshot_id, snap_date, snap_age_rep, type_str,
                      "" if snap_age_rep == 1 else "s",
                      type_str, start_date_str)
                      )
                keep_count += 1
            elif snap.snapshot_id == newest.snapshot_id:
                # Never delete the newest snapshot
                print(("Keeping {}: {}, {} {}{} old - will never"
                      " delete newest snapshot").format(
                      snap.snapshot_id, snap_date, snap_age_rep, type_str,
                      "" if snap_age_rep == 1 else "s")
                      )
                keep_count += 1
            else:
                # Delete it
                print("- Deleting{} {}: {}, {} {}{} old".format(
                      NOT_REALLY_STR, snap.snapshot_id,
                      snap_date, snap_age_rep, type_str,
                      "" if snap_age_rep == 1 else "s")
                      )
                if NOOP is False:
                    snap.delete()
                delete_count += 1
    counts[volume] = [delete_count, keep_count]


def get_vol_snaps(ec2, volume):
    collection_filter = [
        {
            "Name": "volume-id",
            "Values": [volume]
        },
        {
            "Name": "status",
            "Values": ["completed"]
        }
    ]
    collection = ec2.snapshots.filter(Filters=collection_filter)
    return sorted(collection, key=lambda x: x.start_time)


def get_tag_volumes(ec2):
    collection_filter = []
    for key, value in TAGS.items():
        collection_filter.append(
            {
                "Name": "tag:" + key,
                "Values": [value]
            }
        )
    collection = ec2.volumes.filter(Filters=collection_filter)
    return list(collection)


def print_summary(counts, region):
    print("\nSUMMARY:\n")
    for volume, (deleted, kept) in counts.items():
        print("{} in {}:".format(volume, region))
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

    NOW = datetime.now(gettz(TIMEZONE)).replace(microsecond=0,
                                                second=0,
                                                minute=0
                                                )
    START_WEEKS_AFTER = HOURS + (DAYS * 24)
    START_MONTHS_AFTER = START_WEEKS_AFTER + (WEEKS * 24 * 7)
    DELETE_BEFORE_DATE = ((NOW - timedelta(hours=START_MONTHS_AFTER)) -
                          relativedelta(months=MONTHS)
                          )
    NOOP = event["noop"] if "noop" in event else False
    NOT_REALLY_STR = " (not really)" if NOOP is not False else ""
    for region in REGIONS:
        ec2 = resource("ec2", region_name=region)

        if VOLUMES and not TAGS:
            for volume in VOLUMES:
                volume_counts = {}
                snapshots = get_vol_snaps(ec2, volume)
                if snapshots:
                    purge_snapshots(volume, snapshots, volume_counts, region)
                    print_summary(volume_counts, region)
                else:
                    print(("No snapshots found with volume id:"
                          " {} in {}").format(volume, region))
        elif TAGS and not VOLUMES:
            tag_string = " ".join("{}={}".format(key, val) for
                                                (key, val) in TAGS.items())
            volumes = get_tag_volumes(ec2)
            if volumes:
                for volume in volumes:
                    volume_counts = {}
                    snapshots = get_vol_snaps(ec2, volume.volume_id)
                    if snapshots:
                        purge_snapshots(volume.volume_id, snapshots,
                                        volume_counts, region)
                        print_summary(volume_counts, region)
                    else:
                        print(("No snapshots found with volume id:"
                              " {} in {}").format(
                              volume.volume_id, region)
                              )
            else:
                print("No volumes found with tags: {} in {}".format(
                      tag_string, region)
                      )
        else:
            print("You must populate either the VOLUMES OR the TAGS variable.")
