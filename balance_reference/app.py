import boto3
import json
import os

from botocore.exceptions import ClientError
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError
from boto3.dynamodb.conditions import Key, Attr

# import requests

line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])

dynamoDB = boto3.resource('dynamodb')
table = dynamoDB.Table(os.environ['BALANCE_TRANSACTION_TABLE'])

def lambda_handler(event, context):
    # print("Received event: " + json.dumps(event, indent=2))
    reply_token = event["replyToken"]

    sender_id = event["senderId"]
    space_id = event["spaceId"]
    space_type = event["spaceType"]
    is_summarize = event["isSum"]

    sender_name = get_lineuser_info(sender_id, space_id, space_type, 'display_name')
    if sender_name is None:
        return result_message(400, "sender name error")

    res = reference(sender_name, space_id, space_type, is_summarize)
    if (len(res) == 0):
        res = os.environ['NO_RESPONSE_MESSAGE']
    
    send_message(reply_token, res)

    return result_message(200, "ok")

def reference(sender, space_id, space_type, is_summarize):
    try:
        if space_type is None:
            response = table.query(
                KeyConditionExpression =\
                        Key('lender').eq('@' + sender) &\
                        Key('item').gte("あ"),
                FilterExpression=\
                        Attr('charge').ne(0)
            )
        else:
            response = table.query(
                KeyConditionExpression =\
                        Key('lender').eq('@' + sender) &\
                        Key('item').gte("あ"),
                FilterExpression=\
                        Attr('charge').ne(0) &\
                        Attr('space').eq(space_id)
            )

        if is_summarize:
            return summarize(response)

        return "\n".join(list(map(lambda x: x['borrower'] + ": " + str(x['charge']) + "(" + x['item'] + ")", response['Items'])))

    except ClientError as e:
        print(e.response['Error']['Message'])

def summarize(transaction_record):
    trans = dict()
    for record in transaction_record['Items']:
        if record['borrower'] in trans:
            trans[record['borrower']] += record['charge']
        else:
            trans[record['borrower']] = record['charge']

    res = ""
    for k, v in trans.items():
        res += k + ": " + str(v) + "\n"

    return res.rstrip("\n")

def result_message(code, msg):
    return {
        "statusCode": code,
        "body": json.dumps({
            "message": msg,
        }),
    }

def send_message(reply_token, messages):
    line_bot_api.reply_message(reply_token, TextSendMessage(text=messages))

    return

def get_lineuser_info(user_id, space_id, space_type, key):
    try:
        if space_type == "room":
            profile = line_bot_api.get_room_member_profile(space_id, user_id)
        elif space_type == "group":
            profile = line_bot_api.get_group_member_profile(space_id, user_id)
        else:
            profile = line_bot_api.get_profile(user_id)
    except LineBotApiError as e:
        return None

    return getattr(profile, key)

