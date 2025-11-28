import json

with open('prototype.ipynb', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'Total cells: {len(data["cells"])}')

if len(data['cells']) > 13:
    print('\n=== Cell 13 ===')
    print(''.join(data['cells'][13]['source']))
    if 'outputs' in data['cells'][13] and data['cells'][13]['outputs']:
        print('\nCell 13 outputs:')
        for output in data['cells'][13]['outputs']:
            if 'text' in output:
                print(''.join(output['text']))
            if 'ename' in output:
                print(f'Error: {output.get("ename", "")}: {output.get("evalue", "")}')
else:
    print('Cell 13 does not exist')

if len(data['cells']) > 14:
    print('\n=== Cell 14 ===')
    print(''.join(data['cells'][14]['source']))
    if 'outputs' in data['cells'][14] and data['cells'][14]['outputs']:
        print('\nCell 14 outputs:')
        for output in data['cells'][14]['outputs']:
            if 'text' in output:
                print(''.join(output['text']))
            if 'ename' in output:
                print(f'Error: {output.get("ename", "")}: {output.get("evalue", "")}')
else:
    print('Cell 14 does not exist')



