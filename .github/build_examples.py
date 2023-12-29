import os

PASS = True
Fails = []

for example in os.listdir("examples"):
    print("Use PIO to build %s" % (example))
    pio_cmd = "pio run -d examples/%s"
    print(pio_cmd)
    ret = os.system(pio_cmd)
    if ret != 0:
        print("%s build fail!" % (example))
        PASS = False
        Fails.append(example)

if PASS:
    print("All examples compiled passed!")
    sys.exit(0)
else:
    print("These examples failed %s" %(Fails))
    sys.exit(1)
