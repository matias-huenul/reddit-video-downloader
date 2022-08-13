import boto3
import json

def lambda_handler(event, context):
    try:
        client = boto3.client("lambda", region_name="us-east-1")
        response = client.invoke(
            FunctionName="lambda-reddit-video-downloader",
            InvocationType="Event",
            Payload=bytes(event["body"], encoding="utf-8")
        )
        print(event["body"])
    except:
        pass
    finally:
        return { "statusCode": 200 }

if __name__ == "__main__":
    import sys
    chat_id = sys.argv[1]
    text = sys.argv[2]
    lambda_handler(
        {
            "message": {
                "chat": {
                    "id": chat_id
                },
                "text": text
            }
        },
        None
    )
