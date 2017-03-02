import pandas as pd
import numpy as np

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException

import csv

from tqdm import tnrange, tqdm_notebook

import lxml.html
import lxml

import glob

def getGovernmentData(output_file, url, browser, num):

    gov_data = entity_data = createCustomDataFrame()
    browser.get(url)

    url_list = []
    entities = browser.find_elements_by_class_name("primaryCat")

    counter = 0
    for e in entities:
        entity_url = e.get_attribute("href")
        url_list.append(entity_url)

    print('Entities:')
    print(url_list)
    for url in url_list[num:]: 
        getEntityData(output_file, url, browser)

def getEntityData(output_file, url, browser):
    browser.get(url)
    entity_data = createCustomDataFrame()
    
    url_list =[]
    departments = browser.find_elements_by_class_name("primaryCat")

    for d in departments:
        department_url = d.get_attribute("href")
        url_list.append(department_url)

#    print('Departments:')
#    print(url_list)
    for url in url_list:
        getDepartmentData(output_file, url, browser)

def getDepartmentData(output_file, url, browser):
    
    type_contract = ['per_planta', 'per_contrata']
    url_list = []

    for t in type_contract:
        dept_contract_link = url + "/" + t
        browser.get(dept_contract_link)
        try:
            div_years = browser.find_element_by_class_name("linksIntermedios")
            unordered_list = div_years.find_element_by_tag_name("ul")
            years_links_list = unordered_list.find_elements_by_tag_name("li")
            for l in years_links_list:
                link_anchor = l.find_element_by_tag_name("a")
                year_url = link_anchor.get_attribute("href")
                url_list.append(year_url)
        except NoSuchElementException:
            print ('No contract data in ' + url)
            g = open('./output/log_error.csv', 'a')
            g.write(url + ',' + 'No contract' + "\n");
            g.close()
        
    for url in tqdm_notebook(url_list):
        getYearData(output_file, url, browser)

        
def getYearData(output_file, url, browser):
    
    browser.get(url)
    
    monthsdata = False
    # Check if we still have to dive down into the months
    try:
        div_months = browser.find_element_by_class_name("linksIntermedios")
        monthsdata = True
    except NoSuchElementException:
        div_months = False
        #print(url + ' No months, straight to year' )
        # In this case, we go straight into the yearly tables

    url_list = []
    
    

    # If we have monthly data:
    if monthsdata:

        unordered_list = div_months.find_element_by_tag_name('ul')
        months_links_list = unordered_list.find_elements_by_tag_name('li')

        for m in months_links_list:
            month_link = m.find_element_by_tag_name('a')
            month_url = month_link.get_attribute('href')
            url_list.append(month_url)
            

    # Else fetch yearly table, we are already there
    else:
        url_list.append(url)
    
#    for url in url_list:
#        print(url)
    
    for url in url_list:  # debug purposes
        getDatainPage(output_file, url, browser)

    

def getDatainPage(output_file, url, browser):

    browser.get(url)

    table_links = []
    table_links.append(url)

    try:
        pagination = browser.find_element_by_class_name("pagination")
        pages = pagination.find_elements_by_tag_name("li")

        for page in pages:
            try:
                link_element = page.find_element_by_tag_name("a")
                link = link_element.get_attribute("href")
                table_links.append(link)
            except NoSuchElementException:
                pass

        # Remove the last element, its the back arrow
        del table_links[-1]

    except:
        print ('could not get pagination from ' + url)
        f = open('./output/log_error.csv', 'a')
        f.write(url +',' + 'Error Getting pagination' + "\n");
        f.close()


    total_tables = len(table_links)

    
    # Loop through all the pages and record data
    # If the page was already visited, carry on.
    for count, i in enumerate(table_links):
        if not (i in df_visited):
                getTableData2(output_file, i, browser)
        else:
                print('Already scraped: ' + i)

def getTableData2(output_file, url, browser):

    try:
        browser.get(url)

    except WebDriverException:
        print ('error page ' + url)
        f = open('./output/log_error.csv', 'a')
        f.write(url +',' + 'Reached Error Page' + "\n");
        f.close()
        
    #######
    ### 1 Get table metadata from the breadcrumb (Year, Department, Kind of contract, ...)
    #######

    try:
        table_location_data = browser.find_element_by_class_name("breadcrumb")
        breadcrumb_items = table_location_data.find_elements_by_tag_name("li")
        num_breadcrumbs = len(breadcrumb_items)

        entity = breadcrumb_items[1].text
        department = breadcrumb_items[2].text
        type_contract = breadcrumb_items[3].text
        year = breadcrumb_items[4].text
        if num_breadcrumbs == 6:        
            month = breadcrumb_items[5].text
        else:
            month = 'allyear'

    except (NoSuchElementException, IndexError) as err:
        print ('could not get breadcrumbs from ' + url)
        f = open('./output/log_error.csv', 'a')
        f.write(url +',' + 'Error Reading Page' + "\n");
        f.close()
        entity='entity'
        department='department'
        type_contract='type contract'
        year='year'
        month='month'

    #######
    ### 2 Get Data of table
    #######

#    try:
    root = lxml.html.fromstring(browser.page_source)
    master_list = []

    for row in root.findall('.//tbody//tr'):
        row_list = []
        cells = row.xpath('.//td')

        if len(cells)>0:
            row_list = row_list + [entity, department, type_contract, year, month] 

            for e in cells:
                text = e.xpath('text()')
                if text is None:
                    text = ''
                elif len(text) == 0:
                    text = ''
                else:
                    text = text.pop()
                row_list.append(text) 

            row_list.append(url)
            master_list.append(row_list)

#    except:
#        print(e)
#        print ('could not get table from ' + url)
#        f = open('./output/log_error.csv', 'a')
#        f.write(url +',' + 'Error Reading Table' + "\n");
#        f.close()

    #######
    ### 3 Write into csv files
    #######

    try:
        with open(output_file, "a", newline='\n') as f:
            writer = csv.writer(f)
            writer.writerows(master_list)

        a = open('./output/log_opened.csv', 'a')
        a.write(url + ',' + str( time.time()  ) + "\n");
        a.close()

    except:
        try:
            # encoding problems
            print('Encoding problems')
            master_list = [[j.encode('latin1', 'ignore') for j in row] for row in master_list]
    
            with open(output_file, "a", newline='\n') as f:
                writer = csv.writer(f)
                writer.writerows(master_list)

            a = open('./output/log_opened.csv', 'a')
            a.write(url + ',' + str( time.time()  ) + "\n");
            a.close()

        except:
            print ('could not write data from ' + url)
            g = open('./output/log_error.csv', 'a')
            g.write(url + ',' + 'Error writing' + "\n");
            g.close()
        

def cleanLatin(df):
    replace_dict = {'xf3' : 'ó',
                   'xfa' : 'ú',
                   'xed' : 'í',
                   'xf1' : 'ñ',
                   'Ã±' : 'ñ'}

    for key,value in replace_dict.items():
        for col in tqdm_notebook(df.columns):
            df[col] = df[col].str.replace(key, value)
            df[col] = df[col].str.replace('\\', '')
            df[col] = df[col].str.replace("^b'", '')
            df[col] = df[col].str.replace("'$", '')    
    
    