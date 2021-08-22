import sys
from db_manager import insertDatabase


arg_string = ' '.join(sys.argv[1:])
insertDatabase(arg_string)
