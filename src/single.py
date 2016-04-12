import argparse
import sys
import time
import httplib

def parse():
	parser = argparse.ArgumentParser(prog='Single Request', description='Lab 5', add_help=True)
        parser.add_argument('-p', '--port', type = int, action='store', help='port number', default=8080)
	parser.add_argument('-n', '--host', action='store', help='host name', default="localhost")
        parser.add_argument('-d', '--debug', action='store_true',help='debug')
        args = parser.parse_args()
        return args

args = parse()

requestbody = args.host + ':' + str(args.port) + "/index.html"
connection = httplib.HTTPConnection(args.host, args.port)

timeList = []

for x in range(1000):
	try:
		stime = time.time()
		connection.request("GET",'/index.html')
		resp = connection.getresponse()
		resp.read()
		etime = time.time()
		timeList.append(etime-stime)
		if int(resp.status) != 200:
			print "Did not return 200"

	except:
		error = sys.exc_info()[0]
		reason = sys.exc_info()[1]
		print str(error)+str(reason)
		break

total = sum(timeList)
ans = total/len(timeList)
print ans
