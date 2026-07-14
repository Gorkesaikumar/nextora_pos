import os

filepath = r"d:\NEXTORA_POS\src\contexts\employees\forms.py"
with open(filepath, "r") as f:
    content = f.read()

content = content.replace("'class': 'form-input w-full'", "'class': 'input'")
content = content.replace("'class': 'form-select w-full'", "'class': 'select'")
content = content.replace("'class': 'form-input'", "'class': 'input'")
content = content.replace("'class': 'form-select'", "'class': 'select'")

with open(filepath, "w") as f:
    f.write(content)
