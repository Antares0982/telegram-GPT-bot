# region import
import datetime
import sqlite3
import threading
import time
import types
from functools import wraps
from typing import Callable, List

from numpy.random import default_rng
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from basicfunc import *
from cfg import *

try:
    from typing import TYPE_CHECKING
except Exception:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from main import AntaresBot
# endregion

# region const
SECONDS_IN_A_DAY = 24 * 60 * 60

randgenerator = default_rng()

_RT = TypeVar("_RT")
# endregion

# region function


def chatisfromme(update: Update) -> bool:
    """检查是否来自`MYID`"""
    return getchatid(update) == MYID


def isfromme(update: Update):
    return getfromid(update) == MYID


def getfromid(update: Update) -> int:
    """返回`from_user.id`"""
    return update.message.from_user.id


def getchatid(update: Update) -> int:
    """返回`chat_id`"""
    return update.effective_chat.id


def getmsgid(update: Update) -> int:
    """返回message_id"""
    if update.message is not None:
        return update.message.message_id
    if update.channel_post is not None:
        return update.channel_post.message_id
    if update.edited_channel_post is not None:
        return update.edited_channel_post.message_id
    raise ValueError("无法从update获取msgid")


def isprivate(update: Update) -> bool:
    return update.effective_chat.type == "private"


def isgroup(update: Update) -> bool:
    return update.effective_chat.type.find("group") != -1


def ischannel(update: Update) -> bool:
    return update.effective_chat.type == "channel"


def flattenButton(
    buttons: List[InlineKeyboardButton], numberInOneLine: int
) -> InlineKeyboardMarkup:
    btl: List[List[InlineKeyboardButton]] = []
    while len(buttons) > numberInOneLine:
        btl.append(buttons[:numberInOneLine])
        buttons = buttons[numberInOneLine:]
    if len(buttons) > 0:
        btl.append(buttons)
    return InlineKeyboardMarkup(btl)


def getTimeStamp() -> int:
    """精确到毫秒的时间戳."""
    return int(1000*(time.time() - (1 << 30)))

# endregion

# region classes


class botmessages(object):
    __slots__ = ["chat", "msgid"]

    def __init__(self, chat: int, msgid: int) -> None:
        self.chat = chat
        self.msgid = msgid

    def __hash__(self) -> int:
        return hash(self.chat*10000000000+self.msgid)

    def __eq__(self, o: 'botmessages') -> bool:
        try:
            return self.chat == o.chat and self.msgid == o.msgid
        except Exception:
            return False

    def __expr__(self) -> str:
        return str(self.chat)+' '+str(self.msgid)

    def __str__(self) -> str:
        return self.__expr__()


class dateStringStruct(object):
    __slots__ = ["_year", "_month", "_day", "__dict__"]

    def __init__(self, s: str) -> None:
        if "." not in s and " " not in s:
            raise ValueError("dateStringStruct不接受此类型的参数")
        if "." in s:
            args = s.split(".")
        else:
            args = s.split()
        if len(args) < 2 or len(args) > 3:
            raise ValueError("dateStringStruct不接受此类型的参数")
        try:
            if len(args) == 3:
                self.year = int(args[0])
                args = args[1:]
            self.month, self.day = map(int, args)
        except Exception:
            raise ValueError("dateStringStruct接收到的参数无效")

    @property
    def year(self) -> Optional[int]:
        if "_year" not in self.__dict__:
            return None
        return self._year

    @year.setter
    def year(self, _y: int):
        self._year = _y

    @property
    def month(self) -> int:
        return self._month

    @month.setter
    def month(self, _m: int):
        if _m <= 0 or _m > 12:
            raise ValueError(f"month should be in 1-12, got {_m}")
        self._month = _m

    @property
    def day(self) -> int:
        return self._day

    @day.setter
    def day(self, _d: int):
        if _d <= 0 or _d > 31:
            raise ValueError(f"day should be in 1-31, got {_d}")
        self._day = _d

    @property
    def original(self) -> str:
        ans = ""
        if self.year:
            ans = f"{self.year}."
        ans += f"{self.month}.{self.day}"
        return ans

    def __repr__(self) -> str:
        ans = ""
        if self.year:
            ans = f"{self.year}年"
        ans += f"{self.month}月{self.day}日"
        return ans

    @classmethod
    def fromReprString(cls, s: str) -> str:
        ans = ""
        if "年" in s:
            ans, s = s.split("年")
            ans += "."
        s = s.split("月")
        ans += s[0] + "."
        s = s[1].lstrip()

        ans += s[: s.find("日")]
        return cls(ans)

    def __gt__(self, o: "dateStringStruct") -> bool:
        if self.year and o.year:
            if self.year > o.year:
                return True
            if self.year < o.year:
                return False
        if self.month > o.month:
            return True
        if self.month < o.month:
            return False
        return self.day > o.day


