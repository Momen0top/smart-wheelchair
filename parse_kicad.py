import re
with open('pcb_extracted/the updated pcb v3.0/the updated pcb v3.0.kicad_sch', encoding='utf-8', errors='ignore') as f:
    text = f.read()
values = set(re.findall(r'property "Value" "([^"]+)"', text))
print("Values found:")
for v in sorted(values):
    print("- " + v)

references = set(re.findall(r'property "Reference" "([^"]+)"', text))
print("\References found:")
for r in sorted(references):
    print("- " + r)
