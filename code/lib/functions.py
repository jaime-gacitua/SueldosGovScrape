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

from datetime import datetime

import locale
locale.setlocale(locale.LC_ALL, 'es_ES')

from plotly import __version__
from plotly import tools
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot
import plotly.offline as offline
import plotly.graph_objs as go


def listUrlsNames(browser, url, searchStr):
    """
    Searches for available links in an url
    Returns list of urls and text
    """

    browser.get(url)
    items = browser.find_elements_by_class_name(searchStr)

    urls = []
    names = []
    for e in items:
        url = e.get_attribute("href")
        name = e.text

        urls.append(url)
        names.append(name)

    return(urls, names)

def getGovernmentData(output_file, url, browser, period, 
                      cont=['per_planta', 'per_contrata'],
                      start=0, end=999):
    """
    Gets all the entities within the government data
    Then dives into each of them to get the data

    Each Entity could be considered a 'Ministerio', 
    but also 'Presidencia de la Republica' is an entity
    """

    # Fetch list of entities to be looked for
    ent_urls, ent_names = listUrlsNames(browser, url, 'primaryCat')

    # Report what we got
    print('Entities:')
    for i, (t, e) in enumerate(zip(ent_names, ent_urls)):
        print('{}.- {}: {}'.format(i, t, e))


    # Call next level of search
    for entity, url in zip(ent_names[start:end], ent_urls[start:end]):
        print(entity)
        getEntityData(output_file, entity, url, browser, period, cont)


def getEntityData(output_file, entity, url, browser, period, cont):
    """
    Within an entity there are several departments

    For example 'SENAME' is part of the entity
    'Ministerio de Justicia'

    """

    # Fetch list of departments to be looked for
    dep_urls, dep_names = listUrlsNames(browser, url, 'primaryCat')

    # Call next level of search
    for dept,url in zip(dep_names, dep_urls):
        print(dept)
        getDepartmentData(output_file, entity, dept, url, browser, period, cont)

def getDepartmentData(output_file, entity, dept, url, browser, period, cont):
    """
    For each department we must get both types of personnel
    planta, contrata

    Within each, we get into the yearly data

    """

    type_contract = cont
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

    for contract, year, url in tqdm_notebook(zip(contracts, years, url_list)):
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
                getTableData2(output_file, entity, dept, contract, year, month, url, browser, period)
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
                    text = text.replace('\n', '')
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
                   'Ã­a' : 'ía',
                   "^b'" : '',
                   "'$" : '',
                   '\\' : ''
                   }

    for col in tqdm_notebook(df.columns):
        try:            
            for key,value in replace_dict.items():
                    df.loc[:,col] = df[col].str.replace(key, value)
        except:
                print('Could not clean column:', col)


def flipColumns(df, col1, col2, stringIn2):
    startShape = df.shape

    # Involved col2 values that will come to col1
    newCol1s = df.loc[df[col1].str.contains(stringIn2), col2].value_counts()
    
    a = df.loc[df[col1].str.contains(stringIn2)].shape
    b = round((a[0] / df.shape[0])*100,1)
    
    print('{:,} rows of data with flipped {} and {} ({}%)'.format(a[0], col1, col2, b))
    print('Involved {}:'.format(col1,))
    print(newCol1s)

    df[col1].fillna('-1', inplace=True)
    df[col2].fillna('-1', inplace=True)

    df['aux{}'.format(col1)] = [b if stringIn2 in a else a for (a,b) in zip(df[col1], df[col2])]
    df['aux{}'.format(col2)] = [a if stringIn2 in a else b for (a,b) in zip(df[col1], df[col2])]

    df[col1] = df['aux{}'.format(col1)]
    df[col2] = df['aux{}'.format(col2)]

    del df['aux{}'.format(col1)]
    del df['aux{}'.format(col2)]
    
    # Measure results
    a = df.loc[df[col1].str.contains(stringIn2)].shape
    b = round((a[0] / df.shape[0])*100,1)
    print('{:,} rows of data with flipped {} and {} ({}%)'.format(a[0], col1, col2, b))
    endShape = df.shape
    if startShape[0] != endShape[0]:
        print('WARNING DATA SIZE CHANGED')
        print(startShape)
        print(endShape)