class timeStringStruct(object):
    __slots__ = ["_sec", "_hour", "_min", "__dict__"]

    def __init__(self, s: str) -> None:
        if ":" not in s:
            raise ValueError("timeStringStruct 不接受此类型的参数")
        args = s.split(":")
        if len(args) < 2 or len(args) > 3:
            raise ValueError("timeStringStruct 不接受此类型的参数")
        try:
            if len(args) == 3:
                self.sec = int(args[2])
                args = args[:2]
            self.hour, self.minute = map(int, args)
        except Exception:
            raise ValueError("timeStringStruct 接收到的参数无效")

    @property
    def sec(self) -> int:
        if "_sec" not in self.__dict__:
            return None
        return self._sec

    @sec.setter
    def sec(self, _s: int):
        if _s < 0 or _s >= 60:
            raise ValueError(f"sec should be in 0-59, got {_s}")
        self._sec = _s

    @property
    def hour(self) -> int:
        return self._hour

    @hour.setter
    def hour(self, _h: int):
        if _h < 0 or _h >= 24:
            raise ValueError(f"hour should be in 0-23, got {_h}")
        self._hour = _h

    @property
    def minute(self) -> int:
        return self._min

    @minute.setter
    def minute(self, _m: int):
        if _m < 0 or _m >= 60:
            raise ValueError(f"minute should be in 0-59, got {_m}")
        self._min = _m

    def original(self) -> str:
        if len(str(self.hour)) == 1:
            ans = f"0{self.hour}"
        else:
            ans = str(self.hour)
        if len(str(self.minute)) == 1:
            ans += f":0{self.minute}"
        else:
            ans += f":{self.minute}"
        if self.sec:
            if len(str(self.sec)) == 1:
                ans += f":0{self.sec}"
            else:
                ans += f":{self.sec}"
        return ans

    def __repr__(self) -> str:
        return self.original()

    def evalLeftSec(self) -> int:
        loctime = datetime.datetime.now()
        nowh = loctime.hour
        nowm = loctime.minute
        nows = loctime.second
        ans = (self.hour - nowh) * 60
        ans += self.minute - nowm
        ans = ans * 60 - nows + 1
        if ans <= 0:
            ans += SECONDS_IN_A_DAY
        return ans  # 延迟1秒

    def allSecs(self) -> int:
        ans = self.minute * 60 + self.hour * 3600
        if self.sec:
            ans += self.sec
        return ans


class delayLock(object):
    """Delay a few seconds at `__exit__`."""

    def __init__(self, delaySeconds: int = 10) -> None:
        self.__lock = threading.Lock()
        self.__delay = delaySeconds

    def __enter__(self) -> bool:
        return self.__lock.__enter__()

    def __exit__(self, *args, **kwargs) -> Optional[bool]:
        def _f():
            time.sleep(self.__delay)
            return self.__lock.__exit__(*args, **kwargs)

        threading.Thread(target=_f).start()

    def locked(self) -> bool:
        return self.__lock.locked()

    def acquire(self):
        self.__lock.acquire()

    def release(self):
        def _f():
            time.sleep(self.__delay)
            self.__lock.release()

        threading.Thread(target=_f).start()


