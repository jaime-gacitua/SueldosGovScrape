import pandas as pd
import numpy as np

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException, TimeoutException

import csv

import tqdm
from tqdm import tnrange, tqdm_notebook
tqdm.monitor_interval = 0

import lxml.html
import lxml

import glob

from time import time
import traceback

def listUrlsNames(listWebs):
    """
    Given a list of web objects
    get urls and text
    """
    urls = []
    names = []
    for e in listWebs:
        url = e.get_attribute("href")
        name = e.text

        urls.append(url)
        names.append(name)

    return(urls, names)

def getGovernmentData(output_file, url, browser, num, period):
    """
    Gets all the entities within the government data
    Then dives into each of them to get the data

    Each Entity could be considered a 'Ministerio', 
    but also 'Presidencia de la Republica' is an entity
    """

    browser.get(url)

    # Fetch list of entities to be looked for
    entities = browser.find_elements_by_class_name("primaryCat")
    ent_urls, ent_names = listUrlsNames(entities)

    # Report what we got
    print('Entities:')
    for i, (t, e) in enumerate(zip(ent_names, ent_urls)):
        print('{}.- {}: {}'.format(i,t,e))

    # Fire next level of search
    for name,url in zip(ent_names[num:],ent_urls[num:]):
        print(name)
        getEntityData(output_file, name, url, browser, period)


def getEntityData(output_file, entity, url, browser, period):
    """
    Within an entity there are several departments

    For example 'SENAME' is part of the entity
    'Ministerio de Justicia'

    """

    browser.get(url)
    #entity_data = createCustomDataFrame()

    url_list = []
    departments = browser.find_elements_by_class_name("primaryCat")

    dep_urls, dep_names = listUrlsNames(departments)

    for dept,url in zip(dep_names, dep_urls):
        print(dept)
        getDepartmentData(output_file, entity, dept, url, browser, period)

def getDepartmentData(output_file, entity, dept, url, browser, period):
    """
    For each department we must get both types of personnel
    planta, contrata

    Within each, we get into the yearly data

    """

    type_contract = ['per_planta', 'per_contrata']
    url_list = []
    contracts = []
    years = []

    for t in type_contract:
        dept_contract_link = '{}/{}'.format(url, t)
        browser.get(dept_contract_link)

        try:
            div_years = browser.find_element_by_class_name("linksIntermedios")
            unordered_list = div_years.find_element_by_tag_name("ul")
            years_links_list = unordered_list.find_elements_by_tag_name("li")
            for l in years_links_list:
                link_anchor = l.find_element_by_tag_name("a")
                year_url = link_anchor.get_attribute("href")
                year_text = link_anchor.text
                url_list.append(year_url)
                contracts.append(t)
                years.append(year_text)

        except:
            traceback.print_exc()
            print('No contract data ' + t + ' in ' + url)
            g = open('../data/output/log_error.csv', 'a')
            g.write(url + ',' + 'No contract ' + t + "\n");
            g.close()

    for contract, year, url in tqdm_notebook(zip(contracts, years,url_list)):
        print(contract, year)
        getYearData(output_file, entity, dept, contract, year, url, browser, period)


def getYearData(output_file, entity, dept, contract, year, url, browser, period):

    try:
	    browser.get(url)
    except TimeoutException:
    	print('Timeout Exception')
    	traceback.print_exc()
    	g = open('./output/log_error.csv', 'a')
    	g.write(url + ',' + 'Timeout' + "\n");
    	g.close()


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
    months = []

    # If we have monthly data:
    if monthsdata:
        unordered_list = div_months.find_element_by_tag_name('ul')
        months_links_list = unordered_list.find_elements_by_tag_name('li')

        for m in months_links_list:
            month_link = m.find_element_by_tag_name('a')
            month_url = month_link.get_attribute('href')
            month_text = month_link.text
            url_list.append(month_url)
            months.append(month_text)

    # Else fetch yearly table, we are already there, so month has the flag 'all year'
    else:
        url_list.append(url)
        months = ['allyear']

    for month, url in zip(months, url_list):  # debug purposes
        getDatainPage(output_file, entity, dept, contract, year, month, url, browser, period)


