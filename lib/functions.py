import pandas as pd
import numpy as np
import time
import unicodedata
from selenium import webdriver

def createCustomDataFrame():
   
    columns = ['entity', 'department', 'type_contract', 'year', 'month', 'Estamento', 'Apellido paterno', 'Apellido materno', 'Nombres', 'Grado EUS',	'Calificación profesional o formación', 'Cargo', 'Región',	'Asignaciones especiales', 'Unidad monetaria', 'Remuneración Bruta Mensualizada', 'Horas extraordinarias', 'Fecha de inicio', 'Fecha de término', 'Observaciones']
    
    df = pd.DataFrame(columns=columns)
    df = FixColumnNames(df)
    
    return(df)



def FixColumnNames(df):

#    columns = ['Apellido paterno', 'Apellido materno', 'Nombres']
    for c in df.columns:
        df[c] = df[c].str.lower()
        df[c] = df[c].str.replace('á', 'a')
        df[c] = df[c].str.replace('é', 'e')
        df[c] = df[c].str.replace('í', 'i')
        df[c] = df[c].str.replace('ó', 'o')
        df[c] = df[c].str.replace('ú', 'u')
        df[c] = df[c].str.replace(' ', '_')
        

    df['Remuneración Bruta Mensualizada'] = df['Remuneración Bruta Mensualizada'].replace(to_replace = "\.+", value="", regex=True)

    return(df)


def getGovernmentData(output_file, url, browser, numEnt):

    gov_data = entity_data = createCustomDataFrame()
    browser = webdriver.Firefox()
    browser.get(url)

    entities = browser.find_elements_by_class_name("primaryCat")

    counter = 0
    for e in entities:
        entity_url = e.get_attribute("href")
        entity_data = getEntityData(output_file, entity_url, browser)
        gov_data = pd.concat([gov_data, entity_data])
        counter = counter + 1
        if counter >= numEnt:
            break

    return(gov_data)

def getEntityData(output_file, url, browser):
    browser.get(url)
    entity_data = createCustomDataFrame()

    departments = browser.find_elements_by_class_name("primaryCat")

    for d in departments:
        department_url = e.get_attribute("href")
        department_data = getDepartmentData(output_file, department_url, browser)
        entity_data = pd.concat([entity_data,department_data])

    return(entity_data)

def getDepartmentData(output_file, url, browser):
    department_data = createCustomDataFrame()
    
    type_contract = ['per_planta', 'per_contrata']

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
                year_data = getYearData(output_file, year_url, browser)
                
                department_data = pd.concat([department_data,year_data])
                
        except:
            print('Could not get data from' + dept_contract_link)
            pass

    return(department_data)
        
        
        
def getYearData(output_file, url, browser):
    # Check if we still have to dive down into the months
    div_months = browser.find_element_by_class_name("linksIntermedios")
    
    
    if len(div_months) > 0:
        year_data = createCustomDataFrame()

        unordered_list = div_months.find_element_by_tag_name('ul')
        months_links_list = unordered_list.find_elements_by_tag_name('li')

        for m in months_links_list:
            month_link = m.find_element_by_tag_name('a')
            month_url = month_link.get_attribute('href')
            month_data = getTableData(output_file, month_url, browser)
            year_data = pd.concat([year_data, month_data])

    else:
        year_data = getDatainPage(url)
    
    return(year_data)
    

def getDatainPage(output_file, browser, url):

    browser.get(url) # This will open a Firefox window on your machine
    table_links = ()
    table_links.append(url)

    try:
        pagination = browser.find_element_by_class_name("pagination")
        pages = pagination.find_elements_by_tag_name("li")

        for page in pages:
            try:
                link_element = page.find_element_by_tag_name("a")
                link = link_element.get_attribute("href")
                table_links.append(link)
            except:
                pass

        # Remove the last element, its the back arrow
        del table_links[-1]

    except:
        pass

    total_tables = len(table_links)

    # Loop through all the pages and record data
    for count, i in enumerate(table_links):

        if count == 0:
            data = getTableData(browser, i)
        else:
            data1 = getTableData(browser, i)
            data = pd.concat([data, data1])

    with open(output_file, 'a') as f:
        df.to_csv(f, header=False)

    return(data)




def getTableData(browser, url):

    browser.get(url)

    #######
    ### 1 Get table metadata from the breadcrumb (Year, Department, Kind of contract, ...)
    #######

    table_location_data = browser.find_element_by_class_name("breadcrumb")
    breadcrumb_items = table_location_data.find_elements_by_tag_name("li")
    num_breadcrumbs = len(breadcrumb_items)

    entity = breadcrumb_items[1].text
    department = breadcrumb_items[2].text
    type_contract = breadcrumb_items[3].text
    year = breadcrumb_items[4].text
    if num_breadcrumbs == 6:
        month = breadcrumb_items[5]
    else:
        month = 'allyear'

    #######
    ### 2 Get Data of table
    #######

    data = browser.find_elements_by_tag_name("table")

    for i in data:

        # Headers
        head = i.find_elements_by_tag_name("thead")
        for j in head:
            header_row = j.find_elements_by_tag_name("th")

            # Get length and list of headers
            ncol = len(header_row)

            headers = list()
            # Add table location variables
            headers_add = ['entity', 'department', 'type_contract',
                          'year', 'month']
            
            for h in headers_add:
                headers.append(h)
            # Now add actual data row values
            for k in header_row:
                headers.append(k.text)

            headers.append('url')

        # Prepare data frame
        df = pd.DataFrame(columns=headers)

        # Actual Data
        table_data = i.find_elements_by_tag_name("tbody")

        for j in table_data:
            data_row = j.find_elements_by_tag_name("tr")

            # Get length and list of data rows
            nrow = len(data_row)      
            extracted_rows = 0
            master_list = list()
            for count, k in enumerate(data_row):
                data_element = k.find_elements_by_tag_name("td")

                # Process only if there is data in the row
                if len(data_element) != 0:

                    actual_record = list()

                    # Add table location variables
                    actual_record.append(entity)
                    actual_record.append(department)
                    actual_record.append(type_contract)
                    actual_record.append(year)
                    actual_record.append(month)

                    # Populate list with actual record
                    for l in data_element:
                        actual_record.append(l.text)

                    # Add url
                    actual_record.append(url)

                    master_list.append(actual_record)
                    extracted_rows += 1

    df = pd.DataFrame(master_list, columns = headers)
    df = FixColumnNames(df)

    return(df)

    
# Not used anymore      
