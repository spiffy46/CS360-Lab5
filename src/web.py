import os
import time
import sys
import socket
import argparse
import errno
import select

class server:
	def __init__(self, p, d):
		self.host = ""
		self.port = p
		self.debug = d
		self.size = 1024
		self.open_socket()
		self.cache = {}
		self.clients = {}
		self.time = {} 
		self.format = '%a, %d %b %Y %H:%M:%S GMT'

	def parseConf(self):
		self.hosts = {}
		self.media = {}
		self.timeout = 1
		with open('web.conf') as fh:
			for line in fh:
				line = line.strip()
				if line == "":
					continue
				try:
					splitline = line.split()
					if splitline[0] == 'host':
						self.hosts[splitline[1]] = splitline[2]
					elif splitline[0] == 'media':
						self.media[splitline[1]] = splitline[2]
					elif splitline[0] == 'parameter' and splitline[1] == 'timeout':
						self.timeout = int(splitline[2])
					else:
						print "web.conf may have been corrupted"
				except:
					print "web.conf has been corrupted"
					sys.exit(0)	

	def open_socket(self):
		try:
			self.server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
			self.server.bind((self.host,self.port))
			self.server.listen(1)
			self.server.setblocking(0)
		except socket.error, (value,message):
			if self.server:
				self.server.close()
			print "Could not open socket: " + message
			sys.exit(0) 

	def start(self):
		self.parseConf()
		if self.debug:
			print "Started Server: " + str(socket.gethostbyname(socket.gethostname()))
		
		self.poller = select.epoll()
		self.pollmask = select.EPOLLIN | select.EPOLLHUP| select.EPOLLERR
		self.poller.register(self.server,self.pollmask)
		while True:
			try:
				fds = self.poller.poll(timeout=self.timeout)
			except:
				continue	
			for (fd,event) in fds:
				if event & (select.POLLHUP | select.POLLERR):
					self.handleError(fd)
					continue
				if fd == self.server.fileno():
					self.handleServer()
					continue
				result = self.handleClient(fd)
			self.sweep()	
	def handleServer(self):
		while True:
			try:
				(client,address)= self.server.accept()
			except socket.error, (value,message):
				if value == errno.EAGAIN or errno.EWOULDBLOCK:
					return
				print traceback.format_exc()
				sys.exit()
			client.setblocking(0)
			self.clients[client.fileno()] = client
			self.poller.register(client.fileno(),self.pollmask)
			if self.debug:
				print "handleServer has added a client... " +str(client.fileno())

	def handleError(self,fd):
		self.poller.unregister(fd)
		if fd == self.server.fileno():
			if self.debug:
				print "handleError has reset socket"
			self.server.close()
			self.open_socket()
			self.poller.register(self.server,self.pollmask)
		else:
			if self.debug:
				print "handleError has closed a client"
			self.clients[fd].close()
			del self.clients[fd]
			if fd in self.time:
				del self.time[fd]

	def handleClient(self, fd):
		if fd not in self.cache:
			self.cache[fd] = ""
		self.time[fd] = time.time()
		while True:
			try:
				request = self.clients[fd].recv(self.size) 
			except socket.error, (value,message):
				if value == errno.EAGAIN or errno.WOULDBLOCK:
					return
				print traceback.format_exc()
				sys.exit()
			self.cache[fd] += request	
			if '\r\n\r\n' in self.cache[fd]:
				self.cache[fd] = self.cache[fd][:request.find('\r\n\r\n')]
				break
			if not request:
				break

		request = self.cache[fd]
		self.cache[fd] = ""
		if self.debug:
			print "Got request:\n" + request 
		if request:
			response = self.generateResponse(request)
			
			if self.debug:
				print "Sending response:\n" + response 
			rlen = len(response)
			s = 0 
			while s < rlen:
				try:	
					sent = self.clients[fd].send(response[s:])
					s+=sent
				except socket.error, (value,message):
					if value == errno.EAGAIN or errno.WOULDBLOCK:
						continue
					print traceback.format_exc()
					sys.exit()
		else:
			if self.debug:
				print "Closing connection: " + str(fd) 	
			self.poller.unregister(fd)
			self.clients[fd].close()
			del self.clients[fd]
			del self.time[fd]	

	def sweep(self):
		ctime = time.time()
		toDel = []
		for f in self.time:
			if ctime - self.time[f] > self.timeout:
				if self.debug:
					print "Closing connection: " + str(f)
				toDel.append(f)

		for f in toDel:
			self.poller.unregister(f)
			self.clients[f].close()
			del self.clients[f]
			del self.time[f]
	def generateResponse(self, request):
		requestList = request.split('\r\n')
		line = requestList[0].split()
		if line[0] == 'GET':
			url = line[1]
			self.host = self.hosts['default']
			if 'Host:' in request:
				splt = request.split()
				h = splt[splt.index('Host:')+1]
				if h in self.hosts:
					self.host = self.hosts[h]
			response = self.handleGET(url)
		else:
			body = '<html><body><h2>Only GET Requests</h2>Server can only handle GET requests for now</body><html>'
			response = 'HTTP/1.1 501 Bad Request\r\nDate: ' + self.getTime() + '\r\nServer: AwesomeServ1.0\r\nContent-Type: text/html\r\nContent-Length: ' + str(len(body)) + '\r\n\r\n' + body
		return response
	
	def handleGET(self, url):
		filename = url	
		if url[-1] == '/':
			filename = url + 'index.html'
		filename = self.host + filename
		try:
			mediaType = 'text/html'
			if '.' in filename:
				ext = filename.split('.')[-1]
				if ext in self.media:
					mediaType = self.media[filename.split('.')[-1]]
				else:
					raise IOError(1, "Bad Extension")
			f = open(filename)
			date = self.getTime()
			response = 'HTTP/1.1 200 Ok\r\nDate: ' + self.getTime() + '\r\nServer: AwesomeServ1.0\r\nContent-Type: ' + mediaType + '\r\n'
			body = f.read()
			response = response + 'Content-Length: ' + str(os.stat(filename).st_size) + '\r\nLast-Modified: ' + self.lastModified(filename)  + '\r\n\r\n' + body

			return response
		except IOError as (errno,strerror):
			if errno == 13:
				body = '<html><body><h1>403</h1>403: Forbidden</body></html>'
				return 'HTTP/1.1 403 Forbidden\r\nDate: ' + self.getTime() + '\r\nServer: AwesomeServ1.0\r\nContent-Type: text/html\r\nContent-Length: ' + str(len(body)) + '\r\n\r\n' + body
			elif errno == 2:
				body = '<html><body><h1>404</h1>404: Not Found</body></html>'
				return 'HTTP/1.1 404 Not Found\r\nDate: ' + self.getTime() + '\r\nServer: AwesomeServ1.0\r\nContent-Type: text/html\r\nContent-Length: ' + str(len(body)) + '\r\n\r\n' + body
			else:
				body = '<html><body><h1>500</h1>500: Internal Server Error</body></html>'
				return 'HTTP/1.1 500 Internal Server Error\r\nDate: ' + self.getTime() + '\r\nServer: AwesomeServ1.0\r\nContent-Type: text/html\r\nContent-Length: ' + str(len(body)) + '\r\n\r\n' + body

	def getTime(self):
		t = time.time()
		gmt = time.gmtime(t)
		date = time.strftime(self.format,gmt)
		return date

	def lastModified(self,file):
		t = os.stat(file).st_mtime
		gmt = time.gmtime(t)
		date = time.strftime(self.format,gmt)
		return date
def parse():
	parser = argparse.ArgumentParser(prog='Web Server', description='Lab 4', add_help=True)
	parser.add_argument('-p', '--port', type = int, action='store', help='port number', default=8080)
	parser.add_argument('-d', '--debug', action='store_true',help='debug')
	args = parser.parse_args()
	return args

args = parse()

s = server(args.port,args.debug)
s.start()
