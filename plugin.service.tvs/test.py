import sys
import os

if __name__=='__main__':
	print os.path.split(os.path.abspath(os.path.dirname(sys.argv[0])))[0]
