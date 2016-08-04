import time
import json
import boto3

ddb = boto3.client('dynamodb')

class StringEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            return str(o)
        except:
            return None

def handler(event, context):
    return json.loads(json.dumps({"Event": event, "ContextDict": context.__dict__}, cls=StringEncoder))
