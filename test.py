from results import lambda_handler
import json

with open('events_info.json', 'r') as f:
    event = json.load(f)

lambda_handler(event, None)