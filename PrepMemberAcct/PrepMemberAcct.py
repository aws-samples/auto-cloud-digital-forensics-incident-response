import json
import boto3
import os
code_pipeline = boto3.client('codepipeline')
s3 = boto3.client('s3')
ec2 = boto3.client('ec2')
sts_client = boto3.client('sts')
AId = os.environ['MemberAcct']
BKTARN = os.environ['TriageBucketArn']
ARN = os.environ['Role']
Rep = os.environ['DFIRRepo']
SB = os.environ['DFIRSubnetId']
VP = os.environ['DFIRVpcId']
CR = os.environ['DFIRCIDRRange']
RT = os.environ['DFIRRouteTbId']
Oct = ['192','172','10']
params = {}
p = {}
def put_result(params, jobId, tb):
    try:
        my = sts_client.assume_role(RoleArn=ARN, RoleSessionName='PMA'+AId)
        AY = my['Credentials']['AccessKeyId']
        SY = my['Credentials']['SecretAccessKey']
        SN = my['Credentials']['SessionToken']
        cc = boto3.client('codecommit', aws_access_key_id=AY, aws_secret_access_key=SY, aws_session_token=SN)
        re = cc.get_branch(repositoryName=Rep, branchName='main')
        co = re['branch']['commitId']    
        params.update({'TriageBucketName': tb})
        p['Parameters'] = params
        resultjson = json.dumps(p)
        r = cc.put_file(repositoryName=Rep, branchName='main', fileContent=resultjson, filePath='BuildDFIRParameters.json', parentCommitId=co, fileMode='NORMAL', commitMessage='Added BuildDFIRParameters', name='PrepMemberAcct', email='jasmchua@amazon.com')
        return r
    except Exception as err:
        return code_pipeline.put_job_failure_result(jobId=jobId, failureDetails={'type': 'JobFailed', 'message': str(err)})
def lambda_handler(event, context):
    tb = BKTARN.split(':')[5]
    jobId = event['CodePipeline.job']['id']
    try:
        UP = event['CodePipeline.job']['data']['actionConfiguration']['configuration']['UserParameters']
        UPL = json.loads(UP)
        for i in UPL:
            params.update({i["name"]: i["value"]})
        if params['SGIdEMT1']:
            try:     
                ec2.authorize_security_group_ingress(GroupId=params['SGIdEMT1'], IpPermissions=[{'FromPort': 2049, 'IpProtocol': 'tcp', 'ToPort': 2049, 'UserIdGroupPairs': [{'Description': 'Allow datasync agent inbound', 'GroupId': params['DSASGId1'], 'UserId': AId}]}])
            except:
                print("Security Group to allow datasync agent inbound to EFS Mount Target already exists.")
        del params['SGIdEMT1']
        if params['SGIdEMT2'] != "None":
            try:
                ec2.authorize_security_group_ingress(GroupId=params['SGIdEMT2'], IpPermissions=[{'FromPort': 2049, 'IpProtocol': 'tcp', 'ToPort': 2049, 'UserIdGroupPairs': [{'Description': 'Allow datasync agent inbound', 'GroupId': params['DSASGId2'], 'UserId': AId}]}])
            except:
                print("Security Group to allow datasync agent inbound to EFS Mount Target already exists.")
        del params['SGIdEMT2']
        if params['SGIdEMT3'] != "None":
            try:
                ec2.authorize_security_group_ingress(GroupId=params['SGIdEMT3'], IpPermissions=[{'FromPort': 2049, 'IpProtocol': 'tcp', 'ToPort': 2049, 'UserIdGroupPairs': [{'Description': 'Allow datasync agent inbound', 'GroupId': params['DSASGId3'], 'UserId': AId}]}])
            except:
                print("Security Group to allow datasync agent inbound to EFS Mount Target already exists.")
        del params['SGIdEMT3']
        tempf = '/tmp/' + 'PeerInfo.txt'
        s3.download_file(tb, 'PeerInfo.txt', tempf)
        with open(tempf) as f:
            tx = f.read()
        acceptervpcs = json.loads(tx)
        for a in acceptervpcs:
            params['TargetAcctId'] = a['TargetAccountId']
            params['TargetVpcId'] = a['AccepterVPCId']
            params['TargetCIDRRange'] = a['AccepterCIDR']
            params['ExistingPeerId'] = a['ExistingPeer']
            if params['VPRoleARN'] != "None" and CR == "None":
                f = a['AccepterCIDR'].split('.')[0]
                if f in Oct:
                    Oct.remove(f)
                if Oct[0] == '192':
                    params['DFIRCIDRRange'] = '192.168.0.0/16'
                    params['DFIRSubnetInfo'] = '192.168.1.0/24'
                elif Oct[0] == '172':
                    params['DFIRCIDRRange'] = '172.31.0.0/16'
                    params['DFIRSubnetInfo'] = '172.31.1.0/24'
                else:
                    params['DFIRCIDRRange'] = '10.0.0.0/16'
                    params['DFIRSubnetInfo'] = '10.0.1.0/24'
            if params['VPRoleARN'] != "None" and CR != "None":
                f = a['AccepterCIDR'].split('.')[0]
                if f in Oct:
                    Oct.remove(f)
                e = CR.split('.')[0]
                if e in Oct:
                    Oct.remove(e)
                if Oct[0] == '192':
                    params['DFIRCIDRRange'] = '192.168.0.0/16'
                    params['DFIRSubnetInfo'] = '192.168.1.0/24'
                elif Oct[0] == '172':
                    params['DFIRCIDRRange'] = '172.31.0.0/16'
                    params['DFIRSubnetInfo'] = '172.31.1.0/24'
                else:
                    params['DFIRCIDRRange'] = '10.0.0.0/16'
                    params['DFIRSubnetInfo'] = '10.0.1.0/24'                          
            if params['VPRoleARN'] == "None":
                params['DFIRVPCId'] = VP
                params['DFIRSubnetId'] = SB
                params['DFIRRouteTbId'] = RT
                params['DFIRCIDRRange'] = CR
        put_result(params, jobId, tb)
        return code_pipeline.put_job_success_result(jobId=jobId, outputVariables=params)
    except Exception as err:
        return code_pipeline.put_job_failure_result(jobId=jobId, failureDetails={'type': 'JobFailed', 'message': str(err)})