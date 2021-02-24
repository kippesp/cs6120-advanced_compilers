import json
import sys

TERMINATORS = 'jmp', 'br', 'ret'

next_block_idx = 0
block_labels_map = {}
initial_block_label = None
blocks_label_sequence = []

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


def form_cfg():
  global block_labels_map
  global blocks_label_sequence

  CFG = {}
  for idx, block_label in enumerate(blocks_label_sequence):
    BB = block_labels_map[block_label]
    last_instr = BB[-1]

    if last_instr['op'] == 'jmp':
      CFG[block_label] = last_instr['labels']
    elif last_instr['op'] == 'br':
      CFG[block_label] = last_instr['labels']
    elif last_instr['op'] == 'ret':
      CFG[block_label] = []
    else:
      if idx < len(blocks_label_sequence) - 1:
        CFG[block_label] = [blocks_label_sequence[idx + 1]]
      else:
        CFG[block_label] = []
  return CFG


def main():
  global block_labels_map
  global initial_block_label
  global blocks_label_sequence

  M = json.load(sys.stdin)
  for F in M['functions']:
    for BB in form_blocks(F['instrs']):
      block_label = get_first_label(BB)
      if not initial_block_label:
        initial_block_label = block_label
      block_labels_map[block_label] = BB
      blocks_label_sequence.append(block_label)
      print(BB)

  CFG = form_cfg()

  for label in blocks_label_sequence:
    print(label)
    print("   ", CFG[label])

if __name__ == '__main__':
  main()
