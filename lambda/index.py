import json
import os
import re
import urllib.request
import urllib.error
from botocore.exceptions import ClientError

# Lambda コンテキストからリージョンを抽出する関数
def extract_region_from_arn(arn):
    # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"  # デフォルト値

API_ENDPOINT = os.environ.get("API_ENDPOINT", "https://3c46-34-125-224-8.ngrok-free.app/generate")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        
        # 会話履歴を使用
        messages = conversation_history.copy()
        
        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })
        
        # 外部FastAPIサービス用のリクエストペイロードを構築
        request_payload = {
            "prompt": message,
            "max_new_tokens": 512,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        # JSONデータをエンコード
        data = json.dumps(request_payload).encode('utf-8')
        
        print(f"Calling external API at {API_ENDPOINT} with payload:", json.dumps(request_payload))
        
        # リクエストオブジェクトの作成
        req = urllib.request.Request(API_ENDPOINT, data=data)
        
        # ヘッダーの設定
        req.add_header('Content-Type', 'application/json')
        req.add_header('Accept', 'application/json')
        
        try:
            # APIリクエストの送信と応答の取得
            with urllib.request.urlopen(req) as response:
                response_body = response.read().decode('utf-8')
                response_data = json.loads(response_body)
                print("API response:", json.dumps(response_data))
                
                # 生成されたテキストを取得
                generated_text = response_data.get("generated_text", "")
                
                # アシスタントの応答を会話履歴に追加
                messages.append({
                    "role": "assistant",
                    "content": generated_text
                })
                
                # 成功レスポンスの返却
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
                        "response": generated_text,
                        "conversationHistory": messages
                    })
                }
        except urllib.error.HTTPError as e:
            error_message = f"HTTP Error: {e.code}, {e.reason}"
            if hasattr(e, 'read'):
                error_body = e.read().decode('utf-8')
                error_message += f", Response: {error_body}"
            raise Exception(error_message)
        except urllib.error.URLError as e:
            raise Exception(f"URL Error: {str(e.reason)}")
        
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
