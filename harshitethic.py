import requests
import json
import os
import threading
import warnings
import yaml
warnings.filterwarnings("ignore")
from revChatGPT.ChatGPT import Chatbot

import asyncio
api_status = {}

with open("./config.yml", "r") as ymlfile:
  cfg = yaml.load(ymlfile, Loader=yaml.SafeLoader)
  
TOKEN_CHATGPT = cfg['telethon']['TOKEN_CHATGPT']
BOT_TOKEN = cfg['telethon']['TELEGRAM_BOT_TOKEN_hung1610']


chatbot = Chatbot({
      "session_token": TOKEN_CHATGPT},
       conversation_id=None, parent_id=None)



def check_user(user):
  with open('users.json', 'r') as f:
    data = json.load(f)
  found = False
  for i, u in enumerate(data['users']):
    if u['name'] == user:
      found = True
      return (found, u['conversation_id'], u['parent_id'])
  return (found, "", "")


def update_or_add_user(user):
  with open('users.json', 'r') as f:
    data = json.load(f)
    
  found = False
  for i, u in enumerate(data['users']):
    if u['name'] == user['name']:
      found = True
      if u['conversation_id'] != user['conversation_id'] or u['parent_id'] != user['parent_id']:
        data['users'][i] = user
        break

  if not found:
    data['users'].append(user)
    
  with open('users.json', 'w') as f:
    json.dump(data, f)


def openAI(prompt, conversation_id=None, parent_id=None):
    global chatbot
    try:
      response = chatbot.ask(prompt, conversation_id=conversation_id, parent_id=parent_id, gen_title=True)
    except:
      chatbot.reset_chat()
      response = chatbot.ask(prompt, gen_title=True)
    return response
  
  
def process_message(prompt, conversation_id, parent_id, username, chat_id, msg_id):
  global api_status
  bot_response = openAI(f"{prompt}", conversation_id, parent_id)
  print(bot_response)
  telegram_bot_sendtext(bot_response['message'], chat_id, msg_id)
  update_or_add_user({
    "name": username,
    "conversation_id": bot_response["conversation_id"],
    "parent_id": bot_response["parent_id"]
  })
  del api_status[conversation_id]
  print(f"api_status: {api_status}")


def wait_for_completion(prompt, conversation_id, parent_id, username, chat_id, msg_id):
    global api_status
    if conversation_id in api_status:
        print('if')
        api_status[conversation_id].wait()
        api_status[conversation_id] = threading.Event()
        t = threading.Thread(target=process_message, args=(prompt, conversation_id, parent_id, username, chat_id, msg_id,))
        t.start()
        print('luồng 2')
    else:
        print('else')
        api_status[conversation_id] = threading.Event()
        t = threading.Thread(target=process_message, args=(prompt, conversation_id, parent_id, username, chat_id, msg_id,))
        t.start()
  

def telegram_bot_sendtext(bot_message,chat_id,msg_id):
    data = {
        'chat_id': chat_id,
        'text': bot_message,
        'reply_to_message_id': msg_id
    }
    response = requests.post(
        'https://api.telegram.org/bot' + BOT_TOKEN + '/sendMessage',
        json=data
    )
    return response.json()

def Chatbot():
    global api_status
    cwd = os.getcwd()
    filename = cwd + '/chatgpt.txt'
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            f.write("1")
    else:
        pass

    with open(filename) as f:
        last_update = f.read()
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update}'
    response = requests.get(url)
    data = json.loads(response.content)

    for result in data['result']:
        # Checking for new message
        if float(result['update_id']) > float(last_update):
            if not result['message']['from']['is_bot']:
                last_update = str(int(result['update_id']))
                msg_id = str(int(result['message']['message_id']))
                chat_id = str(result['message']['chat']['id'])
                
                
                prompt = result['message']['text']
                username = result['message']['from']['id']
                
                found, conversation_id, parent_id = check_user(username)
                t = threading.Thread(target=wait_for_completion, args=(prompt, conversation_id, parent_id, username, chat_id, msg_id,))
                t.start()

                print(result)
                print(f"api_status: {api_status}")
                

                                            
    # Updating file with last update ID
    with open(filename, 'w') as f:
        f.write(last_update)

    return "done"

# 5 Running a check every 5 seconds to check for new messages
def main():
    timertime=1
    Chatbot()

    # 5 sec timer
    threading.Timer(timertime, main).start()

# Run the main function
if __name__ == "__main__":
    main()