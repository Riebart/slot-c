import json
import time
import boto3

ddb = boto3.client('dynamodb')

def handler(event, context):
    try:
        print "X-Forwarded-For %s %s" % (repr(time.time()),
                                         event['InputParams']['header']['X-Forwarded-For'].replace(',',''))
    except:
        pass

    if 'MessagesTable' not in event or 'ParticipantsTable' not in event:
        return []

    try:
        channel = event['OriginalBody']['channel']
        participant = event['OriginalBody']['participant']
    except:
        participant = None

    if participant == None:
        print "participant is NONE"
        return False

    try:
        ddb.update_item(TableName=event['ParticipantsTable'],
                        Key={'participant': {'S': participant},
                             'channel': {'S': channel}},
                        UpdateExpression='set last_seen = :t',
                        ExpressionAttributeValues={':t': {'N': repr(time.time())}})
    except Exception as e:
        return False

    return True
