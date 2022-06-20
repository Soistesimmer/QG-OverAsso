import jsonlines
from transformers import AutoTokenizer

add_prefix = False
tokenizer = AutoTokenizer.from_pretrained('t5-base')

def get_model_input(data):
    data = list(data.values())[0]
    persona = f"[apprentice_persona] {data['apprentice_persona'].strip()}"
    dialog = []
    model_input = []
    tmp = []
    for idx, turn in enumerate(data['dialog_history']):
        action = turn['action'].strip()
        text = turn['text'].strip()
        if action == 'Apprentice => Wizard':
            role = 'Apprentice'
            dialog.append(f"[{role}] {text}")
        elif action == 'Wizard => Apprentice':
            role = 'Wizard'
            if tmp and add_prefix:
                prefix = f"[Search_Query] {', '.join(tmp)} "
                tmp = []
            else:
                prefix = ''
            dialog.append(prefix + f"[{role}] {text}")
        elif action == 'Wizard => SearchAgent':
            role = 'Search_Query'
            tmp.append(text)
        elif action == 'SearchAgent => Wizard':
            continue
        else:
            raise Exception('UNKNOWN ACTION')
        if role == 'Apprentice' and idx < len(data['dialog_history']) - 1:
            model_input.append({
                'dialogue': f"{persona} [dialog_history] {' '.join(dialog[max(0, len(dialog) - 8):])}".lower(),
                'query': []
            })
        elif role == 'Search_Query':
            if model_input:
                model_input[-1]['query'].append(text.lower())
            else:
                model_input.append({
                    'dialogue': f"{persona} [dialog_history] ".lower(),
                    'query': [text.lower()]
                })
        elif role == 'Wizard' and len(model_input) == 0:
            model_input.append({
                'dialogue': f"{persona} [dialog_history] ".lower(),
                'query': []
            })
    return model_input

k_fold = 3
output_dir = f'../../saved_data/data_en'

import os
if not os.path.exists(output_dir):
    os.mkdir(output_dir)


for split in ['train', 'valid', 'test']:
    data = []
    max_len = 0
    with jsonlines.open(f'../../saved_data/wizard_of_interent/{split}.jsonl', 'r') as reader:
        for line in reader:
            model_inputs = get_model_input(line)
            data += model_inputs
            max_len = max(max_len, len(tokenizer.tokenize(data[-1]['dialogue'])))
    print(len(data), max_len)
    # postprocess
    for x in data:
        if len(x['query']) == 0:
            x['query'].append('none')
    output_file = f'../../saved_data/data_en/{split}.json'
    with jsonlines.open(output_file, 'w') as writer:
        for x in data:
            writer.write(x)
    
    if split == 'train':
        for i in range(k_fold):
            with jsonlines.open(f'{output_dir}/{split}_{i}.json', 'w') as writer:
                for j in range(len(data)):
                    if j % k_fold != i:
                        writer.write(data[j])
            with jsonlines.open(f'{output_dir}/{split}_{i}_.json', 'w') as writer:
                for j in range(len(data)):
                    if j % k_fold == i:
                        writer.write(data[j])
    output_file = f'{output_dir}/{split}.json'