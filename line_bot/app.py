import boto3
import json
import base64
import hashlib
import hmac
import os
import re

def lambda_handler(event, context):
    # print("Received event: " + json.dumps(event, indent=2))
    try:
        channel_secret = os.environ['CHANNEL_SECRET']
        body = event['body']
        # print("Received body: " + json.dumps(body, indent=2))
        hash = hmac.new(channel_secret.encode('utf-8'),
                    body.encode('utf-8'), hashlib.sha256).digest()
        signature = base64.b64encode(hash)
        line_signature = event['multiValueHeaders']['X-Line-Signature'][0].encode(encoding='utf-8')

        if signature != line_signature:
            return result_message(400, "signature error")
    except:
        print("requestError")
        return result_message(400, "request error")

    body_event = json.loads(body)['events'][0]
    return check_message(body_event)

def result_message(code, msg):
    return {
        "statusCode": code,
        "body": json.dumps({
            "message": msg,
        }),
    }

def check_message(item):
    reply_token = item['replyToken']

    user_id = item['source']['userId']

    space_id = None
    space_type = None
    if 'roomId' in item['source']:
        space_id = item['source']['roomId']
        space_type = "room"

    group_id = None
    if 'groupId' in item['source']:
        space_id = item['source']['groupId']
        space_type = "group"

    messages = item['message']['text']
    dic = is_store_message(messages)
    if (dic != False):
        input_event = {
            "replyToken": reply_token,
            "senderId": user_id,
            "spaceId": space_id,
            "spaceType": space_type,
            "groupId": group_id,
            "trans": dic
        }
        payload = json.dumps(input_event)
        return invoke_lambda('BALANCE_CALCULATOR_FUNCTION_ARN', payload)

    is_sum = None
    if (is_reference_message(messages)):
        is_sum = True

    if (is_reference_detail_message(messages)):
        is_sum = False

    if not is_sum is None:
        input_event = {
            "replyToken": reply_token,
            "senderId": user_id,
            "spaceId": space_id,
            "spaceType": space_type,
            "isSum": is_sum
        }
        payload = json.dumps(input_event)
        return invoke_lambda('BALANCE_REFELENCE_FUNCTION_ARN', payload)

    return result_message(400, "request error")

def invoke_lambda(func_arn, payload):
    function_name = os.environ[func_arn].split(":")[-1]
    response = boto3.client('lambda').invoke(
        FunctionName=function_name,
        InvocationType='Event',
        Payload=payload
    )

    return response['Payload'].read()

def is_store_message(messages):
    reg_tran = re.compile(r'@\w+')
    is_mentioned = reg_tran.findall(messages)
    if (not is_mentioned):
        return False

    reg_tran = re.compile(r'[-+]?[,0-9]+ \w+')
    tran = reg_tran.findall(messages)
    
    dic = {key: val for key, val in zip(is_mentioned, tran)}

    return dic

def is_reference_message(messages):
    reg_reference = re.compile(r'^' + os.environ['REFERENCE_MESSAGE'] + '$')
    is_reference = reg_reference.match(messages)
    if (not is_reference):
        return False

    return True

def is_reference_detail_message(messages):
    reg_reference = re.compile(r'^' + os.environ['REFERENCE_DETAIL_MESSAGE'] + '$')
    is_reference = reg_reference.match(messages)
    if (not is_reference):
        return False

    return True

