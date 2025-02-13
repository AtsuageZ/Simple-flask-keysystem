import discord
from discord.ext import commands
import random
import string
import asyncio
import json
import os
import requests
from flask import Flask, request, jsonify
import datetime
import threading

app = Flask(__name__)
guild_id = 11451419194545810 # replace it your guild id
# json
KEYS_FILE = 'keys.json'
SETTINGS_FILE = 'settings.json'
Bot_token = 'your bot token'
ADMIN_PASSWORD = "atsuage114514"
WEBHOOK_URL = "YOUR_WEBHOOK_URL" #additionally

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Flask Functions
def load_keys():
    if not os.path.exists(KEYS_FILE):
        return {}
    with open(KEYS_FILE, 'r') as file:
        return json.load(file)

def save_keys(keys):
    with open(KEYS_FILE, 'w') as file:
        json.dump(keys, file, indent=4)

def log_key_change(old_hwid, new_hwid, key):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open('log.txt', 'a') as log_file:
        log_file.write(f"Time: {timestamp}, Key: {key}, Old HWID: {old_hwid}, New HWID: {new_hwid}\n")

def send_webhook_notification(title, description, color=16711680):
    if not WEBHOOK_URL:
        return
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    embed = {
        "username": "Nothing Auth log",
        "avatar_url": "https://avatars.githubusercontent.com/u/111366720?s=200&v=4",
        "embeds": [
            {
                "title": title,
                "description": description,
                "color": color,
                "footer": {"text": f"Timestamp: {timestamp}"}
            }
        ]
    }
    try:
        response = requests.post(WEBHOOK_URL, json=embed)
        if response.status_code != 204:
            print(f"Failed to send webhook: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Error sending webhook: {e}")

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

# Discord Bot Functions
def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'w') as file:
            json.dump({}, file)
    with open(SETTINGS_FILE, 'r') as file:
        return json.load(file)

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as file:
        json.dump(settings, file, indent=4)

def get_server_settings(guild_id):
    settings = load_settings()
    if str(guild_id) not in settings:
        settings[str(guild_id)] = {"log_channel_id": None, "admin_role_id": None}
        save_settings(settings)
    return settings[str(guild_id)]

def set_server_settings(guild_id, log_channel_id=None, admin_role_id=None):
    settings = load_settings()
    if str(guild_id) not in settings:
        settings[str(guild_id)] = {}
    if log_channel_id:
        settings[str(guild_id)]["log_channel_id"] = log_channel_id
    if admin_role_id:
        settings[str(guild_id)]["admin_role_id"] = admin_role_id
    save_settings(settings)


async def send_log_message(guild_id, title, description):
    settings = get_server_settings(guild_id)
    log_channel_id = settings["log_channel_id"]
    if log_channel_id:
        log_channel = bot.get_channel(log_channel_id)
        if log_channel:
            embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
            await log_channel.send(embed=embed)

async def is_admin(interaction: discord.Interaction):
    settings = get_server_settings(interaction.guild.id)
    admin_role_id = settings["admin_role_id"]
    if admin_role_id:
        admin_role = discord.utils.get(interaction.guild.roles, id=int(admin_role_id))
        return admin_role in interaction.user.roles
    return interaction.user.guild_permissions.administrator

# Slashコマンド: キー追加
@bot.tree.command(name="add_key", description="新しいランダムなキーを生成します。")
async def add_key(interaction: discord.Interaction):
    if not await is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return

    # 新しいキーを生成
    new_key = "NOTHING-" + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(12))
    
    # キーをファイルに保存
    keys = load_keys()
    keys[new_key] = {}
    save_keys(keys)

    await interaction.response.send_message(f"新しいキーが生成されました: {new_key}", ephemeral=True)
    await send_log_message(interaction.guild.id, "新しいキーが生成されました!", f"新しいキー: {new_key}")

# Slashコマンド: キー変更
@bot.tree.command(name="change_key", description="Change an existing key")
async def change_key(interaction: discord.Interaction, old_key: str, new_key: str):
    if not await is_admin(interaction):
        await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
        return

    # Check if key exists, then change it
    keys = load_keys()
    if old_key in keys:
        keys[new_key] = keys.pop(old_key)
        save_keys(keys)
        await interaction.response.send_message(f"キーが変更されました: {new_key}", ephemeral=True)
        await send_log_message(interaction.guild.id, "キーが変更されました。", f"以前のキー: {old_key}\n新しいキー: {new_key}")
    else:
        await interaction.response.send_message("指定されたキーが存在しません。", ephemeral=True)

# Slashコマンド: ログチャンネル設定
@bot.tree.command(name="set_log_channel", description="Set the log channel")
async def set_log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not await is_admin(interaction):
        await interaction.response.send_message("You do not have the required permissions to use this command.", ephemeral=True)
        return

    set_server_settings(interaction.guild.id, log_channel_id=channel.id)
    await interaction.response.send_message(f"Log channel set to {channel.mention}", ephemeral=True)

@bot.tree.command(name="set_admin_role", description="Set the admin role")
async def set_admin_role(interaction: discord.Interaction, role: discord.Role):
    if not await is_admin(interaction):
        await interaction.response.send_message("You do not have the required permissions to use this command.", ephemeral=True)
        return
    
    set_server_settings(interaction.guild.id, admin_role_id=role.id)
    await interaction.response.send_message(f"Admin role set to {role.name}", ephemeral=True)

@app.route('/validate_key', methods=['POST'])
def validate_key():
    data = request.json
    key = data.get("api_key")
    hwid = data.get("hwid")
    ip_address = get_client_ip()

    if not key or not hwid:
        return jsonify({"error": "Key and HWID are required"}), 400

    keys = load_keys()
    if key not in keys:
        return jsonify({"error": "Invalid key"}), 401

    key_data = keys[key]
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    saved_hwid = key_data.get("hwid")
    if saved_hwid and saved_hwid != hwid:
        # Log using a static or pre-configured guild ID
        bot.loop.create_task(
            send_log_message(
                guild_id,
                "HWID Mismatch Detected",
                f"Key: {key}\nSaved HWID: {saved_hwid}\nAttempted HWID: {hwid}\nIP Address: {ip_address}"
            )
        )
        return jsonify({"error": "HWID mismatch. Login blocked"}), 403

    key_data["last_login_date"] = current_date
    key_data["hwid"] = hwid
    save_keys(keys)

    # Log the successful login using the same guild_id
    bot.loop.create_task(
        send_log_message(
            guild_id,  # Same guild_id as before
            "Login Successful",
            f"Key: {key}\nHWID: {hwid}\nIP Address: {ip_address}"
        )
    )

    return jsonify({"message": "Login successful"}), 200

def run_flask():
    app.run(debug=True, host='0.0.0.0', port=25592, use_reloader=False)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    bot.run(Bot_token)
