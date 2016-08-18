import json
import time
import uuid
import urllib
import boto3

ddb = boto3.client('dynamodb')
container_id = str(uuid.uuid1())

def sorted_unique(l):
    s = set()
    r = []
    for i in l:
        if i['event_timestamp']['N'] not in s:
            s.add(i['event_timestamp']['N'])
            r.append(i)
    r.sort(key=lambda i: i['event_timestamp']['N'])
    r.reverse()
    return r

class KeyedTimeseriesCache:
    def __init__(self, UpdateFunction, UpdateInterval, SortKeyFunc):
        self.UpdateFunction = UpdateFunction
        self.UpdateInterval = UpdateInterval
        self.SortKeyFunc = SortKeyFunc
        self.values = dict()

    def get(self, HashKey, SortKey, Args):
        if not isinstance(SortKey, int):
            SortKey = int(SortKey)
        AbsSortKey = abs(SortKey)
        SgnSortKey = SortKey / AbsSortKey
        query_target = None
        if HashKey in self.values:
            v = self.values[HashKey]
            potential_overlap = False
            if len(v[1]) > 0:
                first_ts = self.SortKeyFunc(v[1][-1])
                last_ts = self.SortKeyFunc(v[1][0])

                # If we're scanning forward in time, and starting prior to the
                # newest message
                if SortKey > 0 and SortKey < last_ts:
                    potential_overlap = True
                # If we're scanning backward in time, and starting after the
                # oldest message
                elif SortKey < 0 and AbsSortKey > first_ts:
                    potential_overlap = True
            else:
                first_ts = AbsSortKey + 1
                last_ts = AbsSortKey - 1

            # Don't ask Dynamo if we're querying forward in time, and the sort
            # key is after the newest message (this is the caching case).
            #
            # TODO Do something with the current time, the SortKey, and the
            # update interval, to ensure that we're being asked for 'new'
            # messages, not slightly historical messages
            if (SortKey > 0) and (SortKey > last_ts) and ((v[0] + self.UpdateInterval) > time.time()):
                query_target = "Cache"
                truncated = False
            else:
                query_target = "DynamoDB"
                v[0] = time.time()
                r = self.UpdateFunction(*(Args + (HashKey,SortKey)))
                v[1] = r[0] + v[1]
                truncated = r[1]
                if potential_overlap:
                    v[1] = sorted_unique(v[1])
                self.values[HashKey] = v
        else:
            query_target = "Prime DynamoDB"
            t = time.time()
            v, truncated = self.UpdateFunction(*(Args + (HashKey,SortKey)))
            self.values[HashKey] = [t, v]
        return (query_target,
                truncated,
                [m for m in self.values[HashKey][1] 
                 if SgnSortKey * self.SortKeyFunc(m) >= SortKey])

def ddb_update_function(TableName, Channel, StartTimestamp):
    messages = ddb.query(TableName=TableName,
                             KeyConditionExpression='contextkey = :k AND event_timestamp %s= :t' % \
                                                    ('>' if StartTimestamp > 0 else '<'),
                             ExpressionAttributeValues={
                                 ':k': {'S': Channel},
                                 ':t': {'N': repr(abs(StartTimestamp) / 1000.0)}
                                 },
                             ScanIndexForward=False)
    return (messages['Items'], 'LastEvaluatedKey' in messages)

ddb_cache = KeyedTimeseriesCache(lambda event, channel, timestamp:
                                 ddb_update_function(event['MessagesTable'], channel, timestamp),
                                 1.0,
                                 lambda message: int((1000 * float(message['event_timestamp']['N']))))

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
    try:
        print "X-Forwarded-For %s %s" % (repr(time.time()),
                                         event['InputParams']['header']['X-Forwarded-For'].replace(',',''))
    except:
        pass

    if 'MessagesTable' not in event or 'ParticipantsTable' not in event:
        return {'messages': [], 'error': 'dynamo table names not in event'}

    channel = get_param(event, 'Channel')
    start_ts_str = get_param(event, 'FromTimestamp')

    try:
        start_ts = int(start_ts_str)
    except:
        return {'messages': [], 'error': 'start timestamp not an int: %s' % start_ts_str}

    if not isinstance(channel, str) and not isinstance(channel, unicode):
        return {'messages': [], 'error': 'channel name not a string'}

    # Don't forget to prepend the meta-key
    channel = 'channel:' + urllib.unquote(channel).decode('utf8')

    try:
        query_target, truncated, messages = ddb_cache.get(channel, start_ts, (event,))
        print query_target
    except Exception as e:
        return {'messages': [], 'error': 'error querying table', 'repr': repr(e)}
    else:
        if not isinstance(messages, list):
            return {'messages': [], 'error': 'query returned no items'}
        return {'truncated': truncated,
                'messages':
                   #[{'message': json.dumps(event),
                   #'participant': 'Server',
                   #'timestamp': int(1000*time.time()),
                   #'source': 'server'
                   #}] + \
                   #[{'message': container_id + " - " + query_target,
                   #'participant': 'Server',
                   #'timestamp': int(1000*time.time()),
                   #'source': 'server'}] + \
                   [{'message': m['message']['S'],
                   'participant': m['participant']['S'],
                   'timestamp': int(1000 * float(m['event_timestamp']['N'])),
                   'source': m['source']['S'] if 'source' in m else 'user'}
                    for m in messages ]}
