import os, sys
for a, b, c in os.walk('/srv/corpus/reports'):
    print(a)
sys.exit(1)
