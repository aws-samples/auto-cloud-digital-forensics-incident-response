import json
import boto3

lambda_client = boto3.client('lambda')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    myinput = event['detail']['resources'][0]['ARN']
    key = myinput.split('/')[1]
    bucket = myinput.split('/')[0].split(':::')[1]
    tempfile = '/tmp/' + key
    s3.download_file(bucket, key, tempfile)
    mapping = {}
    targets = []
    with open(tempfile) as f:
        for line in f:
            mapping['AccountId'] = line.split('=')[0]
            mapping['InstanceIds'] = line.split('=')[1].strip()
            targets.append(mapping)
            mapping = {}

    for target in targets:
        targetdata = {"ARN": "arn:aws:iam::" + target['AccountId'] + ":role/MemberDFIRInvokerRole", "InstanceIds": target['InstanceIds']}
        response = lambda_client.invoke(FunctionName="StartDFIRChild", InvocationType="Event", Payload=json.dumps(targetdata))
        print(response)