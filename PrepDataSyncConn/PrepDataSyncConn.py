import json, boto3, zipfile, os
l = boto3.client('codepipeline')
u = boto3.client('sts')
w = boto3.client('codecommit')
z = boto3.client('ec2')
Ac = os.environ['Ac']
Re = os.environ['Re']
p = {}
j = []
def eg(DSASGId, SGDSVe, VId, Peer, ec2):
    r = ec2.authorize_security_group_egress(GroupId=DSASGId,IpPermissions=[{'FromPort': 1024, 'IpProtocol': 'tcp', 'ToPort': 1064, 'UserIdGroupPairs': [{'GroupId': SGDSVe, 'UserId': Ac, 'PeeringStatus': 'active', 'VpcId': VId, 'VpcPeeringConnectionId': Peer}]}])
    return r
def ip(g):
    r = z.describe_network_interfaces(Filters=[{'Name':'group-id','Values':[g]}])
    a = [x['PrivateIpAddress'] for x in r['NetworkInterfaces'] if x['InterfaceType'] == 'vpc_endpoint']
    return str(a).strip('][').replace("'","")
def prep(bkt, i, v, b, n, m):
    for c, x in enumerate(i):
        if x != "None":
            d = "VAR"+str(c)+"=$(curl -s \"http://"+x+"/?gatewayType=SYNC&activationRegion=ap-southeast-1&privateLinkEndpoint="+v+"&endpointType=PRIVATE_LINK&no_redirect\")\n"
            e = "aws datasync create-agent --agent-name agent"+str(c)+" --vpc-endpoint-id "+b+" --subnet-arns arn:aws:ec2:"+Re+":"+Ac+":subnet/"+n+" --security-group-arns arn:aws:ec2:"+Re+":"+Ac+":security-group/"+m+" --activation-key $VAR"+str(c)+" --region "+Re+"\n"
            j.append(d)
            j.append(e)
    try:
        with open('/tmp/activate.sh', 'w') as f:
            f.write("#!/bin/bash\n")
            f.writelines(j)
        c = w.get_branch(repositoryName='DFIR2', branchName='main')
        with open('/tmp/activate.sh', 'rb') as h:
            r = w.put_file(repositoryName='DFIR2', branchName='main', fileContent=h.read(), filePath='activate.sh', parentCommitId=c['branch']['commitId'], fileMode='EXECUTABLE', commitMessage='Added activate.sh', name='PrepDataSyncConn', email='jasmchua@amazon.com')
    except Exception as err:
        return str(err)
def lambda_handler(event, context):
    Id = event['CodePipeline.job']['id']
    try:
        UP = event['CodePipeline.job']['data']['actionConfiguration']['configuration']['UserParameters']
        JL = json.loads(UP)
        for param in JL:
            p.update({param["name"]: param["value"]})
        i = [p.get(x) for x in p.keys() if x.startswith('DSAIP')]
        arn = 'arn:aws:iam::'+p['TA']+':role/MemberDFIRInvokerRole'
        n = u.assume_role(RoleArn=arn, RoleSessionName='MT')
        K = n['Credentials']['AccessKeyId']
        S = n['Credentials']['SecretAccessKey']
        T = n['Credentials']['SessionToken']
        ec2 = boto3.client('ec2', aws_access_key_id=K, aws_secret_access_key=S, aws_session_token=T)
        m = ec2.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [p['TVpcID']]}])
        try:
            ec2.create_route(DestinationCidrBlock=p['DR'], RouteTableId=m['RouteTables'][0]['RouteTableId'], VpcPeeringConnectionId=p['Pi'])
        except:
            print("RouteExists")
        if p['DSASGID2'] == "None":
            s = eg(p['DSASGID1'], p['SGDSVe'], p['VId'], p['Pi'], ec2)
        if p['DSASGID2'] != "None" and p['SGDSVe2'] != "None":
            s = eg(p['DSASGID1'], p['SGDSVe2'], p['VId'], p['Pi'], ec2)
            s = eg(p['DSASGID2'], p['SGDSVe2'], p['VId'], p['Pi'], ec2)
        if p['DSASGID3'] != "None" and p['SGDSVe3'] != "None":
            s = eg(p['DSASGID1'], p['SGDSVe3'], p['VId'], p['Pi'], ec2)
            s = eg(p['DSASGID2'], p['SGDSVe3'], p['VId'], p['Pi'], ec2)
            s = eg(p['DSASGID3'], p['SGDSVe3'], p['VId'], p['Pi'], ec2)
        if p['VeId'] != "None":
            r = ip(p['SGDSVe'])
            t = prep(p['Bkt'], i, r, p['VeId'], p['SN'], p['SGDSVe'])
        if p['Ve2Id'] != "None":
            r = ip(p['SGDSVe2'])
            t = prep(p['Bkt'], i, r, p['Ve2Id'], p['SN'], p['SGDSVe2'])
        if p['Ve3Id'] != "None":
            r = ip(p['SGDSVe3'])
            t = prep(p['Bkt'], i, r, p['Ve3Id'], p['SN'], p['SGDSVe3'])
        return l.put_job_success_result(jobId=Id, outputVariables=p)
    except Exception as e:
        return l.put_job_failure_result(jobId=Id, failureDetails={'type': 'JobFailed', 'message': str(e)})