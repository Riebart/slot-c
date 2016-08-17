This project is based on the [AWS Lambda zombie workshop](https://github.com/awslabs/aws-lambda-zombie-workshop) done at the AWS Loft in London, April 2016. It is heavily modified and extended, with much of the code completely rewritten, and a modern CloudFormation template included.

To deploy:

- Install and configure boto3 for your AWS account, ensure it has permissions to deploy Cloudformation stacks, including creating new IAM resources.
- Make sure that the value of the TemplateContents.S3Bucket parameter in deploy_config.json is the name of a file whose contents is the name of an existing S3 bucket for which you have write permissions.
  > It is done this way to prevent private information (bucket names, etc...) from being tracked in repositories.
- Once deployed, navigate to the HTTPS URL for the `index.html` in the S3 bucket created as part of the stack.
  > The URL will look something like: `https://<S3RegionURLPart>.amazonaws.com/<BucketName>/index.html`
  > For *us-east-1* (also called *US Standard*), the region part is `s3`, for all other regions, it is `s3-<region>`. [Ref](https://docs.aws.amazon.com/AmazonS3/latest/dev/UsingBucket.html)
  > To find the bucket name using the AWS cli:
  
  ```
  aws cloudformation describe-stack-resource --stack-name <StackName> --logical-resource-id StaticContentBucket --query StackResourceDetail.PhysicalResourceId
  ```

To create a new stack: 

```
python deploy.py create-stack
```

To update an existing stack:

```
python deploy.py update-stack --stack-name <StackName>
```

To explicitly only perform epilogue operations (Update Lamda code, push S3 files, etc...) even when a Cloudformation update is available, use `--epilogue-only`.
Note that when the `update-stack` operation is performed, and the stack requires no updates, the end result is approximately equivalent to `--epilogue-only`.

```
python deploy.py update-stack --stack-name <StackName> --epilogue-only
```
