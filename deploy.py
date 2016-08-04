
#!/usr/bin/env python

# Create or update a stack with neww function code, ensuring that DynamoDB tables and
# S3 buckets are properly populated with the necessary items and files.

import sys
import json
import time
import zipfile
import argparse
import tempfile
import boto3

class JSONArg(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            parsed_val = json.loads(values)
        except:
            parsed_val = None
        setattr(namespace, self.dest, parsed_val)

def s3_domain(s3):
    region = s3._client_config.region_name
    if region == "us-east-1":
        return "s3"
    else:
        return "s3-%s" % region

def stack_param(k, v):
    if v == None:
        return {'ParameterKey': k, 'UsePreviousValue': True}
    else:
        return {'ParameterKey': k, 'ParameterValue': v}

def deploy_lambda_code(config):
    pass

def prologue(args):
    try:
        with open('deploy_config.json','r') as fp:
            config = json.loads(fp.read())
    except:
        print "Unable to load configuration JSON from deploy_config.json"
        exit(1)

    if args.stack_name != None:
        config['StackName'] = args.stack_name
    else:
        config['StackName'] = config['StackNamePrefix'] + str(int(time.time()))[-4:]

    # Merge the parameters, overwriting the base ones with the the command-line
    # provided ones.
    stack_params = {}
    if 'BaseStackParameters' in config and len(config['BaseStackParameters']) > 0:
        stack_params.update(config['BaseStackParameters'])
        del config['BaseStackParameters']
    if args.stack_parameters != None:
        stack_params.update(args.stack_parameters)

    if len(stack_params) > 0:
        config['StackParams'] = [ stack_param(k, v) for k, v in stack_params.iteritems() ]
    else:
        config['StackParams'] = []

    return (config, boto3.client('cloudformation'))

def deploy_lambda_code(config, args, cfn):
    print "Deploying Lambda code..."
    awsl = boto3.client('lambda')
    for func_name, func_def in config['LambdaFunctions'].iteritems():
        print "    Depoying code to logical function '%s'" % func_name
        res = cfn.describe_stack_resource(StackName=config['StackName'],
                                          LogicalResourceId=func_name)
        try:
            phys_id = res['StackResourceDetail']['PhysicalResourceId']
        except:
            print func_name
        tfile = tempfile.TemporaryFile(mode='w', dir='.')
        zfile = zipfile.ZipFile(tfile, 'w', zipfile.ZIP_DEFLATED)
        for code_file in func_def['CodeFiles']:
            zfile.write(code_file[0], code_file[1])
        zfile.close()
        bytes = open(tfile.name, 'r').read()
        resp = awsl.update_function_code(FunctionName=phys_id,
                                         ZipFile=bytes,
                                         Publish=func_def['Publish'])
        tfile.close()
        
        if 'Alias' in func_def:
            print "    Updating alias '%s'" % func_def['Alias']
            awsl.update_alias(FunctionName=phys_id,
                              Name=func_def['Alias'],
                              FunctionVersion=resp['Version'])

def custom_epilogue(Epilogue, Config):
    try:
        for svc in Epilogue['Service']:
            exec("%s = boto3.client('%s')" % (svc, svc))
        for c in Epilogue['Code']:
            exec(c.replace('{{STACKNAME}}', Config['StackName']))
        return True
    except Exception as e:
        print repr(e)
        return False

def epilogue(Config, Args, Cfn):
    # Deploy Lambda function code
    if 'LambdaFunctions' in Config:
        deploy_lambda_code(Config, Args, Cfn)
    
    if 'CustomEpilogue' in Config:
        print "Performing custom epilogue steps."
        for e in Config['CustomEpilogue']:
            print "   Performing step:", e['Name']
            if not custom_epilogue(e, Config):
                print "        ERROR!"

def template_kwargs(config):
    ret = {'StackName': config['StackName'],
           'Parameters': config['StackParams']}
    if 'StackOperationConfig' in config:
        soc = config['StackOperationConfig']
        if 'Capabilities' in soc:
            ret.update({'Capabilities': soc['Capabilities']})
    
    if 'S3Bucket' in config['TemplateContents']:
        bucket_name = None
        with open(config['TemplateContents']['S3Bucket'],'r') as fp:
            bucket_name = fp.read().strip()
        
        # The body is too large, so upload it as an S3 object, and deploy by URL.
        s3 = boto3.client('s3')
        s3_key = "%s.%d" % (config['StackName'], int(time.time()))
        s3.put_object(Bucket=bucket_name,
                      Key=s3_key,
                      Body=open(config['TemplateContents']['FileName'], 'r').read())
        ret.update({'TemplateURL': 'https://%s.amazonaws.com/%s/%s' % \
                    (s3_domain(s3),
                     bucket_name,
                     s3_key)})
    else:
        ret.update({'TemplateBody': open(config['TemplateContents']['FileName'], 'r').read()})
    
    return ret

# Periodically list the stack events, looking for CREATE_COMPLETE or UPDATE_COMPLETE.
# Since they are in reverse chronological order, it is always safe to just check the
# first batch. Look for LogicalResourceId matching the stack name exactly.
def wait_for_green_stack(stack_name, cfn, Timeout=300):
    start = time.time()
    while (time.time() - start) <= Timeout:
        sys.stdout.write('.')
        sys.stdout.flush()
        events = cfn.describe_stack_events(StackName=stack_name)
        if 'StackEvents' not in events or len(events['StackEvents']) == 0:
            print
            return False
        e = events['StackEvents'][0]
        if e['LogicalResourceId'] == stack_name:
            status = e['ResourceStatus']
            if status in [ 'CREATE_COMPLETE', 'UPDATE_COMPLETE' ]:
                print
                return True
            elif status in [ 'ROLLBACK_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE' ]:
                print
                return False
        time.sleep(5)
    print
    return False

def nop_stack(config, args, cfn):
    pass

def create_stack(config, args, cfn):
    # Create the stack with the stack name, template body file, parameters
    resp = cfn.create_stack(**template_kwargs(config))
    print json.dumps(resp, indent=4)

def update_stack(config, args, cfn):
    resp = cfn.update_stack(**template_kwargs(config))
    print json.dumps(resp, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
    Create or update a stack with appropriate static content in the S3 bucket and priming DynamoDB table items
    """)

    subparsers = parser.add_subparsers()
    nop_parser = subparsers.add_parser("no-stack-op", help="Perform only epilogue functions on an existing stack.")
    nop_parser.add_argument("--stack-name", default=None, required=True,
                            help="Stack name to update with new template, code, and static content.")
    nop_parser.set_defaults(stack_parameters=None)
    nop_parser.set_defaults(callback=nop_stack, subcommand="nop-stack")

    create_parser = subparsers.add_parser("create-stack", help="Create a new stack with an optional given stack name and parameters.")
    create_parser.add_argument("--stack-name", default=None, required=False,
                               help="Stack name to update with new template, code, and static content.")
    create_parser.add_argument("--stack-parameters", default=None, action=JSONArg,
                               help="Parameters for stack update/creation, given as a JSON dictionary of keys and string values. If a value is null, then the previous value is used.")
    create_parser.set_defaults(callback=create_stack, subcommand="create-stack")

    update_parser = subparsers.add_parser("update-stack", help="Update an existing stack, if possible, with a given name.")
    update_parser.add_argument("--stack-name", default=None, required=True,
                               help="Stack name to update with new template, code, and static content.")
    update_parser.add_argument("--stack-parameters", default=None, action=JSONArg,
                               help="Parameters for stack update/creation, given as a JSON dictionary of keys and string values. If a value is null, then the previous value is used.")
    update_parser.set_defaults(callback=update_stack, subcommand="update-stack")

    args = parser.parse_args()

    config, cfn = prologue(args)
    print "Stack name: %s" % config['StackName']

    print "Performing stack operation (%s)..." % args.subcommand
    args.callback(config, args, cfn)

    print "Waiting for stack to be green..."
    if wait_for_green_stack(config['StackName'], cfn):
        print "Performing epilogue..."
        epilogue(config, args, cfn)
    else:
        print "Stack never reached green state."
