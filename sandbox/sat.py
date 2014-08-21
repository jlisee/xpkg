import pycosat

VARS = [
    'A',
    'B1',
    'B2',
    'C1',
    'B3',
    ]

ID_TO_VAR = {}
VAR_TO_ID = {}

# Build translate tables
for idx, var in enumerate(VARS):
    id_ = idx + 1
    ID_TO_VAR[id_] = var
    VAR_TO_ID[var] = id_

def id_to_bool(id_):
    """
    Go -1 -> !A
    """
    isneg = id_ < 0
    bool_ = ID_TO_VAR[abs(id_)]

    if isneg:
        bool_ = '!' + bool_

    return bool_

def bool_to_id(bool_):
    """
    !A -> 1-
    """
    isneg = bool_.startswith('!')
    var = bool_.strip('!')

    id_ = VAR_TO_ID[var]

    if isneg:
        id_ *= -1

    return id_

def do_convert(clauses, func):
    res = []

    for clause in clauses:
        new_clause = []
        for var in clause:
            new_clause.append(func(var))
        res.append(new_clause)

    return res

to_cnf = lambda c: do_convert(c, bool_to_id)
from_cnf = lambda c: do_convert(c, id_to_bool)

# Really basic unit tests on the conversion functions
def check(a,b):
    msg = '"%s" != "%s"' % (a,b)
    assert a == b, msg

check(id_to_bool(-1), '!A')
check(id_to_bool(4), 'C1')
check(bool_to_id('!B1'), -2)
check(bool_to_id('B2'), 3)
check(to_cnf([['A','B1'],['!C1']]), [[1,2],[-4]])
check(from_cnf([[1,2],[-4]]), [['A','B1'],['!C1']])

def run_test(input):
    # Dump input to text
    print 'CLAUSES:'
    for clause in input:
        print ' ',clause

    # Convert to numeric CNF form
    cnf = to_cnf(input)

    # Print results
    print 'SOLUTIONS:'
    for sol in pycosat.itersolve(cnf):
        print ' ',[id_to_bool(i) for i in sol]
    print

# Base case
run_test([['!A', 'B1', 'B2']])

# First test case
case_1 = [
    ['!A', 'B1', 'B2', 'B3'], # A needs B1, B2 or B3
    ['!B1', '!B2'], # B1 and B2 conflict
    ['!B2', '!B3'], # B2 and B3 conflict
    ['!A', 'C1'],   # A needs C1
    ['!C1', 'B2'],  # C1 needs B1
    ]

run_test(case_1)
