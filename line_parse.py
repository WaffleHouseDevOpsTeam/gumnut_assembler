import re
import instr_ref as ref
from pprint import pprint
import sys

def process_file(file_path):
    lines = []
    with open(file_path, 'r') as file:
        for line in file:
            stripped_line = line.strip()  # Remove leading/trailing whitespace
            if stripped_line and not stripped_line.startswith(';;'):
                lines.append(stripped_line)
    
    file.close()
    return lines

commands = process_file(sys.argv[1])
asm_out = open(sys.argv[2], 'w')


def line_parse(line_in):
    line_in = (line_in.split(';;'))[0]
    line_in = re.sub('[,()]', '', line_in)
    line_in = line_in.split(' ')
    return line_in

def convert_2s(n, bit_length):
    n = int(n)
    if n < 0:
        # Handle negative numbers: Add 2^bit_length to wrap around to 2's complement
        n = (1 << bit_length) + n
    # Format the number as binary and pad with leading zeros
    return format(n & ((1 << bit_length) - 1), f'0{bit_length}b')

    
def det_instr(parse_in):
    # "initializing" variables because python is silly
    rd = 'na'
    rs = 'na'
    op2 = 'na'
    cat = 'na'
    fn = 'na'
    count = 'na'
    disp = 'na'
    addr = 'na'
    label = 'na'
    reference_flag = 0
    
    #check for labels 
    if parse_in[0][-1] == ':':
        n = 1
        label = re.sub('[:]', '', parse_in[0])
    else:
        n = 0
    offset = 0
    instr = parse_in[n]
    # check command categories
    if instr in ref.instructions['ari_log']: # arithmetic and logical 
        rd = format(int(re.sub('[r]', '', parse_in[n+1])), '03b')
        rs = format(int(re.sub('[r]', '', parse_in[n+2])), '03b')
        op2 = parse_in[n+3]
        cat = 'ari_log'
        if op2[0] == 'r':
            cat = cat + '_reg'
            op2 = format(int(re.sub('[r]', '', op2)), "03b")
        else:
            cat = cat + '_imm'
            disp = convert_2s(op2, 8)
        offset = 1
    elif instr in ref.instructions['shift']:# shift 
        rd = format(int(re.sub('[r]', '', parse_in[n+1])), '03b')
        rs = format(int(re.sub('[r]', '', parse_in[n+2])), '03b')
        count = format(int(parse_in[n+3]), '03b') 
        cat = 'shift'
    elif instr in ref.instructions['mem_io']: # memory and i/o
        rd = format(int(re.sub('[r]', '', parse_in[n+1])), '03b')
        rs = format(int(re.sub('[r]', '', parse_in[n+2])), '03b')
        disp = convert_2s(parse_in[n+3], 8)
        cat = 'mem_io'
    elif instr in ref.instructions['branch']: # branch
        try: 
            disp = convert_2s(parse_in[n+1], 8)
        except:
            disp = parse_in[n+1]
            reference_flag = 1
        cat = 'branch'
    elif instr in ref.instructions['jump']: # jump
        try:
            addr = int(parse_in[n+1])
        except: 
            addr = parse_in[n+1]
            reference_flag = 1
        cat = 'jump'
    elif instr in ref.instructions['misc']: # misc
        cat = 'misc'
    else: #default (probably cuz error lol)
       offset = 3

    # assign function into binary 
    if offset == 1:
        fn = format(ref.instructions[cat[:-4]].index(instr), '03b')
    elif offset == 0:
        fn = format(ref.instructions[cat].index(instr), '03b')
 
    # throw it all into a nice dictionary
    parsed_instr = {
        'fn':fn,
        'cat':cat,
        'rd':rd,
        'rs':rs,
        'count':count,
        'op2':op2,
        'disp':disp,
        'addr':addr,
        'label':label,
        'ref_flag':reference_flag
    }
   
    return parsed_instr

def arr_instr_p1(z):
    match z['cat']:
        case 'ari_log_reg':
            machine_code = f"1110 {z['rd']} {z['rs']} {z['op2']} 00 {z['fn']}"
        case 'ari_log_imm':
            machine_code = f"0 {z['fn']} {z['rd']} {z['rs']} {z['disp']}"
        case 'shift':
            machine_code = f"110 0 {z['rd']} {z['rs']} {z['count']} 000 {z['fn'][1:]}"
        case 'mem_io':
            machine_code = f"10 {z['fn'][1:]} {z['rd']} {z['rs']} {z['disp']}"
        case 'branch':
            machine_code = f"111110  {z['fn'][1:]} 00 {z['disp']}"
        case 'jump':
            machine_code = f"11110 {z['fn'][2:]} {z['addr']} "
        case 'misc':
            machine_code = f"1111110 {z['fn']} 00000000"

    return machine_code

program = {}
label_positions = {}
for i in range(len(commands)):
    line = commands[i]
    line_1 = line_parse(line)
    if line_1[0][-1] == ':':  # Detect label
        label_name = line_1[0][:-1]
        label_positions[label_name] = i  # Record label's line index
    program[i] = det_instr(line_1)

print("pass 1 is done!")

for i in range(len(commands)):
    if program[i]['disp'] != 'na' and not program[i]['disp'].isdigit():
        search_label = program[i]['disp']
        if search_label in label_positions:
            # Calculate relative displacement (example for branch instructions)
            program[i]['disp'] = convert_2s(label_positions[search_label] - i - 1, 8)
        else:
            print(f"Error: Label '{search_label}' not found.")
    if program[i]['addr'][:2] == '0x':
        program[i]['addr'] = convert_2s(int(program[i]['addr'], 16), 12) 

    if program[i]['addr'] != 'na' and not program[i]['addr'].isdigit():
        search_label = program[i]['addr']
        if search_label in label_positions:
            # Calculate relative displacement (example for branch instructions)
            program[i]['addr'] = convert_2s(label_positions[search_label], 12)
        else:
            print(f"Error: Label '{search_label}' not found.")

print('pass 2 is done!')
for i in range(len(commands)):
    line_3 = re.sub('[ ]', '', arr_instr_p1(program[i]))
    asm_out.write(line_3)
    print(line_3)

print("pass 2 is done!")
