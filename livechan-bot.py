import urllib
import urllib2
import cookielib
import os
import json
from socketIO_client import SocketIO
import curses
import thread
import time
import pythonircbot

botName = "myLivechanBot"
botPassword = "somepass"

# initialize IRC bot
livechanBot = pythonircbot.Bot(botName)
livechanBot.connect('irc.freenode.net', verbose=False)
livechanBot.sendMsg('NickServ', 'IDENTIFY '+botName+' '+botPassword)
livechanBot.joinChannel('#livechan')

cookies = cookielib.LWPCookieJar()
handlers = [
    urllib2.HTTPHandler(),
    urllib2.HTTPSHandler(),
    urllib2.HTTPCookieProcessor(cookies)
    ]
opener = urllib2.build_opener(*handlers)

curr_chat_room = None
socketIO = None
mesg_queue = []

def fetch(uri):
    req = urllib2.Request(uri)
    return opener.open(req)

def post(uri, params):
    data = urllib.urlencode(params)
    req = urllib2.Request(uri, data)
    return opener.open(req)

def get_password():
    for cookie in cookies:
        if cookie.name == "password_livechan":
            return cookie.value
    return ""

def post_chat(body, chat, name="Anonymous", convo="General", trip=""):
    post_params = {}
    post_params["name"] = name
    post_params["trip"] = trip
    post_params["body"] = body
    post_params["convo"] = convo
    post_params["chat"] = chat
    return post('https://livechan.net/chat/'+chat, post_params)

def login():
    image_response = fetch('https://livechan.net/captcha.jpg')
    image_data = image_response.read()

    with open('captcha.jpg', 'w') as f:
        f.write(image_data)
    os.system("open captcha.jpg")

    digits = int(raw_input("enter the captcha: "))
    post_params = {}
    post_params["digits"] = digits
    login_response = post('https://livechan.net/login', post_params)
    login_html = login_response.read()

    livechan_pass = get_password()
    if livechan_pass == "":
        login()

    global socketIO
    socketIO = SocketIO('https://livechan.net',
        cookies={'password_livechan': livechan_pass})
    socketIO.on('chat', on_chat)
    thread.start_new_thread ( socketIO.wait, () )


def join_chat(chat_room):
    global curr_chat_room
    global socketIO
    if (curr_chat_room != None):
        socketIO.emit('unsubscribe', curr_chat_room);
    socketIO.emit('subscribe', chat_room);

def display_chat(chat_obj):
    print chat_obj["name"]
    print chat_obj["body"]
    print

def get_data(chat):
    data_response = fetch('https://livechan.net/data/'+chat)
    json_data = json.loads(data_response.read())
    for i in json_data[::-1]:
        display_chat(i)

def main_chat(chat_room):
    chat_body = raw_input("> ")
    if (chat_body == "/quit"):
        return True # break
    mainresp = post_chat(chat_body, chat_room)
    return False
    #print mainresp.read()

def on_chat(*args):
    if (args[0]["name"] == "IRCBot"):
        return
    livechanBot.sendMsg('#livechan', args[0]["name"]+"~ "+args[0]["body"])

def on_user_count(*args):
    print args[0], "users online"
    print

#login
login()

chat_room = raw_input("choose room: ")
join_chat(chat_room)

def relaymsg(msg, channel, nick, client, msgMatch):
    mesg_queue.append(nick+": "+msg)

def main_loop():
    global mesg_queue
    while 1:
        time.sleep(7)
        if len(mesg_queue) > 0:
            post_chat("\n".join(mesg_queue), chat_room, name="IRCBot")
        mesg_queue = []

livechanBot.addMsgHandler(relaymsg)

thread.start_new_thread ( main_loop, () )
livechanBot.waitForDisconnect()

print "done"