def pd_preprocess(df):
    #Format
    df['year'] = df['year'].str.lower()
    df['month'] = df['month'].str.lower()

    #Combine
    df['yearmonth'] = df['year'] + '-' + df['month']

    # Remove keywords
    df['yearmonth'] = df['yearmonth'].str.replace('año ', '')
    df['yearmonth'] = df['yearmonth'].str.replace('a�o ', '')

    # Allyear will be considered january
    df['yearmonth'] = df['yearmonth'].str.strip()
    df['yearmonth'] = df['yearmonth'].str.replace(' ', '')


def pd_stats(df, colCount):
    try:
        print('Coverage before fix:')
        a = pd.notnull(df['datets']).value_counts()
        print(a)
        return(a)
    except:
        print('No date timestamp column. Creating')
        df.loc[:, 'datets'] = datetime(2018,1,1)
        df.loc[:, 'datets'] = None
        a = pd.notnull(df['datets']).value_counts()
        print(a)
        return(a)

def pd_runfix(func, df, colCount, col):
    print('----BEFORE FIX ------')
    before = pd_stats(df, colCount)

    func(df, colCount, col)

    print('----AFTER FIX ------')
    after = pd_stats(df, colCount)

    print('Improved: {}'.format(after-before))

def pd_allyear(df, colCount, col):

    df['aux'] = df[col].str.extract('(\d{4})-allyear', expand=False)
    df['aux2'] = df['aux'] + '-01-01'
    df['aux3'] = pd.to_datetime(df['aux2'], format='%Y-%m-%d')

    df.loc[pd.isnull(df[colCount]), colCount] = df['aux3']

def pd_yearmonth(df, colCount, col):

    df['aux'] = df[col].str.extract('(\d{4} ?-? ?[a-z]+)', expand=False)
    df['aux'] = df['aux'].str.replace(' ', '')

    df['aux2'] = pd.to_datetime(df['aux'], format='%Y-%B', errors='coerce')
    df.loc[pd.isnull(df[colCount]), colCount] = df['aux2']    

    df['aux2'] = pd.to_datetime(df['aux'], format='%Y%B', errors='coerce')
    df.loc[pd.isnull(df[colCount]), colCount] = df['aux2']    


def pd_monthallyear(df, colCount, col):

    df['aux'] = df[col].str.extract('>*([a-z]+)-allyear', expand=False)
    df['aux2'] = '2017-' + df['aux'] + '-01'
    df['aux3'] = pd.to_datetime(df['aux2'], format='%Y-%B-%d', errors='coerce')
    
    df.loc[pd.isnull(df[colCount]), colCount] = df['aux3']


def createSalaryTimeline(df, p, cols):
    
    pdf = df.loc[df['personcat']== p]
    #display(pdf)
    
    # Allyear values
    auxYears = pdf.loc[pdf['month'] == 'allyear']
    auxYears = auxYears.set_index('datets')
    auxYears = auxYears.resample('MS').ffill().reset_index()

    # Not Allyear Values
    auxRest = pdf.loc[pdf['month'] != 'allyear']

    out = pd.concat([auxYears, auxRest])
    out = out.set_index('datets', drop=False)

    # Create list of all indexes
    ixs = []

    date_ranges = pdf.loc[pd.notnull(pdf['start1'] - pdf['end1']),
                          ['start1', 'end1']].drop_duplicates()
    for index,row in date_ranges.iterrows():
        ix = pd.DatetimeIndex(start=row['start1'], end=row['end1'], freq='MS')
        ixs.append(ix)
    
    # If all are none, assume working until end of government
    if len(ixs) == 0:
        pdf['end1'] = datetime(2018,3,31)
        date_ranges = pdf.loc[pd.notnull(pdf['start1'] - pdf['end1']),
                              ['start1', 'end1']].drop_duplicates()

        for index,row in date_ranges.iterrows():
            ix = pd.DatetimeIndex(start=row['start1'], end=row['end1'], freq='MS')
            ixs.append(ix)

        
    # Create union of all indexes
    try:
        if len(ixs) == 1:
            ixsAll = ixs[0]
        else:
            for i in ixs[1:]:
                ixsAll = ixs[0].union(i)

        out1 = out.reindex(ixsAll).sort_index()
        out1 = out1.fillna(method='bfill')
        out1 = out1.fillna(method='ffill')
        out1 = out1.reset_index()
        out1 = out1.rename(columns={'index' : 'date'})
    
    except:
        out1 = pdf.copy()

    # Align columns to original data frame
    # New columns are to the end
    cols = list(df.columns) + [x for x in out1.columns if x not in list(df.columns)]
    out1 = out1.loc[:, cols]
    return(out1)


