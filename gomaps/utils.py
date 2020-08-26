# -*- coding: utf-8 -*-
'''
Author: David J. Morfe
Application Name: gomaps.utils
Functionality Purpose: Provides utility functions with some also useful for external consumption
Version: Beta
'''
#8/26/20

import requests, time, os, sys, re
import pyppdf.patch_pyppeteer
from requests_html import HTMLSession
from urllib.parse import quote_plus, unquote_plus
from GeoLiberator import parse_address

__MQ = "https://www.google.com/maps?q="
__SQ = "https://www.google.com/search?q="

def __direct_google_maps(q: str) -> str: # returns the HTML from a Google Maps query
   oq = re.sub(__MQ, '', q.replace('+', ' '))
   query = __MQ + quote_plus(oq)
   resp = requests.get(query)
   return str(resp.text)

def __direct_google_search(q: str) -> str: # returns the HTML from a Google Search query
   session = HTMLSession()
   resp = session.get(__SQ + quote_plus(q))
   resp.html.render()
   return str(resp.html.html)

def __clean_location(location: str) -> str: # returns cleaned address otherwise returns location
   addr = parse_address(location, "full")
   if addr != "OTHER":
      return addr
   else:
      return location

def __is_address(location: str) -> str:
   addr = parse_address(location, "full")
   if addr == "OTHER":
      addr = parse_address(location, "address")
      if addr == "OTHER":
         return False
   return addr

def geocoder(location, reverse: bool=False) -> tuple: # gets geographical lat/long coordinates
   '''Note: this function is especially lightweight as opposed to using maps_search'''
   if not reverse:
      q = __clean_location(str(location))
      html = __direct_google_maps(q)
      try:
         url_components = re.search(
            r'https://www.google.com/maps/preview/place/.+?\\"', html)
         coords = re.search(r"@-?\d\d?\.\d{4,8},-?\d\d?\.\d{4,8}",
                            url_components.group()).group()
         return tuple(coords.strip('@').split(','))
      except (TypeError, AttributeError):
         return None
   else:
      pass

def get_url(data: str) -> str: # parses new url
   if len(data) > 128:
      try:
         url_components = re.search(
            r'https://www.google.com/maps/preview/place/.+?\\"', data)
         prefix = re.sub(r"\?q=", "/place/", __MQ).replace('+', "\+")
         path = re.search(fr'{prefix}.+?/data.+?\\"', data).group()
         path = re.sub(r"\\\\u003d", '=', path)
         coords = re.search(r"@-?\d\d?\.\d{4,8},-?\d\d?\.\d{4,8}",
                            url_components.group()).group()
         path = re.sub(r"/data", f"/{coords},17z/data", path)
         url = path[:-11] + "!8m2!3d" + re.sub(r",", "!4d", coords.strip('@'))
         return url
      except (TypeError, AttributeError):
         return None
   else:
      html = __direct_google_maps(data)
      return get_url(html)

def get_title(data: str) -> str: # parses title
   if len(data) > 128:
      try:
         url_components = re.search(
            r'https://www.google.com/maps/preview/place/.+?\\"', data)
         prefix = re.sub(r"\?q=", "/place/", __MQ).replace('+', "\+")
         path = re.search(fr'{prefix}.+?/data.+?\\"', data).group()
         path = re.sub(r"\\\\u003d", '=', path)
         coords = re.search(r"@-?\d\d?\.\d{4,8},-?\d\d?\.\d{4,8}",
                            url_components.group()).group()
         path = re.sub(r"/data", f"/{coords},17z/data", path)
         url = path[:-11] + "!8m2!3d" + re.sub(r",", "!4d", coords.strip('@'))
         title = re.search(r"(?<=https://www.google.com/maps/place/)\w+.*?/@",
                           url).group().strip("/@")
         return unquote_plus(title)
      except (TypeError, AttributeError):
         return None
   else:
      html = __direct_google_maps(data)
      return get_title(html)

