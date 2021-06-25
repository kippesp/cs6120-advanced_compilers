# Trivial dead code elimination

import click

import json
import sys

TERMINATORS = 'jmp', 'br', 'ret'
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

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

def tldce(BB):
  # Remove redefined-without-use instructions in local BB
  done = False

  while not done:
    done = True
    unused_defs = {}
    remove_idx = None

    for idx,I in enumerate(BB):
      if 'op' in I:
        if 'args' in I:
          for arg in I['args']:
            if arg in unused_defs:
              unused_defs.pop(arg)
        if 'dest' in I:
          if I['dest'] in unused_defs.keys():
            remove_idx = unused_defs.pop(I['dest'])
            done = False
            break
          else:
            unused_defs[I['dest']] = idx

    if remove_idx:
      BB.pop(remove_idx)
  return BB

def tgdce(F):
  # remove unused instuctions in global; does not consider CF
  done = False

  while not done:
    work_queue = []

    used_defs = {}

    # Find all uses
    for I in F['instrs']:
      if 'op' in I:
        if 'args' in I:
          for arg in I['args']:
            used_defs[arg] = 1

    # Find any unused definitions
    for idx,I in enumerate(F['instrs']):
      if 'op' in I:
        if I['op'] in ['call', 'print']:
          continue
        if 'dest' in I:
          if I['dest'] not in used_defs:
            work_queue.append(idx)

    work_queue.reverse()

    for idx in work_queue:
      F['instrs'].pop(idx)

    done = len(work_queue) == 0

  return F



def main_old():
  global next_block_idx
  M = json.load(sys.stdin)
  M2 = M.copy()
  M2['functions'] = []
  for F in M['functions']:
    next_block_idx = 0
    new_BBs = []
    for BB in form_blocks(F['instrs']):
      get_first_label(BB)
      new_BBs.append(tldce(BB))

    F['instrs'] = []
    for BB in new_BBs:
      for I in BB:
        F['instrs'].append(I)
    M2['functions'].append(F)

  new_Fs = []

  for F in M['functions']:
    new_Fs.append(tgdce(F))

  M['functions'] = new_Fs

  print(json.dumps(M2))

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('-p', '--pass', multiple=True,
              help='Add pass')
def main():
  """BRIL opt

  This does something

  """
  pass


if __name__ == '__main__':
  main()
