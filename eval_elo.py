import argparse
import json
import os
import random
import math
import re
from datetime import datetime
from collections import defaultdict
from retrying import retry
import threading
import requests
from multiprocessing import Pool, cpu_count
from zhipuai import ZhipuAI
K = 4  # 根据你的新需求设置的 K 值
SCALE = 400  # 评分差异的缩放因子
BASE = 10  # 计算期望胜率的底数
INIT_RATING = 1000  # 所有模型的初始评分

# ANSI 转义码用于红色和蓝色的颜色
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

@retry(wait_fixed=2000, stop_max_attempt_number=10)
def call_api_timelimit(messages):
    class InterruptableThread(threading.Thread):
        def __init__(self, messages):
            threading.Thread.__init__(self)
            self.result = None
            self.messages = messages

        def run(self):
            try:
                key_list=[
                    '']
                
                client=ZhipuAI(api_key=random.choice(key_list))
                response = client.chat.completions.create(
                    model="glm-4-plus", 
                    messages=self.messages
                )
                # parameters = {
                #     "model": "internlm/internlm2_5-7b-chat",
                #     "messages": self.messages
                # }
                # headers = {
                #     "Content-Type": "application/json",
                #     "Authorization": "Bearer "
                # }
                # response = requests.post(
                #     "https://api.siliconflow.cn/v1/chat/completions",
                #     headers=headers,
                #     json=parameters,
                # ).json()
                if 'choices' not in response:
                    raise Exception(f"API调用返回错误: {response}\n")

                response_text = response.choices[0].message.content.strip()
                self.result = response_text
            except Exception as e:
                print(e)

    it = InterruptableThread(messages)
    it.start()
    timeout_duration = 200
    it.join(timeout_duration)
    if it.is_alive() or it.result is None:
        print('API调用超时')
        raise Exception("API调用超时")
    else:
        return it.result


def response(message):
    messages = [{"role": "user", "content": message}]
    return call_api_timelimit(messages)


def compute_elo_rating(target_model_rating, model_rating, result):
    # 计算模型A（目标模型）的期望胜率
    expected_target_model = 1 / (1 + math.pow(BASE, (model_rating - target_model_rating) / SCALE))
    # 计算模型B（对比模型）的期望胜率
    expected_model = 1 / (1 + math.pow(BASE, (target_model_rating - model_rating) / SCALE))

    # 计算新的 Elo 评分
    new_target_model_rating = target_model_rating + K * (result - expected_target_model)
    new_model_rating = model_rating + K * ((1 - result) - expected_model)

    return new_target_model_rating, new_model_rating


def compute_score(evaluation_result, target_model_rating, model_rating, target_model_name, base_model_name, swap):
    review = evaluation_result
    if swap % 2 == 0:
        print('swap:', (swap % 2 == 0))
        try:
            label_content = review.strip()
            label = re.findall(r"\[\[(\d)\]\]", label_content)
            if label:
                label = label[-1]
                if label == "2":
                    print(f"\033[92m{target_model_name}{RESET} wins this task.")
                    return compute_elo_rating(target_model_rating, model_rating, result=1), [1, 0, 0]
                elif label == "1":
                    print(f"{RED}{target_model_name}{RESET} loses this task.")
                    return compute_elo_rating(target_model_rating, model_rating, result=0), [0, 0, 1]
                elif label == "3":
                    print(f"{BLUE}{target_model_name}{RESET} ties this task.")
                    return compute_elo_rating(target_model_rating, model_rating, result=0.5), [0, 1, 0]
                else:
                    return (target_model_rating, model_rating), [0, 0, 0]
                    print(review)
            else:
                return (target_model_rating, model_rating), [0, 0, 0]
        except Exception as e:
            print(e)
            return (target_model_rating, model_rating), [0, 0, 0]
    else:
        try:
            label_content = review.strip()
            label = re.findall(r"\[\[(\d)\]\]", label_content)
            if label:
                label = label[-1]
                if label == "1":
                    print(f"\033[92m{target_model_name}{RESET} wins this task.")
                    return compute_elo_rating(target_model_rating, model_rating, result=1), [1, 0, 0]
                elif label == "2":
                    print(f"{RED}{target_model_name}{RESET} loses this task.")
                    return compute_elo_rating(target_model_rating, model_rating, result=0), [0, 0, 1]
                elif label == "3":
                    print(f"{BLUE}{target_model_name}{RESET} ties this task.")
                    return compute_elo_rating(target_model_rating, model_rating, result=0.5), [0, 1, 0]
                else:
                    return (target_model_rating, model_rating), [0, 0, 0]
                    print(review)
            else:
                return (target_model_rating, model_rating), [0, 0, 0]
        except Exception as e:
            print(e)
            return (target_model_rating, model_rating), [0, 0, 0]



