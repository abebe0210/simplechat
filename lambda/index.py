import json
import os
import re
import urllib.request
import urllib.error


# Lambda コンテキストからリージョンを抽出する関数 (FastAPI呼び出しでは不要になる可能性あり)
# def extract_region_from_arn(arn):
#     # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
#     match = re.search('arn:aws:lambda:([^:]+):', arn)
#     if match:
#         return match.group(1)
#     return "us-east-1"  # デフォルト値

# グローバル変数としてクライアントを初期化（初期値） - 不要
# bedrock_client = None

# モデルID - 不要
# MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")

# FastAPIエンドポイントURLを環境変数から取得
FASTAPI_ENDPOINT_URL = os.environ.get("FASTAPI_ENDPOINT_URL")

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
        # Bedrockクライアント初期化は不要
        # global bedrock_client
        # if bedrock_client is None:
        #     region = extract_region_from_arn(context.invoked_function_arn)
        #     bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        #     print(f"Initialized Bedrock client in region: {region}")

        print("Received event:", json.dumps(event))

        # Cognito認証情報はそのまま利用可能
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


        # --- Bedrock呼び出し部分は削除 ---
        # print("Calling Bedrock invoke_model API with payload:", json.dumps(request_payload))
        # response = bedrock_client.invoke_model(...)
        # response_body = json.loads(response['body'].read())
        # ... (以降のBedrock関連処理も削除) ...

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
