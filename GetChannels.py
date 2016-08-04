import time
import boto3

ddb = boto3.client('dynamodb')

class CacheController:
    def __init__(self, CacheTime):
        self.CacheTime = CacheTime
        self.last_update_time = 0.0
        self.value = None
    
    def is_expired(self):
        return (time.time() > (self.last_update_time + self.CacheTime))
    
    def update_value(self, value):
        self.value = value
        self.last_update_time = time.time()
        return self.value
    
    def get_value(self):
        return self.value

cache = CacheController(5.0) 

# List all non-default channels (the client knows what the default channel is
# called.
def handler(event, context):
    if 'MessagesTable' not in event or 'ParticipantsTable' not in event:
        return []
    
    # If it's time to get a new value.
    if cache.is_expired():
        result = ddb.query(TableName=event['MessagesTable'],
                           KeyConditionExpression='contextkey = :k',
                           ExpressionAttributeValues={':k': {'S': 'meta:channels'}})
        cache.update_value(result)
    else:
        result = cache.get_value()

    try:
        return {'channels': [i['channel_name']['S']
                             for i in result['Items']
                             if 'channel_name' in i ]}
    except:
        return {'channels': []}