def get_address(data: str, validate=False): # parses address
   if len(data) > 128:
      address = None
      if validate:
         address = re.search(r"title=\"Map of .+?\"",
                             data)
         if address:
            return address.group().replace("title=\"Map of ", '').strip('"')
      if address == None:
         try:
            address = re.search(r"Address</a>: </span>.+?</span>",
                                data)
            return re.sub(r"Address</a>: </span>.+?>", '',
                          address.group()).strip("</span>")
            return address
         except (TypeError, AttributeError):
            return None
   else:
      q = __clean_location(str(data))
      if q != "OTHER":
         validate = True
      html = __direct_google_search(q)
      return get_address(html, validate)

def get_website(data: str) -> str: # parses website
   if len(data) > 128:
      try:
         website1 = re.search(r"Web results.+?onmousedown",
                              data)
         website2 = re.search(r"Web Result with Site Links.+?href=\".+?\"",
                              data)
         if not website1:
            return re.sub(r"Web results.+?href=\"", '',
                          website2.group()).strip('"')
         else:
            return re.sub(r"Web results.+?href=\"", '',
                          website1.group()).strip('" onmousedown')
      except (TypeError, AttributeError):
         return None
   else:
      html = __direct_google_search(data)
      return get_website(html)

def get_phone_number(data: str) -> str: # parses phone number
   if len(data) > 128:
      try:
         phone = re.search(r"Phone</a>: </span>.+?</span>", data)
         return re.search(r"\(?\d{3}\)? \d{3}-\d{4}", phone.group()).group()
      except (TypeError, AttributeError):
         return None
   else:
      html = __direct_google_search(data)
      return get_phone_number(html)

def get_rating(data: str) -> float: # parses rating
   if len(data) > 128:
      try:
         rating = re.search(r"Rated \d\.?\d? out of 5", data)
         return float(rating.group().strip(" out of 5").strip("Rated "))
      except (TypeError, AttributeError):
         return None
   else:
      html = __direct_google_search(data)
      return get_rating(html)

def get_open_hours(data: str) -> dict: # parses open hours
   if len(data) > 128:
      try:
         hours = re.search(r"Hours</a>: </span>.+?</table>", data)
         current = re.search(r"(Opens|Close[sd])( soon)?</b>...((Opens|Closes) \d{1,2}(AM|PM))",
                             data)
         if current:
            current = f"{current.group(1)} - {current.group(3)}"
         return (hours.group(), current)
      except (TypeError, AttributeError):
         return None
   else:
      html = __direct_google_search(data)
      return get_open_hours(html)

def get_popular_times(data: str) -> dict: # parses popular times
   if len(data) > 128:
      try:
         pop_times = re.findall(r"\[\d{1,3},\d{1,3},\d{1,3},\d{1,3},\d{1,3},\d{1,3},\d{1,3},\d{1,3},\d{1,3},"\
                                "\d{1,3},\d{1,3},\d{1,3},\d{1,3},\d{1,3},\d{1,3},\d{1,3},\d{1,3},\d{1,3}\].+?(?:No )?wait",
                                data)
         if pop_times:
            return pop_times
      except (TypeError, AttributeError):
         return None
   else:
      html = __direct_google_search(data)
      return get_popular_times(html)

def attrs_switch(self, data: str, attrs: list):
   if "address" in attrs and self.__dict__["address"] == None:
      self.address = get_address(data)
   if "website" in attrs and self.__dict__["website"] == None:
      self.website = get_website(data)
   if "phone_number" in attrs and self.__dict__["phone_number"] == None:
      self.phone_number = get_phone_number(data)
   if "rating" in attrs and self.__dict__["rating"] == None:
      self.rating = get_rating(data)
   if "open_hours" in attrs and self.__dict__["open_hours"] == {}:
      hours_results = get_open_hours(data)
      if hours_results[1] != None:
         self.open_hours["Currently"] = hours_results[1]
      self._GoogleMaps__set_hours(hours_results[0])
   if "popular_times" in attrs and self.__dict__["popular_times"] == {}:
      ptimes = get_popular_times(data)
      if ptimes != None:
         self._GoogleMaps__set_pop_times(ptimes)

def values_switch(self, attrs: list) -> dict:
   values = {}
   for attr in attrs:
      if attr not in values:
         values[attr] = self.__dict__[attr]
   return values