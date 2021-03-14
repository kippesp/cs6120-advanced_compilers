# Trivial local dead code elimination
# remove redefined without use
# remove defined but not used instructions in BB

import json
import sys

TERMINATORS = 'jmp', 'br', 'ret'

next_block_idx = 0

def form_blocks(instrs):
  cur_block = []

  for I in instrs:
    if 'op' in I:
      cur_block.append(I)
      if I['op'] in TERMINATORS:
        yield cur_block
        cur_block = []
    else: # a label
      if cur_block:
        yield cur_block
      cur_block = [I]

  if cur_block:
    yield cur_block


def get_first_label(BB):
  global next_block_idx
  label = None
  for I in BB:
    if 'label' in I:
      label = I['label']
      break
  if not label:
    label = 'BB{0}'.format(next_block_idx)
    next_block_idx = next_block_idx + 1
    label_inst = {'label': label}
    BB.insert(0, label_inst)
  return label



def main():
  global next_block_idx
  M = json.load(sys.stdin)
  M2 = M.copy()
  M2['functions'] = []
  for F in M['functions']:
    next_block_idx = 0
    new_BBs = []
    for BB in form_blocks(F['instrs']):
      get_first_label(BB)
      new_BBs.append(BB)

    F['instrs'] = []
    for BB in new_BBs:
      for I in BB:
        F['instrs'].append(I)
    M2['functions'].append(F)

  print(json.dumps(M2))


if __name__ == '__main__':
  main()
