from urllib.parse import unquote

# 打开并读取文件
filenam = 'links.txt'
with open(filenam, 'r', encoding='utf-8') as file:
    lines = file.readlines()

# 定义需要过滤的扩展名列表（包含大小写）
extensions_to_filter = {
    'nfo', 'NFO', 'jpg', 'JPG', 'png', 'PNG', 'sh', 'SH',
    'json', 'JSON', 'ini', 'INI', 'js', 'JS', 'ass', 'ASS',
    'srt', 'SRT', 'ssa', 'SSA', 'ttf', 'TTF', 'sfv', 'SFV',
    'sup', 'SUP', 'svg', 'SVG', 'doc', 'DOC', 'webvtt', 'WEBVTT',
    'md', 'MD', 'Atmos','xml'
}

# 过滤掉以指定扩展名结尾的行（支持大小写）
filtered_lines = [
    line for line in lines
    if not unquote(line.strip()).split('.')[-1] in extensions_to_filter
]


# 将过滤后的行写回原文件
with open(filenam, 'w', encoding='utf-8') as file:
    file.writelines(filtered_lines)

print("处理完成，原文件已更新")
# 提取每行的后四位字符，并去重
last_four_chars = set(line.strip()[-4:] for line in lines if len(line.strip()) >= 4)

# 打印去重后的结果
print("文件中所有行的后四位字符（去重后）：")
for chars in last_four_chars:
    print(chars)