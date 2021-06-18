import json
import boto3
import os

sts_client = boto3.client('sts')
s3 = boto3.client('s3')
codecommit_dfir = boto3.client('codecommit')

targets = []
uniquesubnetinaz = {}
efsmounttargets = []
azs = []
vpcs = []
to_peer_vpcs = {}
acceptervpcs = []
peering = False
buildParams = {}
buildParams['Parameters'] = {}
perTarget = []

def lambda_handler(event, context):
    arn = event['ARN']
    targets = event['InstanceIds'].split(",")
    targetacctid = arn.split(':')[4]
    mysession = sts_client.assume_role(RoleArn=arn, RoleSessionName='StartDFIRChild_Session')
    
    ACCESS_KEY = mysession['Credentials']['AccessKeyId']
    SECRET_KEY = mysession['Credentials']['SecretAccessKey']
    SESSION_TOKEN = mysession['Credentials']['SessionToken']
    
    ec2 = boto3.client('ec2', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, aws_session_token=SESSION_TOKEN)
    codecommit = boto3.client('codecommit', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, aws_session_token=SESSION_TOKEN)
    ssm = boto3.client('ssm', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, aws_session_token=SESSION_TOKEN)
    
    DFIRaccount = os.environ['DFIRAccountId']
    triagebucket = os.environ['SecurityTriageBucketName']
    DFIRCodeRepo = os.environ['DFIRCodeRepo']
    ec2response = ec2.describe_instances(InstanceIds=targets)
        
    for n in range(len(ec2response['Reservations'])):
        global uniquesubnetinaz
        if ec2response['Reservations'][n]['Instances'][0]['VpcId'] not in vpcs:
            vpcs.append(ec2response['Reservations'][n]['Instances'][0]['VpcId'])
        if ec2response['Reservations'][n]['Instances'][0]['Placement']['AvailabilityZone'] not in azs:
            uniquesubnetinaz['VpcId'] = ec2response['Reservations'][n]['Instances'][0]['VpcId'] 
            uniquesubnetinaz['SubnetId'] = ec2response['Reservations'][n]['Instances'][0]['SubnetId']
            uniquesubnetinaz['SecurityGroupId'] = ec2response['Reservations'][n]['Instances'][0]['SecurityGroups'][0]['GroupId']
            uniquesubnetinaz['AvailabilityZone'] = ec2response['Reservations'][n]['Instances'][0]['Placement']['AvailabilityZone']
            efsmounttargets.append(uniquesubnetinaz)
            azs.append(ec2response['Reservations'][n]['Instances'][0]['Placement']['AvailabilityZone'])
            uniquesubnetinaz = {}
    for c, p in enumerate(efsmounttargets, start=1):
        perTarget.append({'DFIRAccountId': DFIRaccount, 'VpcId'+str(c): p['VpcId'], 'TargetSecurityGroup'+str(c): p['SecurityGroupId'], 'SubnetId'+str(c): p['SubnetId'], 'AvailabilityZone'+str(c): p['AvailabilityZone']})

    for x in perTarget:
        buildParams['Parameters'].update(x)

    ssmresponse = ssm.get_parameter(Name='/aws/service/datasync/ami')
    buildParams['Parameters'].update({'DataSyncAMIID': ssmresponse['Parameter']['Value']})


    for vpc in vpcs:
        global to_peer_vpcs
        global peering
        peeringresponse = ec2.describe_vpc_peering_connections(Filters=[{'Name':'accepter-vpc-info.vpc-id','Values':[vpc]},{'Name':'requester-vpc-info.owner-id','Values':[DFIRaccount]}])
        for response in peeringresponse['VpcPeeringConnections']:
            if response['Status']['Code'] == 'active':
                print("Peering Connection ID: "+response['VpcPeeringConnectionId'])
                to_peer_vpcs['ExistingPeer'] = response['VpcPeeringConnectionId']
                peering = True
            elif response['Status']['Code'] == 'pending-acceptance':
                try:
                    acceptresponse = ec2.accept_vpc_peering_connection(VpcPeeringConnectionId=peeringresponse['VpcPeeringConnections'][0]['VpcPeeringConnectionId'])
                    print("Accept VPC peering now.\n")
                    to_peer_vpcs['ExistingPeer'] = acceptresponse['VpcPeeringConnection']['VpcPeeringConnectionId']
                    peering = True
                except:
                    print("Something went wrong with VPC peering!\n")
                    print(acceptresponse)
        if peering == False:
            buildParams['Parameters'].update({'PeerRoleRequired': 'True'})          
        vpcinfo = ec2.describe_vpcs(VpcIds=[vpc])
        to_peer_vpcs['AccepterVPCId'] = vpcinfo['Vpcs'][0]['VpcId']
        to_peer_vpcs['AccepterCIDR'] = vpcinfo['Vpcs'][0]['CidrBlock']
        to_peer_vpcs['TargetAccountId'] = targetacctid
        to_peer_vpcs['ExistingPeer'] = 'None'
        acceptervpcs.append(to_peer_vpcs)
        to_peer_vpcs = {}
        notes = json.dumps(acceptervpcs)
        s3response = s3.put_object(Body=notes, Bucket=triagebucket, Key='PeerInfo.txt', ServerSideEncryption='AES256')

    cc2 = codecommit.get_branch(repositoryName='TargetStore', branchName='main')
    lastcommitID2 = cc2['branch']['commitId']        
    parametercontents = json.dumps(buildParams)
    putf2 = codecommit.put_file(repositoryName='TargetStore', branchName='main', fileContent=parametercontents, filePath='TargetParameters.json', parentCommitId=lastcommitID2, fileMode='NORMAL', commitMessage='Added Target Parameters file', name='StartDFIRChild', email='jasmchua@amazon.com')
    print(putf2)