class multiSubLock(object):
    """Only used in multiLock. See `multiLock`."""

    def __init__(self, _multiLock: 'multiLock', msg: botmessages) -> None:
        self._ml = _multiLock
        self.msg = msg

    def __enter__(self) -> bool:
        while True:
            while self.locked():
                time.sleep(1)
            with self._ml._lock:
                if self.locked():
                    continue
                self._ml.memory[self.msg] = self
                return True

    def __exit__(self, *args, **kwargs) -> Optional[bool]:
        def _f():
            time.sleep(self._ml.delay)
            with self._ml._lock:
                self._ml.memory.pop(self.msg)
                return True

        threading.Thread(target=_f).start()

    def locked(self) -> bool:
        return (self.msg in self._ml.memory)

    def acquire(self):
        self.__enter__()

    def release(self):
        self.__exit__()


class multiLock(object):
    """
    A lock with some data. 
    If a lock acquire with the same data as another, its blocked until the first is done.
    """

    def __init__(self, delaytime: int = 0) -> None:
        self.delay = delaytime
        self._lock = threading.Lock()
        self.memory: Dict[botmessages, multiSubLock] = dict()

    def __getitem__(self, msg: botmessages) -> multiSubLock:
        return multiSubLock(self, msg)


class fakeBotObject(object):
    """
    bot instance的伪装类。
    在并发情形下，bot object会在一个command callback函数执行完成之前获取
    新的lastuser，lastchat等信息。在一个update的范围内，如果需要保证这些
    参数是不会发生改变的，使用这个类来伪装成一个botinstance传给callback
    method。注意：除了上述三个数据不会发生改变以外，其他数据是会发生改变的。
    """

    __slots__ = ["_real_bot_obj", "lastchat", "lastuser", "lastmsgid"]

    def __init__(self, bot) -> None:
        self._real_bot_obj = bot
        self.lastchat = 0
        self.lastuser = 0
        self.lastmsgid = -1

    def _to_real(self) -> 'AntaresBot':
        """
        Return the true bot object of main bot.
        """
        return self._real_bot_obj

    def __getattr__(self, attr):
        x = getattr(self._real_bot_obj, attr)
        if callable(x) and (not isinstance(x, types.FunctionType) and not callable(x.__self__)):
            # judge if x is static method or class method.
            # If x is, then return the original x,
            # since it doesn't use any fakeBotObject data.

            def wraped_func(*args, **kwargs):
                return getattr(type(self._real_bot_obj), attr)(self, *args, **kwargs)

            return wraped_func
        return x

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name in ["lastchat", "lastuser", "lastmsgid", "_real_bot_obj"]:
            object.__setattr__(self, __name, __value)
            return
        self._real_bot_obj.__dict__[__name] = __value


class workingMethodFilter(object):
    ...


