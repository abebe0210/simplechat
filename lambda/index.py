import json
import os
import re
import urllib.request
import urllib.error

# FastAPIエンドポイントURLを環境変数から取得
FASTAPI_ENDPOINT_URL = "https://06a2-34-87-73-107.ngrok-free.app/generate"

def lambda_handler(event, context):
    if not FASTAPI_ENDPOINT_URL:
        print("Error: FASTAPI_ENDPOINT_URL environment variable is not set.")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": "FastAPI endpoint URL is not configured."
            })
        }

    try:
        print("Received event:", json.dumps(event))

        # Cognito認証情報
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', []) # フロントエンドから送られてくる形式

        print("Processing message:", message)
        print(f"Calling FastAPI endpoint: {FASTAPI_ENDPOINT_URL}")

        # FastAPIへのリクエストペイロードを作成
        # FastAPI側のInferenceRequestモデルに合わせる
        fastapi_payload = {
            "message": message,
            "conversationHistory": conversation_history # そのまま渡す
        }
        data = json.dumps(fastapi_payload).encode('utf-8')

        # FastAPIエンドポイントへPOSTリクエストを送信
        req = urllib.request.Request(
            FASTAPI_ENDPOINT_URL,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        try:
            with urllib.request.urlopen(req) as response:
                response_status = response.getcode()
                response_body_bytes = response.read()
                response_body_str = response_body_bytes.decode('utf-8')
                print(f"FastAPI response status: {response_status}")
                print(f"FastAPI response body: {response_body_str}")

                if response_status != 200:
                     raise Exception(f"FastAPI request failed with status {response_status}: {response_body_str}")

                # FastAPIからのレスポンスを解析 (FastAPI側のInferenceResponseモデルに合わせる)
                fastapi_response = json.loads(response_body_str)

                if not fastapi_response.get("success"):
                    error_message = fastapi_response.get("error", "Unknown error from FastAPI")
                    raise Exception(f"FastAPI inference failed: {error_message}")

                # 成功レスポンスの返却 (FastAPIのレスポンス構造に合わせる)
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                        "Access-Control-Allow-Methods": "OPTIONS,POST"
                    },
                    "body": json.dumps({
                        "success": True,
                        "response": fastapi_response.get("response"),
                        "conversationHistory": fastapi_response.get("conversationHistory")
                    })
                }

        except urllib.error.HTTPError as e:
            # HTTPエラーの場合、レスポンスボディも取得試行
            error_body = "No additional error body."
            try:
                error_body = e.read().decode('utf-8')
            except Exception:
                pass # 読めなくても無視
            print(f"HTTPError calling FastAPI: {e.code} - {e.reason}. Body: {error_body}")
            raise Exception(f"FastAPI request failed: {e.code} {e.reason}. {error_body}") from e
        except urllib.error.URLError as e:
            print(f"URLError calling FastAPI: {e.reason}")
            raise Exception(f"Could not connect to FastAPI endpoint: {e.reason}") from e

    except Exception as error:
        print("Error:", str(error))

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
