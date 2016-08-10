import json
import time
import uuid
import urllib
import boto3

ddb = boto3.client('dynamodb')
container_id = str(uuid.uuid1())

class IntervalCollection:
    class Interval:
        """
        Represents a 1D interval with closed or open endpoints.
        """
        def __init__(self, Start, End,
                     ContainsStart, ContainsEnd):
            # Swap the endpoints if they're in the wrong order.
            if Start > End:
                Start, End = End, Start
                ContainsStart, ContainsEnd = ContainsEnd, ContainsStart
            
            self.Start = Start
            self.ContainsStart = ContainsStart
            self.End = End
            self.ContainsEnd = ContainsEnd

            if (Start == End) and not (ContainsStart and ContainsEnd):
                print str(self)
                raise ValueError('Inconsistent interval specification.')
        
        def difference(self, Other):
            if not isinstance(Other, IntervalCollection.Interval):
                return None
            """
            If this interval and Other intersect, return the portion of Other
            that is not covered by this interval.
            """
            # If the start of one is in the middle of the other, then there's
            # overlap Check open/closed endpoints.  If the start of one is the
            # end of the other, they both need to be closed.  Otherwise, Other
            # completely encloses this interval, so split it up, removing this
            # interval from the middle.
            r = []
            if (Other.Start <= self.Start) and (Other.End >= self.End):
                r = [(Other.Start, self.Start,
                      Other.ContainsStart, not self.ContainsStart),
                     (self.End, Other.End,
                      not self.ContainsEnd, Other.ContainsEnd)]
            elif (Other.Start >= self.Start) and (Other.Start <= self.End):
                if (self.Start == Other.End) and not (self.ContainsStart and Other.ContainsEnd):
                    return []
                if self.End <= Other.End:
                    r = [(self.End, Other.End,
                          Other.ContainsStart and (not self.ContainsEnd),
                          Other.ContainsEnd)]
            elif (self.Start >= Other.Start) and (self.Start <= Other.End):
                if (self.End == Other.Start) and not (self.ContainsEnd and Other.ContainsStart):
                    return []
                if Other.End <= self.End:
                    r = [(Other.Start, self.Start,
                          Other.ContainsStart,
                          Other.ContainsEnd and (not self.ContainsStart))]
            else:
                r = [ (Other.Start, Other.End, Other.ContainsStart, Other.ContainsEnd) ]
            
            r = [IntervalCollection.Interval(*i) for i in r
                 if not (i[0] == i[1] and not (i[2] and i[3]))]

            return r

        def touches(self, Other):
            """
            Check the endpoints of the intervals to see if they touch.
            Returns True if there are no points between the two intervals.
            Assumes that the two intervals overlap only at endpoints, if at all.
            """
            if self.Start == Other.End and not ((not self.ContainsStart) and (not Other.ContainsEnd)):
                return True
            elif self.End == Other.Start and not ((not self.ContainsEnd) and (not Other.ContainsStart)):
                return True
            else:
                return False

        def __str__(self):
            return "%s%s,%s%s" % ('[' if self.ContainsStart else '(', str(self.Start),
                                  str(self.End), ']' if self.ContainsEnd else ')')

        def __repr__(self):
            return "%s%s,%s%s" % ('[' if self.ContainsStart else '(', repr(self.Start),
                                  repr(self.End), ']' if self.ContainsEnd else ')')
    
    """
    Given a colleciton of open/closed finite or infinite inteverals, this class
    overlays them, and provides functions identifying if given intervals are
    covered by the colleciton.
    """
    def __init__(self):
        self.intervals = []

    def check(self, Interval):
        pass

    def add(self, Interval):
        parts = [ Interval ]
        for i in self.intervals:
            diff = [ i.difference(p) for p in parts ]
            parts = [ j for d in diff for j in d ]
            if parts == []:
                break
        self.intervals.extend(parts)
        self.intervals.sort(key=lambda i: (i.Start, 0 if i.ContainsStart else 1))
        self.merge()

    def difference(self, Interval):
        pass
    
    def merge(self):
        i = 0
        while i < len(self.intervals) - 1:
            if self.intervals[i].touches(self.intervals[i+1]):
                self.intervals[i] = IntervalCollection.Interval(self.intervals[i].Start,
                                                                self.intervals[i+1].End,
                                                                self.intervals[i].ContainsStart,
                                                                self.intervals[i+1].ContainsEnd)
                del self.intervals[i+1]
                i -= 1
            i += 1

    def __str__(self):
        return str(self.intervals)
    
    def __repr__(self):
        return repr(self.intervals)

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

