import sys
import requests
import json
import time
import socket
from threading import Thread
import re

commands = {
    '^!check': 'start_banning',
    '^!help': 'help'
}


# Function for threaded asynchronous function decorator @async
def _async(func):
    from functools import wraps

    @wraps(func)
    def async_func(*args, **kwargs):
        f = Thread(target=func, args=args, kwargs=kwargs)
        f.start()
        return
    return async_func


class TwitchBot:
    def __init__(self, username, client_id, token, channel):
        self.client_id = client_id
        self.token = token
        self.username = username
        self.channel = channel
        self.last_message = 0

    def connect_chat(self, delay=2):
        # create chat connection
        try:
            print("Connecting to server...")
            time.sleep(delay)
            s = socket.socket()
            s.connect(('irc.chat.twitch.tv', 6667))
            s.send(f"PASS {self.token}\r\n".encode("utf-8"))
            s.send(f"NICK {self.username}\r\n".encode("utf-8"))
            s.send(f"CAP REQ :twitch.tv/membership\r\n".encode("utf-8"))
            s.send(f"JOIN #{self.channel}\r\n".encode("utf-8"))
            self.s = s
        except ConnectionResetError as err:
            print(f"An error occurred:\n{err}\nRetrying...")
            self.connect_chat(delay=(delay*2))

    # Send messages to chat
    def chat(self, sock, msg):
        sock.send(bytes('PRIVMSG #%s :%s\r\n' % (self.channel, msg), 'UTF-8'))

    @_async
    def read_chat(self):
        # Starts infinite loop listening to the IRC server
        self.connect_chat()
        while True:
            response = self.s.recv(1024).decode("utf-8")
            if len(response) == 0:
                self.connect_chat()
                continue

            # PONG replies to keep the connection alive
            if response == "PING :tmi.twitch.tv\r\n":
                self.s.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                continue

            # Separates user and message.
            chat_object = re.search(r'^:(\w+)![^:]+:(.*)$', response)
            if chat_object:
                self.process_chat(chat_object)

    @_async
    def process_chat(self, chat_object):
        user = chat_object.group(1)
        msg = chat_object.group(2)
        for command, action in commands.items():
            if bool(re.match(command, msg)):
                if action == 'help':
                    print(f"{user} issued command: HELP")
                    self.chat(self.s, f'Hi {user}! I am BotChecker. For more information, go to https://github.com/YamYammington/twitchbotchecker')
                    return
                elif action == 'start_banning':
                    print(f"{user} issued command: CHECK")
                    self.chat(self.s, "Beginning search...")
                    self.check_for_bots()
                    return
                else:
                    print(f"No command detected in message: {msg}.")
                    continue
            else:
                continue

    def get_viewers(self):
        r = requests.get(f"http://tmi.twitch.tv/group/user/{self.channel}/chatters")
        converted = json.loads(r.text)
        moderator_list = converted['chatters']['moderators'] + converted['chatters']['broadcaster'] + converted['chatters']['vips'] + converted['chatters']['admins'] + converted['chatters']['staff'] + converted['chatters']['global_mods']
        return converted['chatters']['viewers'], moderator_list

    def get_moderator_status(self):
        if "botchecker_yam" in self.get_viewers()[1]:
            return True
        else:
            return False

    def check_for_bots(self):
        bot_count = 0
        mod_status = self.get_moderator_status()
        text = "Bot is a moderator." if mod_status else "Bot is not a moderator."
        print(text)
        viewerlist = self.get_viewers()[0]
        botlist = get_bot_accounts()
        if not viewerlist:
            self.chat(self.s, "There are no viewers!")
            return
        for user in viewerlist:
            if user in botlist:
                if mod_status:
                    bot_count += 1
                    print(f"Bot found: {user}")
                    self.chat(self.s, f"/ban {user}")
                else:
                    bot_count += 1
                    print(f"Bot found: {user}")
                    self.chat(self.s, f"User {user} is a bot!")
            else:
                continue

        if bot_count == 0:
            self.chat(self.s, "No bots detected at the moment.")
        else:
            if mod_status:
                self.chat(self.s, f"Finished checking, banned {bot_count} bots.")
                return
            else:
                self.chat(self.s, f"Finished checking, found {bot_count} bots.")


def get_bot_accounts():
    bot_list = []
    r = requests.get("https://api.twitchinsights.net/v1/bots/all")
    converted = json.loads(r.text)
    for bot in converted["bots"]:
        bot_list.append(bot[0])
    print(f"API returned {len(bot_list)} bot accounts.")
    return bot_list


def main():
    username = "botchecker_yam"
    client_id = "XXXXX"
    token = "oauth:XXXXX"
    channel = sys.argv[1]

    bot = TwitchBot(username, client_id, token, channel)
    bot.read_chat()
    time.sleep(7)
    bot.chat(bot.s, 'BotChecker is now online. !help for information.')
    print("Bot online!")


if __name__ == "__main__":
    main()