fixpeople = {'sandra jaqueline millar concha' : 'thousands'}


def plotPeople(df, dateCol='date', amountCol='salary1', highlight=[], titleAdd=''):

	trace1 = go.Scatter(x=df[dateCol],
						y=df[amountCol],
						text=df['person'],
						mode='markers',
						name='Funcionarios')

	add = []
	if len(highlight) > 0:
		for h in highlight:
			aux = df.loc[df['person'].str.contains(h)]
			traceaux = go.Scatter(x=aux[dateCol],
						y=aux[amountCol],
						text=aux['person'],
						mode='line',
						name=h)
			add.append(traceaux)

	data = [trace1] + add

	layout = go.Layout(title='Salary by Person and Year {}'.format(titleAdd), 
					   yaxis=dict(title='Salary'), 
					   xaxis=dict(title='Year'))

	fig = dict(data=data, layout=layout)
	iplot(fig, filename='styled-scatter')


def plotPeopleBox(df, dateCol='date', amountCol='salary1'):

	yrs = df[dateCol].unique()

	data = []
	for y in yrs:
		dfaux = df.loc[df[dateCol] == y]
		traceAux = go.Box(y=dfaux[amountCol], 
						  x=y,
						  name=str(y)[0:4],
						  jitter = 0.3,
						  pointpos = -1.8,
						  boxpoints = 'all',
						  marker = dict(color = 'rgb(7,40,89)'),
						  line = dict(color = 'rgb(7,40,89)')
						)

		data.append(traceAux)

	layout = go.Layout(title='Salary by Person and Year', 
					   width=800,
					   height=600)

	fig = dict(data=data, layout=layout)
	iplot(fig, filename='styled-scatter')


def plotHighStats(df, titleAdd=''):

	cols = df.columns
	data = []
	ynames = ['y', 'y2', 'y3']
	for col, ynam in zip(df.columns, ynames):

		traceaux = go.Scatter(x=df.index, 
							  y=df[col],
							  name=col,
							  yaxis=ynam)
		data.append(traceaux)

	fig = tools.make_subplots(rows=3, cols=1, specs=[[{}], [{}], [{}]],
	                          shared_xaxes=True, shared_yaxes=False,
	                          vertical_spacing=0.1
	                          )

	count = 1
	for trace in data:
		fig.append_trace(trace, count, 1)
		count = count + 1

	#layout = go.Layout(
	#		yaxis1=dict(domain=[0, 0.33], title=cols[0]), 
	#		yaxis2=dict(domain=[0.33, 0.66], title=cols[1]), 
	#		yaxis3=dict(domain=[0.66, 1]), title=cols[2])


	#fig = dict(data=data, layout=layout)

	fig['layout']['yaxis1'].update(title=cols[0], )
	fig['layout']['yaxis2'].update(title=cols[1], )
	fig['layout']['yaxis3'].update(title=cols[2], )
	fig['layout'].update(title='Costo Dotacion por Año {}'.format(titleAdd), 
						 width=1000,
						 height=600)
	
	iplot(fig, filename='stacked-subplots-shared-xaxes')