def call_evaluate(target_model_dialogue, base_model_dialogue, information, needs, evaluation_prompt, evaluation_hints, target_model_rating, model_rating, target_model_name, base_model_name, swap):
    if swap % 2 == 0:
        # print(target_model_name, 'vs', base_model_name)
        input_data = evaluation_prompt.format(
            information=information, needs=needs,
            dialogue1=base_model_dialogue, dialogue2=target_model_dialogue, evaluation_hints=evaluation_hints
        )
    else:
        input_data = evaluation_prompt.format(
            information=information, needs=needs,
            dialogue1=target_model_dialogue, dialogue2=base_model_dialogue, evaluation_hints=evaluation_hints
        )
    evaluation_result = response(input_data.strip())
    (new_target_model_rating, new_model_rating), win_loss_update = compute_score(evaluation_result, target_model_rating, model_rating, target_model_name, base_model_name, swap)
    
    # print(win_loss_update)

    return input_data, evaluation_result, new_target_model_rating, new_model_rating, win_loss_update


def load_elo_scores(elo_score_path):
    """加载之前的 Elo 分数，如果不存在，则初始化为初始评分。"""
    if os.path.exists(elo_score_path):
        with open(elo_score_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    # 如果没有历史评分，初始化所有模型的评分为1000
    return defaultdict(lambda: INIT_RATING)


def load_win_loss_record(win_loss_path):
    """加载之前的胜负记录，如果不存在，初始化。"""
    if os.path.exists(win_loss_path):
        with open(win_loss_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    # 初始化为空字典
    return {}


def evaluate_task(task_data):
    swap, target_model_dialogue, base_model_dialogue, information, needs, evaluation_prompt, evaluation_hints, target_model_task_rating, base_model_task_rating, target_model_name, base_model_name = task_data
    
    # print(f"\n{target_model_name} vs {base_model_name}")

    # 调用 Elo 评分函数
    _, _, new_target_model_rating, new_base_model_rating, win_loss_update = call_evaluate(
        target_model_dialogue.strip(),
        base_model_dialogue.strip(),
        information,
        needs,
        evaluation_prompt,
        evaluation_hints,
        target_model_task_rating,
        base_model_task_rating,
        target_model_name,
        base_model_name,
        swap
    )
    
    return new_target_model_rating, new_base_model_rating, win_loss_update


def evaluate_two_models(target_model_result, base_model_result, datasource, previous_elo_scores, win_loss_record, target_model_name, base_model_name, process_count, win_loss_path):
    print(f"{BLUE}Evaluating target model: {target_model_name}{RESET} against {RED}{base_model_name}{RESET}")

    model_ratings = previous_elo_scores  # 使用已有的 Elo 评分，不重新初始化

    task_names = datasource.keys()
    
    # task_names = ['0_股价预测']

    for task_name in task_names:
        # 从历史记录中加载 Elo 分数, 如果不存在则初始化为 1000
        target_model_task_rating = model_ratings.get(target_model_name, {}).get(task_name, INIT_RATING)
        base_model_task_rating = model_ratings.get(base_model_name, {}).get(task_name, INIT_RATING)

        print(f"\nEvaluating task: {task_name}")

        target_model_list = target_model_result[task_name]
        base_model_list = base_model_result[task_name]
        datasource_list = datasource[task_name]

        # 准备传递给进程的数据
        task_data_list = []
        for idx, (target_model_item, base_model_item, data) in enumerate(zip(target_model_list, base_model_list, datasource_list)):
            evaluation_prompt = data["evaluation_prompt"]
            evaluation_hints = data["evaluation_hints"]
            information = data["information"]
            needs = data["needs"]
            
            swap = data["id"]
            
            target_model_dialogue = " ".join([turn["content"] for turn in target_model_item["dialogue"]])
            base_model_dialogue = " ".join([turn["content"] for turn in base_model_item["dialogue"]])

            task_data_list.append((swap, base_model_dialogue, target_model_dialogue, information, needs, evaluation_prompt, evaluation_hints, base_model_task_rating, target_model_task_rating, target_model_name, base_model_name))

        # 使用多进程池并行处理任务
        with Pool(processes=process_count) as pool:
            results = pool.map(evaluate_task, task_data_list)

        # 收集结果并更新 Elo 评分以及胜负记录
        for (new_target_model_rating, new_base_model_rating, win_loss_update) in results:
            target_model_task_rating = new_target_model_rating
            base_model_task_rating = new_base_model_rating

            # 更新胜负记录
            if target_model_name not in win_loss_record:
                win_loss_record[target_model_name] = {}
            if task_name not in win_loss_record[target_model_name]:
                win_loss_record[target_model_name][task_name] = {}
            if base_model_name not in win_loss_record[target_model_name][task_name]:
                win_loss_record[target_model_name][task_name][base_model_name] = [0, 0, 0]

            win_loss_record[target_model_name][task_name][base_model_name] = [
                win_loss_record[target_model_name][task_name][base_model_name][0] + win_loss_update[0],
                win_loss_record[target_model_name][task_name][base_model_name][1] + win_loss_update[1],
                win_loss_record[target_model_name][task_name][base_model_name][2] + win_loss_update[2]
            ]

        print(f"[Task: {task_name}] Updated {BLUE}{target_model_name}{RESET} rating: {target_model_task_rating:.3f}")
        print(f"[Task: {task_name}] Updated {RED}{base_model_name}{RESET} rating: {base_model_task_rating:.3f}")

        # 保存每个任务的 Elo 分数
        if target_model_name not in model_ratings:
            model_ratings[target_model_name] = {}
        if base_model_name not in model_ratings:
            model_ratings[base_model_name] = {}

        model_ratings[target_model_name][task_name] = target_model_task_rating
        model_ratings[base_model_name][task_name] = base_model_task_rating

    # 保存更新后的胜负记录
    with open(win_loss_path, 'w', encoding='utf-8') as file:
        json.dump(win_loss_record, file, indent=4, ensure_ascii=False)

    return model_ratings


def load_model_results(model_folder):
    model_results = {}
    for filename in os.listdir(model_folder):
        if filename.endswith(".json"):
            model_path = os.path.join(model_folder, filename)
            with open(model_path, 'r', encoding='utf-8') as file:
                model_results[filename] = json.load(file)
    return model_results


if __name__ == "__main__":
    # 参数解析器以接受输入参数
    parser = argparse.ArgumentParser(description='使用 Elo 评分系统评估两个模型')

    # 目标模型和基准模型 JSON 文件的路径
    parser.add_argument('--target_model_path', type=str, required=True, help="目标模型 JSON 文件的路径")
    parser.add_argument('--base_model_path', type=str, required=True, help="基准模型 JSON 文件的路径")

    # 数据源 JSON 的路径
    parser.add_argument('--datasource_path', type=str, required=True, help="数据源 JSON 文件的路径")

    # 保存 Elo 评分的路径（默认在 res 文件夹中）
    parser.add_argument('--elo_score_path', type=str, default='res/elo_scores.json', help="保存 Elo 评分的路径")

    # 保存胜负记录的路径（默认在 res 文件夹中）
    parser.add_argument('--win_loss_path', type=str, default='res/win_loss_record.json', help="保存胜负记录的路径")

    # 可选标志以清除之前的 Elo 评分
    parser.add_argument('--clear_elo', action='store_true', help="清除之前的 Elo 评分")

    # 用于并行评估的进程数
    parser.add_argument('--process_count', type=int, default=10, help="用于评估的进程数")

    # 解析提供的参数
    args = parser.parse_args()

    # 从文件路径中提取模型名称以用于显示和存储
    target_model_name = os.path.basename(args.target_model_path).split('_')[2]
    base_model_name = os.path.basename(args.base_model_path).split('_')[2]

    # 确保 res 目录存在，如果不存在则创建它
    res_dir = os.path.dirname(args.elo_score_path)
    if not os.path.exists(res_dir):
        os.makedirs(res_dir)

    # 如果设置了 clear_elo 标志，则删除现有的 Elo 评分文件
    if args.clear_elo and os.path.exists(args.elo_score_path):
        os.remove(args.elo_score_path)

    # 加载之前的 Elo 评分，如果文件不存在则初始化
    previous_elo_scores = load_elo_scores(args.elo_score_path)

    # 加载之前的胜负记录，如果文件不存在则初始化
    win_loss_record = load_win_loss_record(args.win_loss_path)

    # 加载目标模型结果
    with open(args.target_model_path, 'r', encoding='utf-8') as file1:
        target_model_result = json.load(file1)

    # 加载基准模型结果
    with open(args.base_model_path, 'r', encoding='utf-8') as file2:
        base_model_result = json.load(file2)

    # 加载数据源（用于评估提示）
    with open(args.datasource_path, 'r', encoding='utf-8') as file3:
        datasource = json.load(file3)

    # 调用修改后的函数以评估两个模型
    updated_elo_scores = evaluate_two_models(
        target_model_result,
        base_model_result,
        datasource,
        previous_elo_scores,
        win_loss_record,
        target_model_name,
        base_model_name,
        args.process_count,
        args.win_loss_path
    )

    # 在 res 目录中保存比较后的更新 Elo 评分
    with open(args.elo_score_path, 'w', encoding='utf-8') as file:
        json.dump(updated_elo_scores, file, indent=4, ensure_ascii=False)
