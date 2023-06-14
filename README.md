# maprun-results

This project automatically downloads separate results from multiple [Maprun events](https://maprunners.weebly.com/), then combines points and time scores for each competitor. It then ranks competitors by overall number of points and time taken. The combined results in CSV and HTML format are stored locally, and optionally uploaded to a website.

## Usage
### Local
First, configure `events_info.json`, specifying:
- `"file"`: json filename containing custom event names and results URLs (see `peak_raid_2023.json` for an example)
- `"html_name"`: name for html and csv files
- `"html_title"`: html title

Ensure that, together with `events_info.json`, the events file itself (eg `peak_raid_2023.json`) is present in the local directory.

Optionally, export the following environment variables to enable FTP upload:
- `UPLOAD_ADDRESS` (eg "ftp.mywebsitehost.com")
- `UPLOAD_DIRECTORY` (eg "/public_html/maprun-results/")
- `UPLOAD_USERNAME`
- `UPLOAD_PASSWORD`

In bash, this would be achieved using:
```
export UPLOAD_ADDRESS="ftp.mywebsitehost.com"
```
Repeat for the others.

Now, in a python virtual environment, run the following commands:
```
pip install -r requirements.txt
python results.py
```
This will produce CSV and HTML files locally, which will also be uploaded to the specified upload location, if specified. This script could be run on a local machine with a cron schedule if desired. Or set it to run in the cloud (see AWS Lambda example below) and forget about it :smile:!

### AWS Lambda
#### Create and upload Docker image
Run the following commands to build the Docker image and upload to AWS ECR:
```
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin [aws-account-id].dkr.ecr.us-east-1.amazonaws.com
docker build -t maprun-results .
docker tag maprun-results:latest [aws-account-id].dkr.ecr.us-east-1.amazonaws.com/maprun-results:latest
docker push [aws-account-id].dkr.ecr.us-east-1.amazonaws.com/maprun-results:latest
```
#### Create Lambda function
- Configure an AWS Lambda function with this ECR image
- Set the environment variables
- Increase the timeout to at least 1 minute
#### Create EventBridge schedule
Finally configure an EventBridge schedule (eg once per hour), that will trigger the Lambda function. In the schedule target, copy and paste from `events_info.json`.

## Example combined results

The repository is deployed on AWS for regular updates to [Peak Raid series](https://explorerevents.co.uk/) combined results:
- [HTML](http://qdata.byethost4.com/peakraid/2023.html)
- [CSV](http://qdata.byethost4.com/peakraid/2023.csv)
