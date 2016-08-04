import time
import boto3

ddb = boto3.client('dynamodb')

class KVCache:
    """
    Caches a list of values based identified by a key, only
    updating at a maximum frequency.
    """
    def __init__(self, UpdateFunction, UpdateInterval):
        self.UpdateFunction = UpdateFunction
        self.UpdateInterval = UpdateInterval
        self.values = dict()
    
    def get(self, HashKey, Args):
        if HashKey in self.values:
            v = self.values[HashKey]
            t = time.time()
            if v[0] < (t - self.UpdateInterval):
                print "Running update function"
                v[0] = t
                v[1] = self.UpdateFunction(*(Args + (HashKey,)))
                self.values[HashKey] = v
            else:
                print "Returning cached value"
        else:
            print "First time seeing key"
            v = [time.time(), self.UpdateFunction(*(Args + (HashKey,)))]
            self.values[HashKey] = v
        return self.values[HashKey][1]

def ddb_update_function(TableName, Channel):
    participants = ddb.query(TableName=TableName,
                             IndexName='LastParticipantActivity',
                             KeyConditionExpression='channel = :c AND last_seen > :t',
                             ExpressionAttributeValues={
                                 ':c': {'S': Channel},
                                 ':t': {'N': repr(time.time() - 2.0)}},
                             ConsistentRead=True)
    return participants

ddb_cache = KVCache(lambda event, channel:
                    ddb_update_function(event['ParticipantsTable'],
                                        channel), 1.0)

def get_param(event, key):
    v = None
    try:
        v = event['InputParams']['path'][key]
    except:
        try:
            v = event['InputParams']['querystring'][key]
        except:
            v = None
    return v

def handler(event, context):
    if 'MessagesTable' not in event or 'ParticipantsTable' not in event:
        return []

    channel = get_param(event, 'Channel')
    if not (isinstance(channel, str) or isinstance(channel, unicode)):
        return {'participants': [], 'error': 'channel not in request'}

    participants = ddb_cache.get(channel, (event,))

    try:
        return {'participants': [ i['participant']['S'] for i in participants['Items'] if 'participant' in i ]}
    except:
        return {'participants': []}
