from twisted.internet import reactor
import atexit, os
from Hatenatools import TMB

#Leafnote RegEx Implementation (Sanitize user-input easily)
import re

fnregex = re.compile("^[A-F0-9_]")

#Leafnote MySQL Implementation (Use a database system that doesn't suck)
import mysql.connector

leafconn = mysql.connector.connect(user="", password="", host="", database="")
leafcur = leafconn.cursor()

#The database handling flipnote files and info
class Database:
	def __init__(self):
		#read database stuff into memory:
		leafcur.execute("CREATE TABLE IF NOT EXISTS `flipnotes` (id INT NOT NULL AUTO_INCREMENT KEY, creatorid VARCHAR(16) NOT NULL, flipnote VARCHAR(24) NOT NULL)")
		leafcur.execute("SELECT creatorid, flipnote FROM `flipnotes` ORDER BY id DESC LIMIT 5000")
		file = [list(i) for i in leafcur.fetchall()]

		self.Newest = file#[creatorID, filename]
		
		self.Creator = {}#to store creator info updates before writing to disk. Creator[id][n] = [filename, views, stars, green stars, red stars, blue stars, purple stars, Channel, Downloads]
		
		self.Views = 0
		self.Stars = 0
		self.Downloads = 0
		
	#interface:
	def CreatorExists(self, CreatorID):
		return os.path.exists("database/Creators/" + CreatorID) or (CreatorID in self.Creator)
	def FlipnoteExists(self, CreatorID, filename):
		return os.path.exists(self.FlipnotePath(CreatorID, filename))
	def GetCreator(self, CreatorID, Store=False):#Returns a list of all the self.GetFlipnote(). "Store" holds it in memory for a while, use this when making changes or reading it often
		if CreatorID in self.Creator:
			return self.Creator[CreatorID]
		else:
			if not os.path.exists("database/Creators/" + CreatorID):
				return None
			
			leafcur.execute("SELECT * FROM `user_%s`" % (CreatorID))
			ret = [list(i) for i in leafcur.fetchall()]
			
			#update to newer format:
			#current format = [filename, views, stars, green stars, red stars, blue stars, purple stars, Channel, Downloads]
			for i in xrange(len(ret)):
				if len(ret[i]) < 9:
					filename = ret[i][0]#take this as a give for now
					for n, default in enumerate((filename, 0, 0, 0, 0, 0, 0, "", 0)):
						if len(ret[i]) <= n:
							ret[i].append(default)
			
			if Store:
				self.Creator[CreatorID] = ret
			
			return ret
	def GetFlipnote(self, CreatorID, filename, Store=False):#returns: [filename, views, stars, green stars, red stars, blue stars, purple stars, Channel, Downloads]
		for i in (self.GetCreator(CreatorID, Store) or []):
			if i[0] == filename:
				return i
		return False
	def GetFlipnotePPM(self, CreatorID, filename):#the ppm binary data
		f = open(self.FlipnotePath(CreatorID, filename), "rb")
		ret = f.read()
		f.close()
		return ret
	def GetFlipnoteTMB(self, CreatorID, filename):#the tmb binary data
		f = open(self.FlipnotePath(CreatorID, filename), "rb")
		ret = f.read(0x6a0)
		f.close()
		return ret
	def AddFlipnote(self, content, Channel=""):#content = ppm binary data
		tmb = TMB().Read(content)
		if not tmb:
			return False
		
		#CreatorID = tmb.Username
		if fnregex.match(tmb.EditorAuthorID):
			CreatorID = tmb.EditorAuthorID
		if fnregex.match(tmb.CurrentFilename[:-4]):
			filename = tmb.CurrentFilename[:-4]
		del tmb
		
		if self.FlipnoteExists(CreatorID, filename):#already exists
			return False
		
		#add to database:
		leafcur.execute("CREATE TABLE IF NOT EXISTS `user_%s` (flipnote VARCHAR(24) NOT NULL KEY, views INT NOT NULL DEFAULT 0, stars INT NOT NULL DEFAULT 0, green_stars INT NOT NULL DEFAULT 0, red_stars INT NOT NULL DEFAULT 0, blue_stars INT NOT NULL DEFAULT 0, purple_stars INT NOT NULL DEFAULT 0, channel VARCHAR(255) NOT NULL DEFAULT '', downloads INT NOT NULL DEFAULT 0)" % CreatorID)
		leafcur.execute("INSERT INTO `flipnotes` (creatorid, flipnote) VALUES ('%s', '%s')" % (CreatorID, filename))
		leafcur.execute("INSERT INTO `user_%s` (flipnote) VALUES ('%s')" % (CreatorID, filename))
		leafconn.commit()
		
		if not self.GetCreator(CreatorID, True):
			self.Creator[CreatorID] = [[filename, 0, 0, 0, 0, 0, 0, Channel, 0]]
		else:
			self.Creator[CreatorID].append([filename, 0, 0, 0, 0, 0, 0, Channel, 0])
		
		#write flipnote to file:
		if not os.path.isdir("database/Creators/" + CreatorID):
			os.mkdir("database/Creators/" + CreatorID)
		f = open(self.FlipnotePath(CreatorID, filename), "wb")
		f.write(content)
		f.close()
		
		return CreatorID, filename
	def AddView(self, CreatorID, filename):
		for i, flipnote in enumerate(self.GetCreator(CreatorID, True) or []):
			if flipnote[0] == filename:
				self.Creator[CreatorID][i][1] = int(flipnote[1]) + 1
				self.Views += 1
				leafcur.execute("UPDATE `user_%s` SET views = %s WHERE flipnote = '%s'" % (CreatorID, self.Views, filename))
				leafconn.commit()
				return True
		return False
	def AddStar(self, CreatorID, filename, amount=1):#todo: add support for other colored stars
		for i, flipnote in enumerate(self.GetCreator(CreatorID, True) or []):
			if flipnote[0] == filename:
				self.Creator[CreatorID][i][2] = int(flipnote[2]) + amount
				self.Stars += 1
				leafcur.execute("UPDATE `user_%s` SET stars = %s WHERE flipnote = '%s'" % (CreatorID, self.Stars, filename))
				leafconn.commit()
				return True
		return False
	def AddDownload(self, CreatorID, filename):
		for i, flipnote in enumerate(self.GetCreator(CreatorID, True) or []):
			if flipnote[0] == filename:
				self.Creator[CreatorID][i][8] = int(flipnote[8]) + 1
				self.Downloads += 1
				leafcur.execute("UPDATE `user_%s` SET downloads = %s WHERE flipnote = '%s'" % (CreatorID, self.Downloads, filename))
				leafconn.commit()
				return True
		return False
	#internal helpers:
	def FlipnotePath(self, CreatorID, filename):#use self.GetFlipnotePPM() instead
		return "database/Creators/%s/%s.ppm" % (CreatorID, filename)
Database = Database()#is loaded, yesth!