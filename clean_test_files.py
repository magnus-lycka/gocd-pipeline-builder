#!/usr/bin/python
import os
import re
import sys
import shutil
from difflib import context_diff

replacements = [
    (r'="\d+\.\d+\.\d+\.\d+"', '="N.N.N.N"'),
    (r'="[a-f\d]+\-[a-f\d]{4}\-[a-f\d]{4}\-[a-f\d]{4}\-[a-f\d]+"', '="UUID"'),
    (r'hostname="[^"]+"', 'hostname="HOST"')
]


def clean(filename):
    fix = 'n'
    with open(filename) as text_file:
        text = text_file.read()
        orig = text[:]
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text)
        if text != orig:
            for line in context_diff(orig.splitlines(),
                                     text.splitlines(),
                                     fromfile=filename,
                                     tofile='new_file'):
                print line
            fix = raw_input('Replace? (y/n)')
    if fix.lower().startswith('y'):
        temp_name = filename + '.before_cleaning'
        shutil.move(filename, temp_name)
        fixed_file = open(filename, 'w')
        fixed_file.write(text)
        fixed_file.close()


def main():
    for root, dirs, files in os.walk('src/texttest'):
        map(clean, (os.path.join(root, fn) for fn in files))


if __name__ == '__main__':
    main()
