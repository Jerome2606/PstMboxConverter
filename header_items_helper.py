class HeaderItemsHelper:
    """ Helps working with the items contained in the transport header af an email message. """

    def __init__(self, email_transport_header):

       self.__items_dictionary = {}
       self.header_to_dict(email_transport_header)
        

    def header_to_dict(self, headers):
        """Convert headers string to a dictionary."""
        header_dict = {}
        current_header_item = ''
        for h_line in headers.splitlines():
            if len(h_line) == len(h_line.lstrip()):
                if ':' in h_line:
                    key, value = h_line.split(':', 1)
                    self.__items_dictionary[key.strip()] = value.strip()
                    current_header_item = key.strip()
            else:
                self.__items_dictionary[current_header_item] += h_line #.strip()[1:]  # Skip leading space/tab character

    
    def get_header_item(self, header_item_name):
        """Get the value of a specific header item, if it exists. 
          If not returning None. Boolean first return Value indicates
          if the value itself at all exists in the transport header."""
        if header_item_name in self.__items_dictionary.keys():
            return True, self.__items_dictionary[header_item_name]
        else:
            return False, None
        
    def contains_header_item(self, header_item_name):
        """Check if a specific header item exists in the transport header."""
        return header_item_name in self.__items_dictionary.keys()
    
    def header_item_names(self):
        """Get all header items as a dictionary."""
        return sorted(self.__items_dictionary.keys())
    
