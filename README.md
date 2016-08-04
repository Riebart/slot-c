This project is based on the [AWS Lambda zombie workshop](https://github.com/awslabs/aws-lambda-zombie-workshop) done at the AWS Loft in London, April 2016. It is heavily modified and extended, with much of the code completely rewritten, and a modern CloudFormation template included.

To deploy:

- Install and configure boto3 for your AWS account, ensure it has permissions to deploy Cloudformation stacks, including creating new IAM resources.
- Make sure that the value of the TemplateContents.S3Bucket parameter in deploy_config.json is the name of a file whose contents is the name of an existing S3 bucket for which you have write permissions.
  > It is done this way to prevent private information (bucket names, etc...) from being tracked in repositories.

To create a new stack: 

```
python deploy.py create-stack
```

To update an existing stack:

```
python deploy.py update-stack --stack-name <StackName>
```

To only perform epilogue operations (Update Lamda code, push S3 files, etc...):

```
python deploy.py no-stack-op --stack-name <StackName>
```
