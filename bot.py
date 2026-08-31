import botpy
from botpy.message import Message
import httpx
import asyncio
import uvicorn
from fastapi import FastAPI

SCR_GROUP_ID = 3620943

# 1. 建立一個極簡的網頁伺服器，讓 Render 認定這是個 Web 服務
app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "Bot is running!"}

# 2. 定義 QQ 機器人邏輯
class MyClient(botpy.Client):
    async def on_group_at_message_create(self, message: Message):
        content = message.content.strip()
        
        if "/ranklookup" in content:
            args = content.replace("/ranklookup", "").strip()
            
            if not args:
                await message.reply(content="Error: Please provide a Roblox username. Example: /ranklookup Builderman")
                return
            
            try:
                async with httpx.AsyncClient() as client:
                    payload = {"usernames": [args], "excludeBannedUsers": False}
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Content-Type": "application/json"
                    }
                    
                    res = await client.post(
                        "https://users.roblox.com/v1/usernames/users", 
                        json=payload, 
                        headers=headers,
                        timeout=10.0
                    )
                    
                    data = res.json()
                    
                    if not data.get("data"):
                        await message.reply(content=f"Error: Player {args} not found.")
                        return
                        
                    user_id = data["data"][0]["id"]
                    display_name = data["data"][0]["displayName"]
                    
                    group_res = await client.get(
                        f"https://groups.roblox.com/v2/users/{user_id}/groups/roles",
                        headers=headers,
                        timeout=10.0
                    )
                    group_data = group_res.json()
                    
                    role_name = "Not in group"
                    if "data" in group_data:
                        for group_info in group_data["data"]:
                            if group_info["group"]["id"] == SCR_GROUP_ID:
                                role_name = group_info["role"]["name"]
                                break
                    
                    reply = (f"Username: {args}\n"
                             f"DisplayName: {display_name}\n"
                             f"UserID: {user_id}\n"
                             f"Group Role: {role_name}")
                             
                    await message.reply(content=reply)
                    
            except Exception as e:
                await message.reply(content=f"Error fetching data: {str(e)}")

# 3. 同時啟動網頁伺服器與 QQ 機器人
async def main():
    # 啟動 FastAPI 網頁服務 (監聽 Render 給的 PORT)
    config = uvicorn.Config(app, host="0.0.0.0", port=10000, log_level="info")
    server = uvicorn.Server(config)
    
    intents = botpy.Intents.default()
    client = MyClient(intents=intents)
    
    # 並行運行網頁服務與機器人
    await asyncio.gather(
        server.serve(),
        client.start(appid="1905533434", secret="HkDhBgCiFmKsR1bCnP2fJxcHxeL3lUEy")
    )

if __name__ == "__main__":
    asyncio.run(main())
