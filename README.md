# ec2-purge-snapshots-lambda
An AWS Lambda function that purges EC2 snapshots according to the rules you specify. This script is based of of https://github.com/stiang/ec2-purge-snapshots

## Usage
This python script is a meant to be run as a scheduled AWS Lamdba function. You should also have another script that takes regular volume snapshots, and this script will allow you to set up a rolling retention policy for those snapshots.  You will need to configure the following variables at the top of the script:
You must populate either the VOLUMES variable or the TAGS variable, but not both.
You must populate the HOURS, DAYS, WEEKS and MONTHS variables.

VOLUMES - List of volume-ids, or "all" for all volumes
eg. ["vol-12345678", "vol-87654321"] or ["all"]

TAGS - Dictionary of tags to use to filter the snapshots. May specify multiple
eg. {'key': 'value'} or {'key1': 'value1', 'key2': 'value2', ...}

HOURS -  The number of hours to keep ALL snapshots

DAYS - The number of days to keep ONE snapshot per day

WEEKS - The number of weeks to keep ONE snapshot per week

MONTHS - The number of months to keep ONE snapshot per month

REGION - AWS region in which the snapshots exist
eg. "us-east-1"

TIMEZONE - The timezone in which daily snapshots will be kept at midnight
eg. "America/Denver"

## Configure Lambda function
### IAM Role Policy
Go to the IAM service in the AWS Management console. Click on Roles and click the Create New Role button. Name the role ec2-purge-snapshots and click Next Step. Click the Select button that is next to the AWS Lambda service. On the Attach Policy page, don't check any boxes and just click Next Step. Click Create Role. Click on the newly created role and expand the Inline Policies and click where it says click here to create a new policy. Click Custom Policy and click Select. Name the policy ec2-purge-snapshots. Copy the contents of the iam_role_policy.json file and paste it in the Policy Document box and click Apply Policy.

### Create Lambda function
#### Configure function
Go to the Lambda service in the AWS Management console. Create a new function and on the Select blueprint page click the Skip button. On the Configure function page fill in the following details:
* Name: ec2-purge-snapshots
* Description: An AWS Lambda function that purges EC2 snapshots according to the rules you specify
* Runtime: Python
* Code box: paste the contents of the ec2-purge-snapshots-lambda.py file
* Handler: ec2-purge-snapshots.main
* Role: ec2-purge-snapshots
* Memory: 128
* Timeout: 10 sec
Click the Next button and click Create function.
In the Code tab, configure the variables at the top of the script to your desired configuration. Click Save.

#### Event sources
Click the Event sources tab and click the Add event source link. Choose the type Scheduled Event and fill in the following details:
* Name: ec2-purge-snapshots.main
* Description: Run script hourly
* Schedule Expression: cron(0 * * * ? *)
Click submit and your function will run every hour at 0 minutes. You can change the cron expression to your desired schedule.

#### Test function
You can test the function from the Lambda console. Click the Actions button and select Configure test event. Choose Scheduled Event from the drop down. Change the account parameter to your actual AWS account number and you can modify the time parameter to a time relativly close to the current time. Note that the script does not expect the time to be before any of the time stamps on the snapshots, so choose a time in the future, or the current time. Add the following parameter to the structure "noop": "True".  This will tell the script to not actually delete any snapshots, but to print that it would have. Now you can press the Save and Test button and you will see the results of the script running in the Lambda console.

#### CloudWatch logs
You will be able to see the output when the script runs in the CloudWatch logs. Go to the CloudWatch service in the AWS Management console. Click on Logs and you will see the ec2-purge-snapshots log group. Click in it and you will see a Log Stream for every time the script is executed which contains all the output of the script. Go back to the Log Group and click the Never Expire link in the Expire Events After column of the log group row. Change the Retention period to what you feel comfortable with.