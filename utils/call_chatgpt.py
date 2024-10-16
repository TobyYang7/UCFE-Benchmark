import requests, json

def call_chatgpt(prompt, system="",model:str="gpt-4"):
    url = "https://api.ai-gaochao.cn/v1/chat/completions"
    api_key = ""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model,
        "messages": [
            {
                'role': 'system',
                'content': system
            },
            {
                'role': 'user',
                'content': prompt
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.8,
    }

    raw_response = requests.post(url, headers=headers, json=payload, verify=False)
    response = json.loads(raw_response.content.decode("utf-8"))

    return response['choices'][0]['message']['content']

if __name__ == "__main__":

    string1 = \
    "帮我改进这个json文件, 你应该输出中文，主要改进的事evaluation的部分:"+"""{
        "role_prompt": "\n你在进行角色扮演，扮演一名普通大众。\n你正在询问AI助手什么是资产负债表\n确保用普通大众的语气与AI助手对话，不要说多余的废话，尽量符合实际情况。\n如果你觉得AI助手的回答满足了你的需求，那你可以按照prompt的指示输出相应的字符。\n请开始你们的对话。\n",
        "model_prompt": "\n你正在向普通大众提供金融咨询服务，在提供服务的过程中，你可以反问对方以获取更多信息。\n",
        "information": "",
        "needs": "",
        "evaluation_prompt": "\n扮演一个公正的评委，评估用户与两个AI助手之间的对话，以判断哪个AI助手为用户提供的服务更好。\n在每段对话中，用户希望AI助手进行金融常识的咨询。\n您的评估需要考虑AI助手回复的准确性以及是否满足用户需求。不要让对话长度影响你的评价。\nAI助手本次服务的评估参考是：{evaluation_hints}\n在进行评估后，严格按照以下格式输出您的最终结论：如果AI助手 1 表现更好，则输出“[[1]]”；如果AI助手 2 表现更好，则“[[2]]”；如果平局，则输出“[[3]]”。\n\n[AI助手1对话开始]\n{dialogue1}\n[AI助手1对话结束]\n\n[AI助手2对话开始]\n{dialogue2}\n[AI助手2对话结束]\n",
        "evaluation_hints": "AI助手必须将其定义为财务报表 ，必须提及该表展示财务状况，鼓励提及针对个人或企业”]",
        "evaluation_points": {
            "answer": "",
            "must_contain": "",
            "at_least_contain": "",
            "should_contain": "1.定义为财务报表；2.展示财务状况；",
            "encourage_contain": "1.针对个人或企业",
            "forbid_contain": ""
        }"""
    response = call_chatgpt(string1)
    print(response)


