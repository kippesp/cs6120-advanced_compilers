# Trivial dead code elimination

import click
import json
import sys

import pdb

from pprint import pprint

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

def form_blocks(instrs):
  TERMINATORS = 'jmp', 'br', 'ret'
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
  changed = True

  while changed:
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

      changed = True if workqueue_idx else False

      for idx in workqueue_idx:
        F['instrs'].pop(idx)

  return M

# Module Pass: local value numbering
#
# Removes unused instructions.  A LHS variable definition with no RHS
# uses is dead.
def lvn(M):
  def canonical_lvn_value(I):
    nonlocal lvn_vars

    if I['op'] == 'const':
      lvn_value = (I['op'], I['type'], I['value'])
    else:
      if 'args' not in I:
        raise 'unhandled case of no args'
      sorted_named_args = sorted(I['args'])

      # Convert each named argument to its LVN value
      sorted_args = [lvn_vars[var] for var in sorted_named_args]

      if 'type' in I:
        lvn_value = (I['op'], I['type'], *sorted_args)
      else:
        lvn_value = (I['op'], *sorted_args)
    return lvn_value

  def find_lvn_value(lvn_value_needle):
    nonlocal lvn_table

    for idx in lvn_table:
      lvn_value, lvn_var = lvn_table[idx]

      if lvn_value == lvn_value_needle:
        return idx

  workqueue_fns = []
  for i,F in enumerate(M['functions']):
    workqueue_fns.append((i, F))

  for i,F in workqueue_fns:
    BBs = [BB for BB in form_blocks(F['instrs'])]

    # Only a single basic block is supported
    if len(BBs) > 1:
      continue

    for BB_idx, _ in enumerate(BBs):
      # Initialize LVN table
      #   lvn_table[instruction_idx] = (lvn_value, lvn_var)
      lvn_table = {}

      # Initialize LVN vars table
      #   lvn_vars[lvn_var] = instruction_idx (in lvn_table)
      lvn_vars = {}

      # Initialize LVN values table
      #   lvn_values[lvn_value] = use_count
      lvn_values = {}

      # Initialize LVN value/var table index
      lvn_idx = 1

      for I_idx, I in enumerate(BBs[BB_idx]):
        def reconstruct_I(I):
          nonlocal lvn_value
          nonlocal lvn_table
          nonlocal lvn_vars

          assert(I['op'] != 'const')

          new_I = {'dest' : I['dest'], 'op' : I['op'], 'type' : I['type']}

          # Lookup the instruction creating the canonical definition
          #canonical_instruction_idx = find_lvn_value(lvn_value)

          canonical_args = [lvn_table[lvn_vars[arg]][1] for arg in I['args']]

          new_I['args'] = canonical_args

          return new_I

        if 'op' not in I:
          continue
        if 'dest' not in I:
          continue

        lvn_value = canonical_lvn_value(I)
        lvn_var = I['dest']

        # Has this value been previously computed?
        if lvn_value in lvn_values:
          # Yes, the earlier lvn_value will be the canonical home
          lvn_value_def_idx = find_lvn_value(lvn_value)
          lvn_vars[lvn_var] = lvn_value_def_idx
        else:
          # No, add the lvn_value to the table and make an entry in lvn_vars
          lvn_table[lvn_idx] = (lvn_value, lvn_var)
          lvn_vars[lvn_var] = lvn_idx
          lvn_idx = lvn_idx + 1

        lvn_values[lvn_value] = lvn_values.get(lvn_value, 0) + 1

        # CSE - common sub-expression elimination
        if 'dest' in I and I['op'] != 'const':
          new_I = reconstruct_I(I)
          BBs[BB_idx][I_idx] = new_I

        # TODO: sum2 becomes the ident instruction
        # TODO: mul becomes sum1 mul sum1

    # rewrite function after pass
    M['functions'][i]['instrs'] = []
    for BB in BBs:
      for I in BB:
        M['functions'][i]['instrs'].append(I)

  return M

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
      M = lvn(M)
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
