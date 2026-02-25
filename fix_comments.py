import re

filepath = 'c:/Users/joe70/PythonProject/Aura/templates/components/voucher_preview_modal.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('x-data="{')
end = content.find('}"\n@open-voucher-modal', start)
xdata = content[start:end]

# Replace // with /* */ inside xdata
# Only lines that have //
new_xdata_lines = []
for line in xdata.split('\n'):
    if '//' in line:
        parts = line.split('//', 1)
        new_line = parts[0] + '/* ' + parts[1].strip() + ' */'
        new_xdata_lines.append(new_line)
    else:
        new_xdata_lines.append(line)

new_xdata = '\n'.join(new_xdata_lines)
final_content = content[:start] + new_xdata + content[end:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(final_content)

print("done")
