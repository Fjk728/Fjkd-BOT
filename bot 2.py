import botpy
from botpy.message import Message
import httpx
import asyncio
import uvicorn
from fastapi import FastAPI

SCR_GROUP_ID = 3620943

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "Bot is running!"}

class MyClient(botpy.Client):
    async def on_group_at_message_create(self, message: Message):
        content = message.content.strip()
        
        # 指令改為 /view
        if "/view" in content:
            args = content.replace("/view", "").strip()
            
            if not args:
                await message.reply(content="Error: Please provide a Roblox username. Example: /view Builderman")
                return
            
            try:
                async with httpx.AsyncClient() as client:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Content-Type": "application/json"
                    }
                    
                    # 1. 獲取 UserID 與基本資料
                    payload = {"usernames": [args], "excludeBannedUsers": False}
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
                    
                    # 2. 獲取群組職位 (SCR Group)
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
                    
                    # 3. 獲取註冊時間
                    user_detail_res = await client.get(
                        f"https://users.roblox.com/v1/users/{user_id}",
                        headers=headers,
                        timeout=10.0
                    )
                    user_detail_data = user_detail_res.json()
                    created_at = user_detail_data.get("created", "未知").split("T")[0]
                    
                    # 4. 獲取玩家大頭貼 (420x420 Png)
                    thumb_res = await client.get(
                        f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png",
                        headers=headers,
                        timeout=10.0
                    )
                    thumb_data = thumb_res.json()
                    avatar_url = ""
                    if thumb_data.get("data") and len(thumb_data["data"]) > 0:
                        avatar_url = thumb_data["data"][0].get("imageUrl", "")

                    # 5. 排版回覆訊息
                    reply = (f"📋 | 👤 **{args}** ({display_name})\n"
                             f"----------------------------------\n"
                             f"🔹 玩家 ID: {user_id}\n"
                             f"🔹 註冊日期: {created_at}\n"
                             f"🔸 SCR 職位: {role_name}")
                             
                    # QQ 機器人支援直接發送網路圖片 URL，帶入 image 參數即可
                    if avatar_url:
                        await message.reply(content=reply, image=avatar_url)
                    else:
                        await message.reply(content=reply)
                    
            except Exception as e:
                await message.reply(content=f"Error fetching data: {str(e)}")

async def main():
    config = uvicorn.Config(app, host="0.0.0.0", port=10000, log_level="info")
    server = uvicorn.Server(config)
    
    intents = botpy.Intents.default()
    client = MyClient(intents=intents)
    
    await asyncio.gather(
        server.serve(),
        client.start(appid="1905533434", secret="HkDhBgCiFmKsR1bCnP2fJxcHxeL3lUEy")
    )

if __name__ == "__main__":
    asyncio.run(main())
