import json
import time
import hashlib
import urllib
import boto3

ddb = boto3.client('dynamodb')

class SlashCommand:
    @staticmethod
    def do(Event, Channel, Participant, Message):
        pass
    @staticmethod
    def help():
        return ""

class ChannelCmd(SlashCommand):
    @staticmethod
    def do(Event, Channel, Participant, Message):
        try:
            # Generate a unique timestamp numeric value from the SHA256 hash of
            # the
            # channel name.
            #
            # str() doesn't include the 'L' in the long integer type, and as
            # per the
            # DynamoDB limits, the integer fields can have up to 38 digits of
            # precision,
            # which corresponds to about 128 bits (32 hex digits), so cut off a
            # couple
            # for safety.
            # See:
            # https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Limits.html#limits-data-types)
            ts_hash = str(int(hashlib.sha256(Message.strip()).hexdigest()[:30], 16))
            ddb.update_item(TableName=Event['MessagesTable'],
                            Key={'contextkey': {'S': 'meta:channels'},
                                 'event_timestamp': {'N': ts_hash}},
                            UpdateExpression='set channel_name = :c',
                            ExpressionAttributeValues={':c': {'S': Message.strip()}})
            return None
        except Exception as e:
            print repr(e)
            return None

    @staticmethod
    def help():
        return """
        /channel <ChannelName>
        - Create a new channel, if the channel already exists, no changes are made.
        - The channel will appear in the list at the next channel refresh period.
        - Channels cannot be deleted.
        """

class GroupCmd(SlashCommand):
    @staticmethod
    def do(Event, Channel, Participant, Message):
        pass
    @staticmethod
    def help():
        return """
        /group create <grou pname> <participant> [participant] ...
        - Create a group with the given alias and participants
        /@ <participant> [participant] ...
        - Create a group with the default alias (comma separated list of participant usernames) and given participants.
        /group rename <old group name> <new group name>
        - Rename a group of which you are a member.
        /leave <group name>
        - Exit a group. IT IS NOT POSSIBLE TO RE JOIN A GROUP YOU HAVE LEFT.
        - When a member of a group leaves, and the group was given the default alias (with /@), the group's alias is updated to reflect the new membership list.
        /group delete <group name>
        - Delete a group of which you are a member. This will result in all group message content being unrecoverable.
        /group members <group name>
        - Obtain membership list of a group with the given alias.
        """

class PublishCmd(SlashCommand):
    @staticmethod
    def do(Event, Channel, Participant, Message):
        pass
    @staticmethod
    def help():
        return """
        /publish <message>
        - Publish a message to all subscribed participants.
        - The message will appear to all other participants as normal, but will be posted to the channel's SNS topic.
        """

class SubscribeCmd(SlashCommand):
    @staticmethod
    def do(Event, Channel, Participant, Message):
        pass
    @staticmethod
    def help():
        return """
        /subscription <none|published|all> <realtime|daily> <email|sms>
        - Changes subscription settings for the active channel, with three parameters:
        > Which messages to get notifications for (if 'none' is given, the other parameters are ignored)
        > How frequently to receive notifications about new messages.
        > Which channel you want to receive notifications via.
        """

class PGPCmd(SlashCommand):
    @staticmethod
    def do(Event, Channel, Participant, Message):
        pass
    @staticmethod
    def help():
        return """
        /pgp challenge
        - The server will return the challenge nonce, and a timeout for the response.
        - If the user already has a PGP key associated it, the recipient of the key will also be indicated.
        - The server expects the challenge nonce signed with the user's PGP key.
   
        /pgp response <ASCII-armoured PGP-clearsigned challenge nonce, stripped of newlines>
        - Authenticate to the server by responding to the challenge.
        """

slash_commands = { 'channel': ChannelCmd.do,
                   'group': GroupCmd.do,
                   'pgp': PGPCmd.do,
                   'publish': PublishCmd.do,
                   'subscribe': SubscribeCmd.do,
                   'help': lambda e, c, p, a: "\n".join([cmd.help() for cmd in [ChannelCmd,
                                                               GroupCmd,
                                                               PGPCmd,
                                                               PublishCmd,
                                                               SubscribeCmd]]) }

def handle_slash_command(Event, Channel, Participant, Message):
    # It needs to have some characters, and start with a slash.
    if len(Message) > 0 and Message[0] == '/':
        parts = Message[1:].split(' ', 1)
        if len(parts) == 1:
            command_key = parts[0]
            args = None
        else:
            command_key, args = parts
        if command_key in slash_commands:
            return (None, slash_commands[command_key](Event, Channel, Participant, args).strip().split('\n'))
        else:
            return (Message, None)
    else:
        return (Message, None)

def handler(event, context):
    try:
        print "X-Forwarded-For %s %s" % (repr(time.time()),
                                         event['InputParams']['header']['X-Forwarded-For'].replace(',',''))
    except:
        pass

    # All events should have two pieces of information at the top level.
    if 'MessagesTable' not in event or 'ParticipantsTable' not in event:
        return {'server_messages': None}

    try:
        channel = 'channel:' + event['OriginalBody']['channel']
        participant = event['OriginalBody']['participant']
        message = event['OriginalBody']['message']
    except:
        return {'server_messages': None, 'result': False}

    message, server_messages = handle_slash_command(event, channel, participant, message)

    if message == None:
        return {'server_messages': server_messages, 'result': True}

    # Everything needs to be a string.
    for v in [channel, participant, message]:
        if not isinstance(v, str) and not isinstance(v, unicode):
            return {'server_messages': None, 'result': False}

    # If the message checks out, put it into the table.
    try:
        ddb.put_item(TableName=event['MessagesTable'],
                     Item={'contextkey': {'S': channel},
                           'participant': {'S': participant},
                           'event_timestamp': {'N': repr(time.time())},
                           'message': {'S': message}})
    except Exception as e:
        return {'server_messages': None, 'result': False}

    return {'server_messages': None, 'result': True}