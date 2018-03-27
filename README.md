# ec2-purge-snapshots-lambda
An AWS Lambda function that purges EC2 snapshots according to the rules you specify. This script is based off of https://github.com/stiang/ec2-purge-snapshots

## Usage
This python script is a meant to be run as a scheduled AWS Lamdba function. You should also have another script that takes regular volume snapshots like https://github.com/xombiemp/ec2-take-snapshots-lambda, and this script will allow you to set up a rolling retention policy for those snapshots.  You will need to configure the following variables at the top of the script:  
You must populate either the VOLUMES variable or the TAGS variable, but not both.  
You must populate the HOURS, DAYS, WEEKS and MONTHS variables.  

VOLUMES - List of volume-ids  
eg. ["vol-12345678"] or ["vol-12345678", "vol-87654321", ...]

TAGS - Dictionary of tags to use to filter the volumes. May specify multiple  
eg. {"key": "value"} or {"key1": "value1", "key2": "value2", ...}

HOURS -  The number of hours to keep ALL snapshots

DAYS - The number of days to keep ONE snapshot per day

WEEKS - The number of weeks to keep ONE snapshot per week

MONTHS - The number of months to keep ONE snapshot per month

REGIONS - AWS regions in which the snapshots exist  
eg. ["us-east-1"] or ["us-east-1", "us-west-1", ...]

TIMEZONE - The timezone in which daily snapshots will be kept at midnight  
https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List  
eg. "America/Denver"

## Configure Lambda function
### IAM Role Policy
Go to the IAM service in the AWS Management console. Click on Roles and click the Create Role button. Click Lambda under the 'Choose the service that will use this role' section and click the Next:Permissions button. On the 'Attach permissions policies' page, don't check any boxes and just click the Next:Review button. Name the role ec2-purge-snapshots and click the Create role button. Click on the newly created role and click the Add inline policy link and click the JSON tab. Copy the contents of the iam_role_policy.json file and paste it in the box and click the Review policy button. Name the policy root and click the Create policy button.

### Create Lambda function
#### Configure function
Go to the Lambda service in the AWS Management console. Create the Create function button and on the Author from scratch page fill in the following details:
* Name: ec2-purge-snapshots
* Runtime: Python 3.6
* Role: Choose an existing role
* Existing role: ec2-purge-snapshots  
Click the Create function button. In the Function code box fill out:
* Handler: lambda_function.main
* Code box: paste the contents of the ec2-purge-snapshots-lambda.py file  
Scroll down to the settings at the bottom. In Basic settings fill in:
* Description: An AWS Lambda function that purges EC2 snapshots according to the rules you specify
* Memory: 128
* Timeout: 1 min 0 sec  
In the code editor, configure the variables at the top of the script to your desired configuration. Click Save.

#### Event sources
In the Designer - Add triggers box click CloudWatch Events and click the CloudWatch Events box on the right. Click Create a new rule in the Rule dropdown. Fill in the following details:
* Name: ec2-purge-snapshots
* Description: Run script hourly
* Schedule Expression: cron(0 * * * ? *)  
Your function will run every hour at 0 minutes. You can change the cron expression to your desired schedule. Click the Add button and then click the Save button.

#### Test function
You can test the function from the Lambda console. Click the Select a test event.. button and select Configure test events. Choose Scheduled Event from the Event template drop down. Add the following parameter to the structure "noop": "True".  This will tell the script to not actually delete any snapshots, but to print that it would have. Name the Event name noop and click the Create button. Click the Test button and you will see the results of the script running in the Lambda console.

#### CloudWatch logs
You will be able to see the output when the script runs in the CloudWatch logs. Go to the CloudWatch service in the AWS Management console. Click on Logs and you will see the ec2-purge-snapshots log group. Click in it and you will see a Log Stream for every time the script is executed which contains all the output of the script. Go back to the Log Groups and click the Never Expire link in the Expire Events After column of the log group row. Change the Retention period to what you feel comfortable with.