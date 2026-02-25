import json

with open('c:/Users/joe70/PythonProject/Aura/templates/components/voucher_preview_modal.html', 'r', encoding='utf-8') as f:
    text = f.read()

start = text.find('x-data="{') + 8
end = text.find('}"\n@open-voucher-modal', start)

x_data = text[start:end+1]
try:
    print(f"Length of x_data: {len(x_data)}")
    if '"' in x_data[1:-1]:
        print("FOUND DOUBLE QUOTES INSIDE!")
    print("Test passed.")
except Exception as e:
    print(e)
