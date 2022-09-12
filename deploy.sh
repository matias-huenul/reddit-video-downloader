#! /bin/bash

RED="\e[31m"
GREEN="\e[32m"
ENDCOLOR="\e[0m"

check_status() {
    if [[ $? != 0 ]]; then
        echo -e " [${RED}FAILED${ENDCOLOR}]"
        exit 1
    fi
    echo -e " [${GREEN}OK${ENDCOLOR}]"
}

STACK_NAME="reddit-video-downloader"
TEMPLATE="template.yaml"
TEMPLATE_PACKAGED="template-packaged.yaml"
API_GATEWAY_STAGE="dev"
S3_ARTIFACTS_BUCKET="cloudformation-stacks-$AWS_ACCOUNT_ID-$AWS_REGION"

echo -n "Creating deployment package for lambda-caller..."

rm -rf package
mkdir package
cp -r src/lambda-caller/* package
cd package
zip -r ../lambda-caller-package.zip . 2>&1 >/dev/null
check_status

cd ..
echo -n "Creating deployment package for lambda-downloader..."

rm -rf package
mkdir package
cp -r src/lambda-downloader/* package
cd package
zip -r ../lambda-downloader-package.zip . 2>&1 >/dev/null
check_status

cd ..
rm -rf package

echo -n "Creating cloudformation packaged template..."

aws cloudformation package \
    --template-file $TEMPLATE \
    --s3-bucket $S3_ARTIFACTS_BUCKET \
    --s3-prefix $STACK_NAME \
    --output-template-file $TEMPLATE_PACKAGED \
    --region $AWS_REGION 2>&1 >/dev/null

check_status

echo -n "Deploying stack..."

aws cloudformation deploy \
    --stack-name $STACK_NAME \
    --template-file $TEMPLATE_PACKAGED \
    --parameter-overrides pTelegramAPIToken=$TELEGRAM_API_TOKEN \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $AWS_REGION 2>&1 >/dev/null

check_status

rm lambda-caller-package.zip
rm lambda-downloader-package.zip
rm $TEMPLATE_PACKAGED

echo -n "Deploying API..."

REST_API_ID=$(aws cloudformation describe-stack-resource \
    --stack-name $STACK_NAME \
    --logical-resource-id rApiGatewayRest \
    --region $AWS_REGION | jq -r '.["StackResourceDetail"]["PhysicalResourceId"]')

aws apigateway create-deployment \
    --rest-api-id $REST_API_ID \
    --stage-name $API_GATEWAY_STAGE \
    --region $AWS_REGION 2>&1 >/dev/null

check_status

echo -n "Setting webhook... "

API_GATEWAY_URL="https://$REST_API_ID.execute-api.$AWS_REGION.amazonaws.com/$API_GATEWAY_STAGE"

curl -s --request POST \
    --header "Content-Type: application/json" \
    --data "{\"url\": \"$API_GATEWAY_URL\"}" \
    "https://api.telegram.org/bot$TELEGRAM_API_TOKEN/setWebhook" >/dev/null

check_status
