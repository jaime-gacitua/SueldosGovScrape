import pandas as pd
import numpy as np
import time
import unicodedata
from selenium import webdriver
import sys
sys.path.append('./lib/')
from functions import *


# parameters
read_file = True
output_file = './output/dept_contract_years_list.csv'

# In case we have already run the spider.
if read_file:
    text_file = open(output_file, "r")
    webpages_list = text_file.readlines()

# Use web spider to get URL list
else:
    webpages_list = getWebpages(output_file)

total_urls = len(webpages_list)
print(total_urls)


# Start crawling the data from each URL
#browser = webdriver.PhantomJS(executable_path='C:/Users/jgaci/Documents/PhantomJSdriver/bin')
#browser = webdriver.PhantomJS()
browser = webdriver.Firefox()

# Text file to log results
myfile = open('./output/visited_pages.csv', 'w')
count_success = 0

for count, i in enumerate(webpages_list):
    success = False

    i = i.strip('\n')

    if count == 0:
        try:
            data = getDatainPage(browser, i)
            success = True
            count_success += 1
        except:
            pass
    else:
        try:
            data1 = getDatainPage(browser, i)
            data = pd.concat([data, data1])
            success = True
            count_success += 1
        except:
            pass

    line_to_write = ''
    line_to_write = line_to_write + str(i) + ',' + str(success) + '\n'
    myfile.write(line_to_write)

    print("Scraped", str(count + 1), "of", str(total_urls), '. Got: ',
        count_success, '\n')

data.to_csv("./output/scraped_data.csv")

myfile.close()

'''
all_links = list()
for y in dept_contract_years_list:
    browser.get(year_link)

    # Find out if we are already in a table page,
    # or we have to dig into months
    check_table = "a"
    try:
        check_table = browser.find_elements_by_tag_name("table")
        print("Found a Table")
    except:
        check_table = "a"

    if check_table == "a":
        try:
            div_months = browser.find_element_by_class_name("linksIntermedios")
            unordered_list_m = div_months.find.element_by_tag_name("ul")
            months_links_list = unordered_list_m.find_elements_by_tag_name("li")
            for l in months_links_list:
                link_anchor_m = l.find_element_by_tag_name("a")
                month_link = link_anchor_m.get_attribute("href")
                all_links.append(month_link)
        except:
            pass
    else:
        all_links.append(y)


print(len(all_links))

myfile = open('./output/all_links.csv', 'wb')
wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
for item in all_links:
    myfile.write("%s\n" % item)



# Prepare webdriver and start scraping

for count, i in enumerate(urls):

    if count == 0:
        data = getDatainPage(browser, i)
    else:
        data1 = getDatainPage(browser, i)
        data = pd.concat([data, data1])
    print("Scraped",count+1,"of",total_urls)

data.to_csv("./output/scraped_data.csv")
'''
