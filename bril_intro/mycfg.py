import json
import sys

TERMINATORS = 'jmp', 'br', 'ret'

def form_blocks(I):
  cur_block = []

  for instr in I:
    if 'op' in instr:
      cur_block.append(instr)
      if instr['op'] in TERMINATORS:
        yield cur_block
        cur_block = []
    else: # a label
      yield cur_block
      cur_block = [instr]

  yield cur_block


def main():
  M = json.load(sys.stdin)
  for F in M['functions']:
    for block in form_blocks(F['instrs']):
      print(block)

if __name__ == '__main__':
  main()
