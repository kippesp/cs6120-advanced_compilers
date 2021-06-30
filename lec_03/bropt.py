# Trivial dead code elimination

import click

import json
import sys

TERMINATORS = 'jmp', 'br', 'ret'
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

# next_block_idx = 0

#def form_blocks(instrs):
#  cur_block = []
#
#  for I in instrs:
#    if 'op' in I:
#      cur_block.append(I)
#      if I['op'] in TERMINATORS:
#        yield cur_block
#        cur_block = []
#    else: # a label
#      if cur_block:
#        yield cur_block
#      cur_block = [I]
#
#  if cur_block:
#    yield cur_block


#def get_first_label(BB):
#  global next_block_idx
#  label = None
#  for I in BB:
#    if 'label' in I:
#      label = I['label']
#      break
#  if not label:
#    label = 'BB{0}'.format(next_block_idx)
#    next_block_idx = next_block_idx + 1
#    label_inst = {'label': label}
#    BB.insert(0, label_inst)
#  return label

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


def is_single_BB(M):
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

# Module Pass: normalize basic blocks
#
# Creates default label at start of each basic block if no label exists.
def normbbs(M):
  workqueue_fns = []
  for i,F in enumerate(M['functions']):
    workqueue_fns.append((i, F))

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

  next_block_idx = 0

  def normalize_first_label(BB):
    nonlocal next_block_idx

    label = None
    for I in BB:
      if 'label' in I:
        label = I['label']
        break
    if not label:
      label = 'BB{0}'.format(next_block_idx)
      next_block_idx = next_block_idx + 1
      label_inst = {'label': label, 'metalabel': 1}
      BB.insert(0, label_inst)
    return label

  for i,F in workqueue_fns:
    next_block_idx = 0

    BBs = [BB for BB in form_blocks(F['instrs'])]

    for idx,_ in enumerate(BBs):
      normalize_first_label(BBs[idx])

    # Now that all BBs are labeled, recreate the function using the
    # BB instructions.

    new_F = []
    for BB in BBs:
      for I in BB:
        new_F.append(I)
    M['functions'][i]['instrs'] = new_F

  return M

# Module Pass: clean meta data
#
# Removes unnecessary labels added by normbbs pass
def cleanmeta(M):
  workqueue_fns = []
  for i,F in enumerate(M['functions']):
    workqueue_fns.append((i, F))

  workqueue_idx = []

  for i,F in workqueue_fns:
    for idx,I in enumerate(F['instrs']):
      if 'label' in I and 'metalabel' in I:
        if I['metalabel'] == 1:
          workqueue_idx.append(idx)

    workqueue_idx.reverse()

    for idx in workqueue_idx:
      F['instrs'].pop(idx)

  return M


# Module Pass: trivial dead code elimination
#
# Removes unused instructions.  A LHS variable definition with no RHS
# uses is dead.
def tdce(M):
  workqueue_fns = []
  for i,F in enumerate(M['functions']):
    workqueue_fns.append((i, F))

  for i,F in workqueue_fns:
    used_defs = {}
    workqueue_idx = []

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
            workqueue_idx.append(idx)

    workqueue_idx.reverse()

    for idx in workqueue_idx:
      F['instrs'].pop(idx)

  return M

import pdb

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--passes', '-p', help='Add passes')
@click.option('--filename', '-f', help='Input filename')
@click.option('--passthru', is_flag=True, help='Skip all passes')
def main(passes, filename, passthru):
  """BRIL opt

  Available optimization passes:

  tdce - trivial dead code elimination

      Global pass to remove obvious dead instructions.  This pass can operate
      on multiple basic blocks.

  lvn - local value numbering

      Adds metadata for follow on optimizations

  normbbs - normalize all basic blocks to have a label

      Finds all basic blocks and creates default label if necessary.

  cleanmeta - clean meta data added by earlier passes

      Removes meta labels not required for control flow.

  OPTIONS:

  -p PASSLIST, --optpass=PASSLIST
      Comma-separated list of passes to apply; can be used multiple times,
      as in -p tdce -p copy_prop.
  """
  if passes:
    if ',' in passes:
      passes = passes.split(',')
    else:
      passes = [passes]

  if filename:
    file_contents = open(filename, 'r').read()
    M = json.loads(file_contents)
  else:
    M = json.load(sys.stdin)

  # module pass - trivial dead code elimination
  while not passthru and len(passes):
    if passes[0] == 'tdce':
      M = tdce(M)
      passes = passes[1:]
    elif passes[0] == 'normbbs':
      M = normbbs(M)
      passes = passes[1:]
    elif passes[0] == 'lvn':
      #M = lvn(M)
      passes = passes[1:]
    elif passes[0] == 'cleanmeta':
      M = cleanmeta(M)
      passes = passes[1:]
    else:
      print("Unknown pass:", passes[0])
      sys.exit(1)

  print(json.dumps(M))

  return 0


if __name__ == '__main__':
  ret = main()
  sys.exit(ret)
