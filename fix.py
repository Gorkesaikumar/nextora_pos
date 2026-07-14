import os

filepath = r"d:\NEXTORA_POS\src\contexts\employees\forms.py"
with open(filepath, "r") as f:
    content = f.read()

content = content.replace("'class': 'form-input'", "'class': 'form-input w-full'")
content = content.replace("'class': 'form-select'", "'class': 'form-select w-full'")

with open(filepath, "w") as f:
    f.write(content)
