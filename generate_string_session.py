#!/usr/bin/env python3
try:
    from pyrogram import Client
except Exception as e:
    print(e)
    print('\nInstall PyroFork: pip3 install pyrofork')
    exit(1)

print('Required pyrofork V2 or greater.')
API_KEY = int(input("Enter API KEY: "))
API_HASH = input("Enter API HASH: ")
with Client(name='EWU', api_id=API_KEY, api_hash=API_HASH, in_memory=True) as app:
    print(app.export_session_string())
    app.send_message("me",
        "**PyroFork Session String**:\n\n"
        f"`{app.export_session_string()}`"
    )
    print(
            "Your Pyrofork session string has been sent to "
            "Saved Messages of your Telegram account!"
        )