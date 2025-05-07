import json
import urllib.request
import urllib.error
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

# FastAPI アプリケーションの初期化
app = FastAPI()

# 外部APIのエンドポイントURL（適宜変更してください）
API_URL = "https://06a2-34-87-73-107.ngrok-free.app/generate"

# リクエストボディのスキーマ定義
class MessageRequest(BaseModel):
    message: str
    conversationHistory: list = []

# レスポンスボディのスキーマ定義
class MessageResponse(BaseModel):
    success: bool
    response: str
    conversationHistory: list

@app.post("/generate", response_model=MessageResponse)
async def generate_message(request: MessageRequest):
    try:
        # リクエストデータの取得
        message = request.message
        conversation_history = request.conversationHistory

        # 会話履歴を使用してリクエストペイロードを構築
        messages = conversation_history.copy()
        messages.append({"role": "user", "content": message})

        # 外部API用のリクエストペイロード
        payload = {
            "prompt": message,
            "max_new_tokens": 200,
            "do_sample": True,
            "temperature": 0.8,
            "top_p": 0.9
        }
        
        # JSONデータをエンコード
        data = json.dumps(payload).encode('utf-8')
        
        # リクエストオブジェクトの作成
        req = urllib.request.Request(API_URL, data=data)
        
        # ヘッダーの設定
        req.add_header('Content-Type', 'application/json')
        req.add_header('Accept', 'application/json')
        
        # APIリクエストの送信と応答の取得
        try:
            with urllib.request.urlopen(req) as response:
                # レスポンスの読み取り
                response_data = response.read().decode('utf-8')
                result = json.loads(response_data)
                
                # 生成されたテキストを取得
                generated_text = result.get("generated_text", "")
                
                # アシスタントの応答を会話履歴に追加
                messages.append({"role": "assistant", "content": generated_text})
                
                # 成功レスポンスを返却
                return MessageResponse(
                    success=True,
                    response=generated_text,
                    conversationHistory=messages
                )
        except urllib.error.HTTPError as e:
            # HTTP エラーの場合
            error_message = f"HTTPエラー: {e.code}, {e.reason}"
            if hasattr(e, 'read'):
                error_body = e.read().decode('utf-8')
                error_message += f", レスポンス: {error_body}"
            raise HTTPException(status_code=e.code, detail=error_message)
        except urllib.error.URLError as e:
            # URL エラーの場合
            raise HTTPException(status_code=500, detail=f"URLエラー: {str(e.reason)}")

    except Exception as error:
        # その他のエラーの場合
        raise HTTPException(status_code=500, detail=str(error))
