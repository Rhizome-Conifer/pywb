"""
Representation and parsing of HTTP-style status + headers
"""

import pprint


#=================================================================
class StatusAndHeaders(object):
    """
    Representation of parsed http-style status line and headers
    Status Line if first line of request/response
    Headers is a list of (name, value) tuples
    An optional protocol which appears on first line may be specified
    """
    def __init__(self, statusline, headers, protocol=''):
        self.statusline = statusline
        self.headers = headers
        self.protocol = protocol

    def get_header(self, name):
        """
        return header (name, value)
        if found
        """
        name_lower = name.lower()
        for value in self.headers:
            if value[0].lower() == name_lower:
                return value[1]

    def remove_header(self, name):
        """
        remove header (case-insensitive)
        return True if header removed, False otherwise
        """
        name_lower = name.lower()
        for index in xrange(len(self.headers) - 1, -1, -1):
            if self.headers[index][0].lower() == name_lower:
                del self.headers[index]
                return True

        return False

    def __repr__(self):
        headers_str = pprint.pformat(self.headers, indent=2)
        return "StatusAndHeaders(protocol = '{0}', statusline = '{1}', \
headers = {2})".format(self.protocol, self.statusline, headers_str)

    def __eq__(self, other):
        return (self.statusline == other.statusline and
                self.headers == other.headers and
                self.protocol == other.protocol)


#=================================================================
class StatusAndHeadersParser(object):
    """
    Parser which consumes a stream support readline() to read
    status and headers and return a StatusAndHeaders object
    """
    def __init__(self, statuslist):
        self.statuslist = statuslist

    def parse(self, stream):
        """
        parse stream for status line and headers
        return a StatusAndHeaders object

        support continuation headers starting with space or tab
        """
        statusline = stream.readline().rstrip()

        protocol_status = self.split_prefix(statusline, self.statuslist)

        if not protocol_status:
            msg = 'Expected Status Line starting with {0} - Found: {1}'
            msg = msg.format(self.statuslist, statusline)
            raise StatusAndHeadersParserException(msg, statusline)

        headers = []

        line = stream.readline().rstrip()
        while line:
            name, value = line.split(':', 1)
            name = name.rstrip(' \t')
            value = value.lstrip()

            next_line = stream.readline().rstrip()

            # append continuation lines, if any
            while next_line and next_line.startswith((' ', '\t')):
                value += next_line
                next_line = stream.readline().rstrip()

            header = (name, value)
            headers.append(header)
            line = next_line

        return StatusAndHeaders(statusline=protocol_status[1].strip(),
                                headers=headers,
                                protocol=protocol_status[0])

    @staticmethod
    def split_prefix(key, prefixs):
        """
        split key string into prefix and remainder
        for first matching prefix from a list
        """
        for prefix in prefixs:
            if key.startswith(prefix):
                plen = len(prefix)
                return (key[:plen], key[plen:])


#=================================================================
class StatusAndHeadersParserException(Exception):
    """
    status + headers parsing exception
    """
    def __init__(self, msg, statusline):
        super(StatusAndHeadersParserException, self).__init__(msg)
        self.statusline = statusline