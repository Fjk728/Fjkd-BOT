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
        
        # 指令 1：/view (玩家查詢)
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
                    
                    user_detail_res = await client.get(
                        f"https://users.roblox.com/v1/users/{user_id}",
                        headers=headers,
                        timeout=10.0
                    )
                    user_detail_data = user_detail_res.json()
                    created_at = user_detail_data.get("created", "未知").split("T")[0]
                    
                    thumb_res = await client.get(
                        f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png",
                        headers=headers,
                        timeout=10.0
                    )
                    thumb_data = thumb_res.json()
                    avatar_url = ""
                    if thumb_data.get("data") and len(thumb_data["data"]) > 0:
                        avatar_url = thumb_data["data"][0].get("imageUrl", "")

                    reply = (f"| {args} ({display_name})\n"
                             f"----------------------------------\n"
                             f"玩家 ID: {user_id}\n"
                             f"註冊日期: {created_at}\n"
                             f"職位: {role_name}")
                             
                    if avatar_url:
                        try:
                            upload_media = await self.api.post_group_file(
                                group_openid=message.group_openid,
                                file_type=1,
                                url=avatar_url
                            )
                            await self.api.post_group_message(
                                group_openid=message.group_openid,
                                msg_type=7,
                                msg_id=message.id,
                                media=upload_media,
                                content=reply
                            )
                        except Exception as e:
                            await message.reply(content=reply + f"\n(圖片加載失敗: {str(e)})")
                    else:
                        await message.reply(content=reply)
                    
            except Exception as e:
                await message.reply(content=f"Error fetching data: {str(e)}")

        # 指令 2：/groupstats (SCR群組特定階級人數統計)
        elif "/groupstats" in content:
            try:
                async with httpx.AsyncClient() as client:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Content-Type": "application/json"
                    }
                    
                    roles_res = await client.get(
                        f"https://groups.roblox.com/v1/groups/{SCR_GROUP_ID}/roles",
                        headers=headers,
                        timeout=10.0
                    )
                    roles_data = roles_res.json()
                    
                    # 定義要抓取的目標階級 (TD 到 SV)
                    target_roles = [
                        "Trainee Driver",
                        "Qualified Driver",
                        "Dispatcher",
                        "Guard",
                        "Signaller",
                        "Supervisor"
                    ]
                    
                    stats_dict = {}
                    if "roles" in roles_data:
                        for role in roles_data["roles"]:
                            if role["name"] in target_roles:
                                stats_dict[role["name"]] = role.get("memberCount", 0)
                    
                    # 按照自訂的陣列順序輸出
                    stats_lines = []
                    for role_name in target_roles:
                        if role_name in stats_dict:
                            stats_lines.append(f"{role_name}: {stats_dict[role_name]}")
                    
                    if stats_lines:
                        reply = (f"| SCR 階級人數統計 (TD-SV)\n"
                                 f"----------------------------------\n"
                                 + "\n".join(stats_lines))
                        await message.reply(content=reply)
                    else:
                        await message.reply(content="Error: 無法獲取群組資料。")
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
