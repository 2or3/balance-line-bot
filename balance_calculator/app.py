import boto3
import json
import os

from botocore.exceptions import ClientError
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError
from boto3.dynamodb.conditions import Key, Attr

# import requests

line_bot_api = LineBotApi(os.environ["LINE_CHANNEL_ACCESS_TOKEN"])

dynamoDB = boto3.resource("dynamodb")
table = dynamoDB.Table(os.environ["BALANCE_TRANSACTION_TABLE"])


def insert(s, space_id, records):
    if len(records) == 0:
        return False

    for k, v in records.items():
        c, i = v.split()

        try:
            response = table.query(
                KeyConditionExpression=Key("lender").eq("@" + s) & Key("item").eq(i),
                FilterExpression=Attr("borrower").eq(k) & Attr("space").eq(space_id),
            )
        except ClientError as e:
            print(e.response["Error"]["Message"])

        if len(response["Items"]) > 0:
            current_charge = response["Items"][0]["charge"]
        else:
            current_charge = 0

        table.put_item(
            Item={
                "lender": "@" + s,
                "item": i,
                "space": space_id,
                "borrower": k,
                "charge": int(c) + current_charge,
            }
        )

        table.put_item(
            Item={
                "lender": k,
                "item": i,
                "space": space_id,
                "borrower": "@" + s,
                "charge": -1 * (int(c) + current_charge),
            }
        )

    return True


def lambda_handler(event, context):
    # print("Received event: " + json.dumps(event, indent=2))
    reply_token = event["replyToken"]
    trans = event["trans"]

    sender_id = event["senderId"]
    space_id = event["spaceId"]
    space_type = event["spaceType"]

    if space_type is None:
        return result_message(400, "Cannot accept request from direct message.")

    sender_name = get_lineuser_info(sender_id, space_id, space_type, "display_name")
    if sender_name is None:
        return result_message(400, "sender name error")

    if insert(sender_name, space_id, trans):
        send_message(reply_token, os.environ["RESPONSE_MESSAGE"])

    return result_message(200, "ok")


def result_message(code, msg):
    return {
        "statusCode": code,
        "body": json.dumps(
            {
                "message": msg,
            }
        ),
    }


def send_message(reply_token, messages):
    line_bot_api.reply_message(reply_token, TextSendMessage(text=messages))

    return


def get_lineuser_info(user_id, space_id, space_type, key):
    try:
        if space_type == "room":
            profile = line_bot_api.get_room_member_profile(space_id, user_id)
        else:
            profile = line_bot_api.get_group_member_profile(space_id, user_id)
    except LineBotApiError as e:
        return None

    return getattr(profile, key)