def getDatainPage(output_file, entity, dept, contract, year, month, url, browser, period):
    """
    For a certain year or month we find the actual data

    The data can be in a single page, or split across several pages
    Here we capture the links for all the pages and 
    then call the data extraction

    """
    browser.get(url)

    table_links = []
    table_links.append(url)

    pages = []
    try:
        pagination = browser.find_element_by_class_name("pagination")
        pages = pagination.find_elements_by_tag_name("li")

    except:
        pass
        #print('pagination error: getting li in {}'.format(url))

    try:
        for page in pages:
                try:
                    link_element = page.find_element_by_tag_name("a")
                    link = link_element.get_attribute("href")
                    table_links.append(link)
                except NoSuchElementException:
                    pass

        # Remove the last element, its the back arrow
        if len(table_links) >= 2:
            del table_links[-1]

    except:
        print('pagination error: getting links in {}'.format(url))
        f = open('../data/output/log_error_{}.csv'.format(period), 'a')
        f.write(url +',' + 'Could not get pagination' + "\n");
        f.close()


    total_tables = len(table_links)

    if 'df_visited' not in globals():
    	df_visited = [' ']

    # Loop through all the pages and record data
    # If the page was already visited, carry on.
    for count, url in enumerate(table_links):
        if not (url in df_visited):
                getTableData2(output_file, entity, contract, dept, year, month, url, browser, period)
        else:
                print('Already scraped: ' + url)

def getTableData2(output_file, entity, dept, contract, year, month, url, browser, period):

    try:
        browser.get(url)

    except WebDriverException:
        print ('error page ' + url)
        f = open('../data/output/log_error_{}.csv'.format(period), 'a')
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
        f = open('../data/output/log_error.csv', 'a')
        f.write(url +',' + 'Could not get breadcrumbs' + "\n");
        f.close()
        entity=entity
        department=dept
        type_contract=contract
        year=year
        month=month

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
            #print(row_list)
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
    a = open('../data/output/log_opened_{}.csv'.format(period), 'a')
    a.write(url + ',' + str( time()  ) + "\n");
    a.close()


    try:
        with open(output_file, "a", newline='\n') as f:
            writer = csv.writer(f, delimiter='|', quoting=csv.QUOTE_ALL)
            writer.writerows(master_list)

        a = open('../data/output/log_opened_{}.csv'.format(period), 'a')
        a.write(url + ',' + str( time()  ) + "\n");
        a.close()

    except:
        try:
            # encoding problems
            print('Encoding problems')
            master_list = [[j.encode('utf-8', 'ignore') for j in row] for row in master_list]

            with open(output_file, "a", newline='\n', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter='|', quoting=csv.QUOTE_ALL)
                writer.writerows(master_list)

            a = open('../data/output/log_opened_{}.csv'.format(period), 'a')
            a.write(url + ',' + str( time()  ) + "\n");
            a.close()

        except:
            print ('could not write data from ' + url)
            g = open('./output/log_error_{}.csv'.format(period), 'a')
            g.write(url + ',' + 'Error writing' + "\n");
            g.close()


def cleanLatin(df):
    replace_dict = {'xf3' : 'ó',
                   'xfa' : 'ú',
                   'xed' : 'í',
                   'xf1' : 'ñ',
                   'Ã±' : 'ñ',
                   'AÃ±o' : 'Año',
                   'Ãºb' : 'úb',
                   'rÃ­a' : 'ría',
                   'iÃ³n' : 'ión',
                   'Ã' : 'ñ',
                   'ÃN' : 'ón',
                   '\\r\\n' : ' ',
                   '\\n' : ' ',
                   'Âº': '',
                   'º' : '',
                   'xba' : '',
                   'iÃ³' : 'ió',
                   'GÃA' : 'GÍA',
                   'CIxd3N' : 'CIÓN',
                   'FÃSICA' : 'FÍSICA',
                   'Bxc1SICA' : 'BÁSICA',
                   'INGLÃS' : 'INGLÉS',
                   'Ã­di' : 'ídi',
                   'rãq' : 'ríq',
                   'Ã­a' : 'ía'
                   }

    for key,value in tqdm_notebook(replace_dict.items()):
        for col in df.columns:
            try:
                df.loc[:,col] = df[col].str.replace(key, value)
                df.loc[:,col] = df[col].str.replace('\\', '')
                df.loc[:,col] = df[col].str.replace("^b'", '')
                df.loc[:,col] = df[col].str.replace("'$", '')
            except:
                print('Could not clean column:', col)
