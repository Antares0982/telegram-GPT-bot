from basebot import baseBot
import time
import threading
import requests
from utils import *
SECONDS_IN_A_DAY = 60 * 60 * 24


class GptTokenExpireException(Exception):
    ...


class OpenAICallingProxy(object):
    def __init__(self, sid: int) -> None:
        self.lock = threading.Lock()
        self.update(sid)

    def call(self, content: str):
        # if time.time() - self.timestamp > SECONDS_IN_A_DAY:
        #     raise GptTokenExpireException()
        with self.lock:
            response = requests.post(
                f"http://127.0.0.1:{openai_port}/api", json={
                    "sid": self.sid,
                    "msg": content,
                    "ensure_id": True
                })
        if response.status_code != 200:
            raise Exception("OpenAI API error")
        return response.text

    def update(self, sid: int):
        with self.lock:
            self.timestamp = time.time()
            self.sid = sid
            response = requests.get(
                f"http://127.0.0.1:{openai_port}/create?sid={self.sid}",
            )
            if response.status_code != 200:
                raise Exception("OpenAI API error")


class OpenAISessionKeeper(object):
    def __init__(self) -> None:
        self.sessions: Dict[botmessages, OpenAICallingProxy] = {}
        self.lock = threading.Lock()
        self.bot: "gptBot" = None

    def call(self, msg: botmessages, content: str):
        with self.lock:
            if msg not in self.sessions:
                _u = OpenAICallingProxy(self._newId())
                self.sessions[msg] = _u
            t = self.sessions[msg]
        try:
            return t.call(content)
        except GptTokenExpireException:
            self.bot.debuginfo("token expired, renewing...")
            t.update(self._newId())
            return t.call(content)

    def ensure_id_call(self, msg: botmessages, content: str):
        with self.lock:
            if msg not in self.sessions:
                raise Exception("session not found")
            t = self.sessions[msg]
        try:
            return t.call(content)
        except GptTokenExpireException:
            self.bot.debuginfo("token expired, renewing...")
            t.update(self._newId())
            return t.call(content)

    def _newId(self) -> int:
        response = requests.get(f"http://127.0.0.1:{openai_port}/newid")
        if response.status_code == 200:
            return int(response.text)
        raise Exception("OpenAI API error")

    def register_session(self, botmsg: botmessages, nextbotmsg: botmessages):
        with self.lock:
            if botmsg not in self.sessions:
                raise Exception("session not found")
            self.sessions[nextbotmsg] = self.sessions[botmsg]


keeper = OpenAISessionKeeper()


class GPTPermissionDatabase(databaseManager):
    def __init__(self, botinstance: "gptBot", dbpath: str) -> None:
        super().__init__(botinstance, dbpath)
        self.tables += ["GPT"]


class gptBot(baseBot):
    def __init__(self):
        self.gptbotInit()

    def gptbotInit(self):
        print("gpt bot init")
        if not hasattr(self, "updater"):
            print("base bot init")
            baseBot.__init__(self)
            print("base bot init finish")
        print("gpt bot init finish")
        self.gpt_session_keeper = keeper
        keeper.bot = self
        self.gpt_allow_database = GPTPermissionDatabase(self, gpt_database)
        allow_data_all = self.gpt_allow_database.select("GPT")
        self.gpt_allow_list = set(r[0] for r in allow_data_all)

    def call_gpt(self, botmsg: botmessages, content: str, ensure_id=False):
        if ensure_id:
            return self.gpt_session_keeper.ensure_id_call(botmsg, content)
        return self.gpt_session_keeper.call(botmsg, content)

    def register_sessionid(self, botmsg: botmessages, nextbotmsg: botmessages):
        self.gpt_session_keeper.register_session(botmsg, nextbotmsg)

    def addPermmision(self, chatid: int):
        if chatid not in self.gpt_allow_list:
            self.gpt_allow_list.add(chatid)
            self.gpt_allow_database.insertInto("GPT", {"TGID": chatid})

    @staticmethod
    def processMessage(text: str) -> str:
        text = text.strip()
        if text.startswith("/gpt"):
            text = text[4:]
        return text

    @commandCallbackMethod
    def gpt(self, update: Update, context: CallbackContext) -> handleStatus:
        if self.lastchat not in self.gpt_allow_list and not isfromme(update):
            return self.errorInfo("你/这个群没有权限")
        oldmsg = botmessages(
            self.lastchat, self.lastmsgid)
        question = self.processMessage(update.message.text)
        msgid = self.reply(self.call_gpt(oldmsg, question))
        self.gpt_session_keeper.register_session(oldmsg, botmessages(
            self.lastchat, msgid))
        return True

    @commandCallbackMethod
    def allowgpt(self, update: Update, context: CallbackContext) -> handleStatus:
        if not isfromme(update):
            return self.errorInfo("你没有权限")
        if isprivate(update):
            try:
                allowId = int(context.args[0])
            except Exception:
                return self.errorInfo("用法: /allowgpt <群号>")
            self.addPermmision(allowId)
            self.reply("已开启")
        else:
            self.addPermmision(self.lastchat)
            self.reply("已开启")
        return True

    def textHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        if self.lastchat not in self.gpt_allow_list and self.lastuser != MYID:
            return handlePassed
        if update.message.reply_to_message is None:
            return handlePassed
        oldmsg = botmessages(self.lastchat,
                             update.message.reply_to_message.message_id)
        try:
            msgid = self.reply(self.call_gpt(
                oldmsg, update.message.text, ensure_id=True))
        except Exception:
            self.debuginfo("no session, ignored")
            return handlePassed
        self.gpt_session_keeper.register_session(
            oldmsg,
            botmessages(self.lastchat, msgid)
        )
        return handleBlocked()

    @classmethod
    def chatmigrate(cls, oldchat: int, newchat: int, instance: "gptBot"):
        if oldchat in instance.gpt_allow_list:
            instance.debuginfo(
                f"gpt allowed chat migrate {oldchat} -> {newchat}"
            )
            instance.gpt_allow_list.remove(oldchat)
            instance.gpt_allow_list.add(newchat)
            instance.gpt_allow_database.delete(
                "GPT", {"TGID": oldchat}
            )
            instance.gpt_allow_database.insertInto(
                "GPT", {"TGID": newchat}
            )
