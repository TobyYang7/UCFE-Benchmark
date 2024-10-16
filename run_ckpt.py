import argparse
from utils.user_simulator import GPTPerson, GPTTest, CONFIG
import json
from datetime import datetime
import os
from tqdm import tqdm
import logging  # 引入日志模块

# 定义颜色代码
RED = '\033[91m'    # 提示
GREEN = '\033[92m'  # 用户
ORANGE = '\033[94m'  # 模型
RESET = '\033[0m'

print('\033[94m' + CONFIG + '\033[0m')

# 配置日志记录
log_dir = "log"
os.makedirs(log_dir, exist_ok=True)

# 创建日志文件并清空之前的日志
log_filename = os.path.join(log_dir, "gpt_test_log.txt")
with open(log_filename, 'w'):  # 清空日志文件
    pass
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def load_existing_tasks(output_dir, model_name):
    """加载已有的任务名称和数据"""
    task_set = set()
    task_data = {}
    try:
        for file_name in os.listdir(output_dir):
            if file_name.endswith(f"_{model_name}_eng.json"):
                with open(os.path.join(output_dir, file_name), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    task_set.update(data.keys())
                    task_data.update(data)  # 记录已有任务数据
    except Exception as e:
        logging.error(f"加载已有任务时出错: {e}")
    return task_set, task_data


def save_task_results(output_file, task_name, task_data, loaded_data):
    """将单个任务的结果保存到文件中，并保留已有任务数据"""
    try:
        # 如果文件存在，合并新数据与已有数据
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)  # 读取已有数据
                except json.JSONDecodeError:
                    existing_data = {}  # 如果文件存在但数据有误，初始化为空
        else:
            # 如果文件不存在，初始化为空字典
            existing_data = {}

        # 更新已有的数据，加入新的任务
        existing_data.update(loaded_data)  # 保留之前加载的数据
        existing_data[task_name] = task_data  # 添加新的任务数据

        # 将合并后的数据写回文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)
        print(GREEN + f"任务 {task_name} 的对话已成功保存到 {output_file}" + RESET)

    except IOError as e:
        print(RED + f"保存任务 {task_name} 时出错: {e}" + RESET)
        logging.error(f"保存任务 {task_name} 时出错: {e}")



def test_gpt(model_name, total_data, existing_tasks, output_file, loaded_data):
    # 初始化最终结果为已加载的任务数据
    test_result = loaded_data.copy()

    for task_name in total_data.keys():
        # 如果任务已经存在，将其保留在最终结果中，但不重复处理
        if task_name in existing_tasks:
            print(ORANGE + f"任务 {task_name} 已存在，跳过..." + RESET)
            continue

        test_task_temp = []

        if '0' in task_name:
            name = task_name.split("_")[1]
            print(RED + 'Task Name:', name + RESET)
        else:
            name = task_name
            print(RED + 'Task Name:', name + RESET)

        data_chunk = total_data[task_name]
        total_tokens = 0

        try:
            if task_name.startswith("0_"):
                for data in tqdm(data_chunk, desc="Testing"):
                    dialogue = []
                    data['dialogue_round'] = 1
                    gpt_model = GPTTest(data=data)
                    query = data['model_prompt']

                    # print("---------------------query------------------------")
                    user_turn = {"role": "用户", "content": query}
                    # print(GREEN + f"用户：{query}\n" + RESET)
                    dialogue.append(user_turn)

                    res, total_tokens = gpt_model.response(query)
                    ai_turn = {"role": "AI助手", "content": res}
                    # print(ORANGE + f"AI助手：{res}\n" + RESET)
                    dialogue.append(ai_turn)

                    data['dialogue'] = dialogue
                    data['model'] = model_name
                    data['total_tokens'] = total_tokens
                    test_task_temp.append(data)

                test_result[task_name] = test_task_temp

            else:
                for data in tqdm(data_chunk, desc="Testing"):
                    gpt_user = GPTPerson(data=data)
                    gpt_test = GPTTest(data=data)

                    dialogue = []
                    query, total_tokens = gpt_user.initial_response()
                    user_turn = {"role": "用户", "content": query}
                    dialogue.append(user_turn)

                    # print("---------------------query------------------------")
                    # print(GREEN + f"用户：{query}\n" + RESET)

                    turn_num = 10
                    for round in range(1, turn_num):
                        data["dialogue_round"] = round

                        res, total_tokens = gpt_test.response(query)
                        ai_turn = {"role": "AI助手", "content": res}
                        # print(ORANGE + f"AI助手：{res}\n" + RESET)
                        dialogue.append(ai_turn)

                        if round >= 3:
                            prompt_template = """
                            The information above is the AI assistant's response.
                            Please reply based on your role setting and needs.
                            If your question has been satisfactorily answered, or you have no more questions, please reply with <Consultation Ended>.
                            """
                        else:
                            prompt_template = """
                            The information above is the AI assistant's response.
                            Please reply based on your role setting and needs.
                            If you have any further questions or need additional clarification, feel free to continue asking.
                            """

                        combined_response = f"{res}\n\n{prompt_template}"

                        query, total_tokens = gpt_user.response(combined_response, is_follow_up=True)
                        user_turn = {"role": "用户", "content": query}
                        # print(GREEN + f"用户：{query}\n" + RESET)
                        dialogue.append(user_turn)

                        if "Consultation Ended" in query:
                            break

                    actual_rounds = round
                    # print(RED + f"对话结束，共进行了 {actual_rounds} 轮。\n" + RESET)

                    data['dialogue'] = dialogue
                    data['model'] = model_name
                    data['total_tokens'] = total_tokens
                    test_task_temp.append(data)

                test_result[task_name] = test_task_temp

            # 逐个任务保存结果，将新任务数据和已有任务数据合并保存
            save_task_results(output_file, task_name, test_task_temp, loaded_data)

        except Exception as e:
            print(RED + f"任务 {task_name} 处理失败: {e}" + RESET)
            logging.error(f"任务 {task_name} 处理失败: {e}")

    return test_result


if __name__ == "__main__":

    # 数据地址
    data_path = 'UCFE_bench.json'

    # 模型名称
    with open(CONFIG, 'r', encoding='utf-8') as file:
        config = json.load(file)
    config = config["test"]
    full_model_name = config.get("model_name", "gpt-4o-mini")
    model_name = full_model_name.split('/')[-1]
    print(RED + f"Model Name: {model_name}" + RESET)

    # 读取数据
    if not os.path.exists(data_path):
        print(RED + f"数据文件未找到: {data_path}" + RESET)
        exit(1)

    with open(data_path, 'r', encoding='utf-8') as file:
        try:
            total_data = json.load(file)
        except json.JSONDecodeError as e:
            print(RED + f"JSON解析错误: {e}" + RESET)
            exit(1)

    # 加载已有的任务，避免重复处理
    existing_tasks, loaded_data = load_existing_tasks("log", model_name)

    # 执行测试
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{current_time}_{model_name}_eng.json"
    file_path = os.path.join(log_dir, output_filename)

    # 执行测试并逐个任务保存结果
    test_gpt(model_name, total_data, existing_tasks, file_path, loaded_data)
