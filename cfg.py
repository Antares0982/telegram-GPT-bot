from configparser import ConfigParser

__all__ = [
    "token",
    "proxy",
    "proxy_url",
    "MYID",
    "blacklistdatabase",
    "startcommand",
    "openai_port",
    "gpt_database",
]

cfgparser = ConfigParser()
cfgparser.read("config.ini")

# region basic
token = cfgparser["settings"]["token"]
proxy = cfgparser.getboolean("settings", "proxy")
proxy_url = cfgparser["settings"]["proxy_url"]
MYID = cfgparser.getint("settings", "myid")
blacklistdatabase = cfgparser["settings"]["blacklistdatabase"]
startcommand = cfgparser["settings"]["startcommand"]
# endregion

# region gpt
openai_port = cfgparser.getint("gpt", "port")
gpt_database = cfgparser["gpt"]["database"]
# endregion

del cfgparser