class KTSCache:
    def __init__(self, UpdateFunction, UpdateInterval, SortKeyFunc):
        self.UpdateFunction = UpdateFunction
        self.UpdateInterval = UpdateInterval
        self.SortKeyFunc = SortKeyFunc
        self.values = dict()
        self.ic = IntervalCollection()

    def get(self, HashKey, SortKey, Args):
        if not isinstance(SortKey, int):
            SortKey = int(SortKey)
        AbsSortKey = abs(SortKey)
        SgnSortKey = SortKey / AbsSortKey
        query_target = None

        # If we've encountered this hash key before...
        if HashKey in self.values:
            v = self.values[HashKey]
            # Check to see if the last message us more than UpdateInterval seconds in
            # the past, and if our sortKey is positive. That means we need to fetch.
            #
            # The Sortkey also needs to be strictly after the last message we have,
            # otherwise we could return something from the cache.
            if (SortKey > 0) and (SortKey > last_ts) and ((v[0] + self.UpdateInterval) > time.time()):
                query_target = "Cache"
                truncated = False
            # Check to see if this is a historical fetch, and if so, if it is covered
            # by the cache (indicated by a difference that is an empty set.
            elif SortKey < 0 and self.ic.difference(IntervalCollection.Interval(-SortKey/1000.0, -float('inf'), True, False)) == []:
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
        # Otherwise there's a guarantee that we have to get from Dynamo
        else:
            query_target = "Prime DynamoDB"
            t = time.time()
            v, truncated = self.UpdateFunction(*(Args + (HashKey,SortKey)))
            self.values[HashKey] = [t, v]
        
        if "DynamoDB" in query_target and len(self.values[HashKey][1]) > 0:
            ts, msgs = self.values[HashKey][1]
            if SortKey >= 0:
                a = SortKey / 1000.0
                b = float(msgs[0]['event_timestamp']['N']) if truncated else ts
            elif SortKey < 0:
                a = AbsSortKey / 1000.0
                b = float(msgs[-1]['event_timestamp']['N']) if truncated else -float('inf')
            self.ic.add(IntervalCollection.Interval(a, b, True, True))
        # Return the query target, whether or not the results obtained were truncated,
        # and the list of messages that match given sort key/direction.
        return (query_target,
                truncated,
                [m for m in self.values[HashKey][1] 
                if SgnSortKey * self.SortKeyFunc(m) >= SortKey])

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

ic = IntervalCollection()
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

if __name__ == "__main__":
    print "Running tests"
    ic = IntervalCollection()
    I = IntervalCollection.Interval
    def func(ic, i):
        #print "?", I(*i)
        ic.add(I(*i))
    func(ic, (0,1,False,False))
    func(ic, (0,1,True,True))
    func(ic, (-1,1,True,True))
    func(ic, (-2,-1.5,True,False))
    func(ic, (-1.5,-1,True,True))
    func(ic, (1,2,False,False))
    func(ic, (-3,-2,True,True))
    func(ic, (-1,-0,True,True))
    func(ic, (1,2,True,True))
    func(ic, (-5,5,True,True))
    print ic
    func(ic, (10,100,True,True))
    print ic
    func(ic, (-float('inf'),-10,False,True))
    func(ic, (10,float('inf'),False,False))
    print ic
    func(ic, (-10,10,False,False))
    print ic
