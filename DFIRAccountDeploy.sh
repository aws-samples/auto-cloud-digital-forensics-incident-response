#!/bin/bash

read -p 'Specify a new S3 Build Bucket Name for dumping large sized Lambda code: ' BUILDBUCKETNAME
read -p 'Specify the AWS REGION that you are deploying to: ' REGION
read -p 'Specify your DFIR Account Number: ' DFIRACCOUNTID
read -p 'Specify your Organization ID: ' ORGID
read -p 'Specify a new Security Triage Bucket Name: ' SECURITYTRIAGEBUCKETNAME
read -p 'Specify the Email address of your Security Team: ' EMAILADDRESS

echo -e "Publish Lambda cfnresponse module layer...\n"
LAYERVERSIONARN=`aws lambda publish-layer-version --layer-name cfnresponse_lib --zip-file fileb://CFNResponse.zip --compatible-runtimes python3.8 --query 'LayerVersionArn'`
VERSION=`echo $LAYERVERSIONARN | cut -d ":" -f 8 | sed -e 's/"$//'`
echo -e "Sharing Lambda cfnresponse module layer with Organization...\n"
aws lambda add-layer-version-permission --layer-name cfnresponse_lib --version-number $VERSION --statement-id ShareLayerWOrg --principal '*' --organization-id $ORGID --action lambda:GetLayerVersion --region $REGION
echo -e "Create S3 bucket $BUILDBUCKETNAME to dump large sized lambda functions code...\n"
echo -e "{\"Parameters\": {\"LambdaCodeBucketName\": \"$BUILDBUCKETNAME\", \"OrganizationID\": \"$ORGID\"}}" > LambdaBucketParameters.json
aws cloudformation deploy --template-file DFIRLambdaBucket.yaml --stack-name DFIRLambdaBucket --parameter-overrides file://LambdaBucketParameters.json --capabilities CAPABILITY_IAM

aws cloudformation package --template-file DFIRResources.yaml --s3-bucket $BUILDBUCKETNAME --output-template-file DFIRResourcesOut.yaml

aws cloudformation package --template-file MemberResources.yaml --s3-bucket $BUILDBUCKETNAME --output-template-file MemberResourcesOut.yaml
echo -e "Generated MemberResourcesOut.yaml ready for you to deploy as a StackSet...\n"

echo -e "Copy relevant template files to $BUILDBUCKETNAME in preparation for DFIR...\n"
if [ -d "builddfir" ];
then
    aws s3 sync builddfir s3://$BUILDBUCKETNAME
fi
echo -e "{\"Parameters\": {\"DFIRAccountId\": \"$DFIRACCOUNTID\", \"OrganizationID\": \"$ORGID\", \"SecurityTriageBucketName\": \"$SECURITYTRIAGEBUCKETNAME\", \"SecurityEmailAddress\": \"$EMAILADDRESS\", \"LayerVersionARN\": $LAYERVERSIONARN, \"BuildDFIRBucketName\": \"$BUILDBUCKETNAME\"}}" > SecurityParameters.json
echo -e "Deploy DFIRResources stack into DFIR account...\n"
aws cloudformation deploy --template-file DFIRResourcesOut.yaml --stack-name DFIRResources --parameter-overrides file://SecurityParameters.json --capabilities CAPABILITY_NAMED_IAM

# Perhaps to automate this step below in the future - to deploy as stack with parameters taken from the output of above DFIRResources stack deployment.
aws cloudformation package --template-file BuildDFIRPipeline.yaml --s3-bucket $BUILDBUCKETNAME --output-template-file BuildDFIRPipelineOut.yaml
echo -e "Generated BuildDFIRPipelineOut.yaml ready for you to deploy as a Stack...\n"

