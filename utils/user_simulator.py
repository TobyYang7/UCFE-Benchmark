import requests
import threading
from retrying import retry
import json
import os
import random

# 获取当前文件的绝对路径
current_file_path = os.path.abspath(__file__)

# 获取UC_legalbench目录的路径
uc_legalbench_dir = os.path.dirname(os.path.dirname(current_file_path))

# 构建configuration.json的完整路径
CONFIG = os.path.join(uc_legalbench_dir, 'config', 'configuration_gpt.json')


class GPTPerson():
    def __init__(self, data):
        # 从配置文件的person部分读取配置信息
        with open(CONFIG, 'r', encoding='utf-8') as file:
            config = json.load(file)

        person_config = config["person"]
        self.api_key = person_config["gpt_key"]
        self.model_name = person_config.get("model_name", "gpt-4o")  # 默认值为 "gpt-4"
        self.base_url = person_config.get("base_url", "https://api.ai-gaochao.cn/v1/chat/completions")
        self.role = data["role_prompt"]
        self.temperature = 0.7
        self._initial_person(data)

    def _initial_person(self, data):
        if "{information}" in self.role and "{needs}" in self.role:
            self.role = self.role.format(information=data["information"], needs=data["needs"])
        elif "{information}" in self.role:
            self.role = self.role.format(information=data['information'])
        elif "{needs}" in self.role:
            self.role = self.role.format(needs=data['needs'])

        self.temp_messages = [{"role": "system", "content": self.role}]

    @retry(wait_fixed=2000, stop_max_attempt_number=50)
    def call_api_timelimit(self, temperature=None):
        class InterruptableThread(threading.Thread):
            def __init__(self, temp_messages, api_key, model_name, base_url):
                threading.Thread.__init__(self)
                self.result = None
                self.temp_messages = temp_messages
                self.api_key = api_key
                self.model_name = model_name
                self.base_url = base_url
                self.temperature2 = temperature

            def run(self):
                temperature = self.temperature2 if self.temperature2 else 0.7
                try:
                    parameters = {
                        "model": self.model_name,
                        "messages": self.temp_messages,
                        "temperature": temperature,
                        'seed':123,
                        'frequency_penalty':0.5,
                        'presence_penalty':0.5,
                    }

                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    }
                    response = requests.post(
                        self.base_url,
                        headers=headers,
                        json=parameters,
                    ).json()
                    if 'choices' not in response and 'error' in response:
                        raise Exception(response['error']['message'] + '\n' + 'apikey:' + self.api_key)

                    response_text = response["choices"][0]["message"]["content"].strip()
                    resp_tokens=response['usage']['total_tokens']
                    self.result = response_text
                    self.total_tokens=resp_tokens
                except Exception as e:
                    print(e)

        it = InterruptableThread(self.temp_messages, self.api_key, self.model_name, self.base_url)
        it.start()
        # 设置超时时间
        timeout_duration = 200
        it.join(timeout_duration)
        if it.is_alive() or it.result is None:
            print('时间进程出错')
            raise Exception("API调用超时")
        else:
            return it.result,it.total_tokens

    def response(self, message, is_follow_up=False):
        self.temp_messages.append({"role": "user", "content": message})
        try:
            response_text,total_tokens = self.call_api_timelimit()
        except Exception as e:
            response_text = ""
        self.temp_messages.append({"role": "assistant", "content": response_text})
        return response_text,total_tokens

    def initial_response(self):
        try:
            response_text,total_tokens = self.call_api_timelimit(temperature=0.1)
        except Exception as e:
            response_text = ""
        self.temp_messages.append({"role": "assistant", "content": response_text})
        return response_text,total_tokens

    def characters(self):
        return self.temp_messages


# Model类
class GPTTest():
    def __init__(self, data={},model_name='internlm2_5-7b-chat'):
        # 从配置文件的test部分读取配置信息
        with open(CONFIG, 'r', encoding='utf-8') as file:
            config = json.load(file)

        test_config = config["test"]
        self.api_keys = test_config["gpt_key"]
        self.model_name = test_config.get("model_name", "gpt-4")  # 默认值为 "gpt-4"
        self.base_url = test_config.get("base_url", "https://api.ai-gaochao.cn/v1/chat/completions")
        self.data = data

        format_args = {}
        if "{information}" in self.data.get('model_prompt', ''):
            format_args["information"] = self.data.get("information", "")
        if "{needs}" in self.data.get('model_prompt', ''):
            format_args["needs"] = self.data.get("needs", "")
        if format_args:
            self.data['model_prompt'] = self.data['model_prompt'].format(**format_args)

        self.temp_messages = [{"role": "system", "content": self.data.get("model_prompt", "")}]

    @retry(wait_fixed=2000, stop_max_attempt_number=10)
    def call_api_timelimit(self):
        class InterruptableThread(threading.Thread):
            def __init__(self, temp_messages, api_key, model_name, base_url):
                threading.Thread.__init__(self)
                self.result = None
                self.temp_messages = temp_messages
                self.api_keys = api_key
                self.model_name = model_name
                self.base_url = base_url

            def run(self):
                current_key=''
                try:
                    current_key = self.api_keys[0] if len(self.api_keys) == 1 else random.choice(self.api_keys)
                    parameters = {
                        "model": self.model_name,
                        "messages": self.temp_messages,
                        "temperature": 0.5,
                        'seed':123,
                        'frequency_penalty':0.5,
                        'presence_penalty':0.5,
                    }
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {current_key}"
                    }
                    response = requests.post(
                        self.base_url,
                        headers=headers,
                        json=parameters,
                    ).json()
                    if 'choices' not in response and 'error' in response:
                        raise Exception(response['error']['message'] + '\n' + 'apikey:' + current_key)
                    response_text = response["choices"][0]["message"]["content"].strip()
                    resp_tokens=response['usage']['total_tokens']
                    self.result = response_text
                    self.total_tokens=resp_tokens
                except Exception as e:
                    print(e)

        it = InterruptableThread(self.temp_messages, self.api_keys, self.model_name, self.base_url)
        it.start()
        # 设置超时时间
        timeout_duration = 200
        it.join(timeout_duration)
        if it.is_alive() or it.result is None:
            print('时间进程出错')
            raise Exception("API调用超时")
        else:
            return it.result,it.total_tokens

    def response(self, message):
        self.temp_messages.append({"role": "user", "content": message})
        try:
            response_text,total_tokens = self.call_api_timelimit()
        except Exception as e:
            response_text = ""
        self.temp_messages.append({"role": "assistant", "content": response_text})
        return response_text,total_tokens

    def characters(self):
        return self.temp_messages
