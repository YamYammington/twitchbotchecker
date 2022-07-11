# standard library
import sys, json, time, socket, re, logging, threading

# needs to be installed
import requests

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s] %(message)s',
    handlers=[logging.FileHandler("twitch_bot.log"), logging.StreamHandler(sys.stdout)]
)
os.system("color")
OKCYAN = '\033[96m'
OK = '\033[92m'
FAIL = '\033[91m'
ENDC = '\033[0m'


def _async(func):
    from functools import wraps

    @wraps(func)
    def async_func(*args, **kwargs):
        f = threading.Thread(target=func, args=args, kwargs=kwargs)
        f.start()
        return
    return async_func


class TwitchBot:
    def __init__(self, username, client_id, token, channel):
        self.client_id = client_id
        self.token = token
        self.username = username
        self.channel = channel
        self.socket_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        self.read_chat()

    def connect_chat(self, delay=2):
        try:
            logging.info("Connecting to server...")
            time.sleep(delay)
            self.socket_conn = socket.socket()
            self.socket_conn.connect(('irc.chat.twitch.tv', 6667))
            self.socket_conn.send(f"PASS {self.token}\r\n".encode("utf-8"))
            self.socket_conn.send(f"NICK {self.username}\r\n".encode("utf-8"))
            self.socket_conn.send(f"CAP REQ :twitch.tv/membership\r\n".encode("utf-8"))
            self.socket_conn.send(f"JOIN #{self.channel}\r\n".encode("utf-8"))

        except ConnectionResetError as err:
            logging.error(f"{FAIL}An error occurred:\n{err}\nRetrying...{ENDC}")
            self.connect_chat(delay=(delay*2))

    def chat(self, msg):
        self.socket_conn.send(bytes(f'PRIVMSG #{self.channel} :{msg}\r\n', 'UTF-8'))

    @_async
    def read_chat(self):
        self.connect_chat()
        while True:
            response = self.socket_conn.recv(1024).decode("utf-8")
            if len(response) == 0:
                self.connect_chat()
                continue

            if response == "PING :tmi.twitch.tv\r\n":
                self.socket_conn.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                continue

            chat_object = re.search(r'^:(\w+)![^:]+:(.*)$', response)
            if chat_object:
                self.process_chat(chat_object)

    @_async
    def process_chat(self, chat_object):
        user = chat_object.group(1)
        msg = chat_object.group(2)
        commands = [('^!help$', 'help'), ('^!check$', 'check')]
        for regex, keyword in commands.items():
            if re.match(regex, msg):
                if keyword == 'help':
                    logging.info(f"{user} issued command: HELP")
                    self.chat(f'Hi {user}! I am BotChecker. For more information, go to https://github.com/YamYammington/twitchbotchecker')
                    return
                elif keyword == 'check':
                    if user not in self.get_viewers()[1]:
                        self.chat("Sorry, you need to be a moderator to use this command!")
                        return
                    logging.info(f"{user} issued command: CHECK")
                    self.chat("Beginning search...")
                    self.check_for_bots()
                    return

    def get_viewers(self):
        raw_json = requests.get(f"http://tmi.twitch.tv/group/user/{self.channel}/chatters").text
        bot_dict = json.loads(raw_json)
        moderator_list = bot_dict['chatters']['moderators'] + bot_dict['chatters']['broadcaster'] + bot_dict['chatters']['vips'] + bot_dict['chatters']['admins'] + bot_dict['chatters']['staff'] + bot_dict['chatters']['global_mods']
        return bot_dict['chatters']['viewers'], moderator_list

    def get_moderator_status(self):
        if "botchecker_yam" in self.get_viewers()[1]:
            return True
        else:
            return False

    def check_for_bots(self):
        bot_count = 0
        mod_status = self.get_moderator_status()
        viewerlist = self.get_viewers()[0]
        botlist = get_bot_accounts()
        if not viewerlist:
            logging.info("There are no viewers.")
            self.chat("There are no viewers.")
            return
        for user in viewerlist:
            if user in botlist:
                if mod_status:
                    bot_count += 1
                    logging.info(f"{OKCYAN}Bot found: {user}{ENDC}")
                    self.chat(f"/ban {user}")
                else:
                    bot_count += 1
                    logging.info(f"{OKCYAN}Bot found: {user}{ENDC}")
                    self.chat(f"User {user} is a bot!")

        if bot_count == 0:
            self.chat("No bots detected at the moment.")
        else:
            if mod_status:
                self.chat(f"Finished checking, banned {bot_count} bots.")
            else:
                self.chat(f"Finished checking, found {bot_count} bots.")

def get_bot_accounts():
    bot_list = []
    r = requests.get("https://api.twitchinsights.net/v1/bots/all")
    converted = json.loads(r.text)
    for account in converted["bots"]:
        bot_list.append(account[0])
    logging.debug(f"API returned {len(bot_list)} bot accounts.")
    return bot_list


if __name__ == "__main__":
    username = "botchecker_yam"
    client_id = "XXXXX"
    token = "oauth:XXXXX"
    channel = sys.argv[1]

    bot = TwitchBot(username, client_id, token, channel)
    bot.start()
    bot.chat('BotChecker is now online. !help for information.')
    logging.info("Bot online!")
    logging.info("Bot is a moderator." if bot.get_moderator_status() else "Bot is not a moderator.")
