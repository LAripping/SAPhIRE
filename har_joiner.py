#!/usr/bin/python
import sys
import json

if __name__ == "__main__":
    if len(sys.argv)<4:
        print "usage: %s 1.har 2.har [3.har [4.har...]] out.har" % sys.argv[0]
        exit(1)
        
    print "[+] %d harfiles to join" % (len(sys.argv)-2)

    har_files = [i for i in sys.argv[1:-1]]
    joined = {}
    with open(har_files[0]) as first:
        joined = json.load(first)
        print "[+] Got %d entries, as well as the prologue from %s" % (len(joined['log']['entries']), har_files[0])

    for h in har_files[1:]:
        with open(h) as other:
            other_entries = json.load(other)['log']['entries']
            joined['log']['entries'] += other_entries
            print "[+] Added %d entries from %s" % (len(other_entries), h)

    with open(sys.argv[-1],"w") as out:
        out.write( json.dumps(joined, indent=2) )

    print "[+] Finished. %d total entries written to %s" % (len(joined['log']['entries']),sys.argv[-1])