class databaseManager(object):
    conn: sqlite3.Connection

    def __init__(self, botinstance: "AntaresBot", dbpath: str) -> None:
        self.database = dbpath
        self.conn = None
        self.botinstance = botinstance
        self.tables: List[str] = []
        self.lock = threading.Lock()

    def connect(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                ...
        self.conn = sqlite3.connect(self.database)

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                ...
            self.conn = None

    def _getPrimaryKey(self, table: str) -> str:
        c = self.conn.cursor()
        c.execute(f"PRAGMA table_info({table});")
        for r in c.fetchall():
            if r[-1] > 0:
                return r[1]
        return ""

    def _select(
        self, table: str, where: Optional[Dict[str, Any]] = None, need: Optional[List[str]] = None
    ) -> list:
        parseArgs: List[str] = []
        command = "SELECT "
        if need is None:
            command += "* FROM "
        else:
            command += ", ".join(need) + " FROM "

        command += table

        if where is not None:
            command += " WHERE "
            l = []
            for k, v in where.items():
                thispart = f"{k}="
                if type(v) is str:
                    thispart += "?"
                    parseArgs.append(v)
                else:
                    thispart += str(v)
                l.append(thispart)
            command += " AND ".join(l)

        command += ";"

        self.botinstance.debuginfo(command)
        if len(parseArgs) > 0:
            self.botinstance.debuginfo("parsing args: "+' '.join(parseArgs))

        c = self.conn.cursor()

        c.execute(command, parseArgs)

        return c.fetchall()

    def _insert(self, table: str, datadict: dict):
        c = self.conn.cursor()
        command = f"INSERT INTO {table}("
        command2 = f"VALUES("
        parseArgs: List[str] = []
        sep = ""
        for k, v in datadict.items():
            command += sep + str(k)
            if type(v) is str:
                command2 += f"{sep} ?"
                parseArgs.append(v)
            else:
                command2 += sep + " " + str(v)
            sep = ","
        command += ")"
        command2 += ");"

        command += command2

        self.botinstance.debuginfo(command)
        if len(parseArgs) > 0:
            self.botinstance.debuginfo("parsing args: "+' '.join(parseArgs))
        c.execute(command, parseArgs)
        self.conn.commit()

    def _update(self, table: str, datadict: dict, pkey: str):
        c = self.conn.cursor()

        command = f"UPDATE {table} SET "
        parseArgs: List[str] = []
        sep = ""
        setlength = 0

        for k, v in datadict.items():
            if str(k) == pkey:
                continue
            setlength += 1
            command += sep + str(k) + "="
            if type(v) is str:
                command += "?"
                parseArgs.append(v)
            else:
                command += str(v)
            sep = ","

        if setlength == 0:
            self.botinstance.debuginfo(
                "nothing to set, no need to update database")
            return

        command += f" WHERE {pkey}="
        if type(datadict[pkey]) is str:
            command += f"?;"
            parseArgs.append(datadict[pkey])
        else:
            command += str(datadict[pkey]) + ";"

        self.botinstance.debuginfo(command)
        if len(parseArgs) > 0:
            self.botinstance.debuginfo("parsing args: "+' '.join(parseArgs))

        c.execute(command, parseArgs)
        self.conn.commit()

    def _delete(self, table: str, where: Optional[Dict[str, Any]] = None):
        c = self.conn.cursor()
        cmd = f"DELETE FROM {table}"
        parseArgs: List[str] = []

        if where is not None:
            cmd += f" WHERE "
            l = []
            for k, v in where.items():
                thispart = f"{k}="
                if type(v) is str:
                    thispart += "?"
                    parseArgs.append(v)
                else:
                    thispart += str(v)
                l.append(thispart)
            cmd += " AND ".join(l)

        cmd += ";"

        self.botinstance.debuginfo(cmd)
        if len(parseArgs) > 0:
            self.botinstance.debuginfo("parsing args: "+' '.join(parseArgs))

        c.execute(cmd, parseArgs)
        self.conn.commit()

    def _seenThisPkey(self, table: str, pk: str, pkeyval):
        return bool(self._select(table, {pk: pkeyval}))

    def insertInto(self, table: str, datadict: dict):
        with self:
            pk = self._getPrimaryKey(table)
            upd = False
            if pk != "":
                if pk not in datadict:
                    raise ValueError("插入表的数据必须要有主键")
                if self._seenThisPkey(table, pk, datadict[pk]):
                    self.botinstance.debuginfo("已经存储过该key，更新目标")
                    upd = True

            if upd:
                self._update(table, datadict, pk)
            else:
                self._insert(table, datadict)

    def insertMany(self, table: str, manydata: List[dict], no_pkey_check: bool = False):
        with self:
            pk = self._getPrimaryKey(table)
            for data in manydata:
                upd = False
                if not no_pkey_check and pk != "":
                    if pk not in data:
                        raise ValueError("插入表的数据必须要有主键")
                    if self._seenThisPkey(table, pk, data[pk]):
                        upd = True
                if upd:
                    self._update(table, data, pk)
                else:
                    self._insert(table, data)

    def select(
        self,
        table: str,
        where: Optional[Dict[str, Any]] = None,
        need: Optional[List[str]] = None,
    ) -> list:
        with self:
            ans = self._select(table, where, need)
            return ans

    def execute(self, cmd: List[str]):
        """execute a list of commands."""
        with self:
            for c in cmd:
                self.conn.cursor().execute(c)
            self.conn.commit()

    def delete(self, table, where: Optional[Dict[str, Any]] = None):
        with self:
            self._delete(table, where)

    def clean(self, table: str):
        with self:
            self._delete(table)

    def __enter__(self):
        self.lock.acquire()
        self.connect()
        return True

    def __exit__(self, *args, **kwargs):
        self.close()
        self.lock.release()
        return True


class CallbackDataServer(object):
    """store callback data in a dict."""

    def __init__(self) -> None:
        self.callbackDataMemory: Dict[str, str] = dict()

    def getData(self, key: str) -> str:
        ans = dictpop(self.callbackDataMemory, key)
        if ans is None:
            raise ValueError("无效的callbackData索引")
        return ans

    def setData(self, key: str, value: str) -> None:
        if key in self.callbackDataMemory:
            raise ValueError("callbackData索引已存在")
        self.callbackDataMemory[key] = value


class handleStatus(object):
    __slots__ = ["block", "normal"]

    def __init__(self, normal: bool, block: bool) -> None:
        self.block: bool = block
        self.normal: bool = normal

    def __bool__(self):
        ...

    def blocked(self):
        return self.block


handlePassed = handleStatus(True, False)


class handleBlocked(handleStatus):
    __slots__ = []

    def __init__(self, normal: bool = True) -> None:
        super().__init__(normal=normal, block=True)

    def __bool__(self):
        return self.normal


# endregion

# region decorator


class commandCallback(object):
    def __init__(self, func: Callable) -> None:
        wraps(func)(self)

    def __call__(self, *args, **kwargs):
        numOfArgs = len(args) + len(kwargs.keys())
        if numOfArgs != 2:
            raise TypeError(f"指令的callback function参数个数应为2，但接受到{numOfArgs}个")
        return self.__wrapped__(*args, **kwargs)

    def __get__(self, instance, cls):
        if instance is not None:
            raise TypeError("该装饰器不适用于方法")
        return self


class commandCallbackMethod(object):
    """
    表示一个指令的callback函数，仅限于类的成员方法。
    调用时，会执行一次指令的前置函数。
    """

    def __init__(self, func: Callable[[Update, CallbackContext], _RT]) -> None:
        wraps(func)(self)
        # self.run_async = True
        self.instance: "AntaresBot" = None

    def __call__(self, *args, **kwargs):
        numOfArgs = len(args) + len(kwargs.keys())
        if numOfArgs != 2:
            raise RuntimeError(f"指令的callback function参数个数应为2，但接受到{numOfArgs}个")

        if len(args) == 2:
            fakeinstance = self.preExecute(*args)
        elif len(args) == 1:
            fakeinstance = self.preExecute(args[0], **kwargs)
        else:
            fakeinstance = self.preExecute(**kwargs)

        inst = self.instance
        with inst.locks.botlock:
            if any(
                x in inst.blacklist
                for x in (fakeinstance.lastchat, fakeinstance.lastuser)
            ):
                fakeinstance.errorInfo("你在黑名单中，无法使用任何功能")
                return

        return self.__wrapped__(fakeinstance, *args, **kwargs)

    def preExecute(self, update: Update, context: "CallbackContext") -> "AntaresBot":
        """在每个command Handler前调用，是指令的前置函数"""
        if self.instance is None:
            raise RuntimeError("command callback method还未获取实例")
        return self.instance.renewStatus(update)

    def __get__(self, instance, cls):
        if instance is None:
            raise TypeError("该装饰器仅适用于方法")
        if self.instance is None:
            self.instance = instance
        return self


# endregion
