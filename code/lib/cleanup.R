library(tidyverse)
library(stringr)


#### Extract ---- 

# Get list of files in directories
setwd(dirname(rstudioapi::getActiveDocumentContext()$path))
files.output <- list.files(path = '../output', recursive = TRUE)
files.output <- paste0('../output/', files.output)

# Process and put into a data.table
combine.csv <- function(file.list, file.text){
  files.to.get <- file.list[grepl(file.text, file.list)]

  df.list <- list()
  
  counter <- 1
  for(i in files.to.get){
    df.list[[counter]] <- read.csv(i, header = FALSE)
    counter <- counter + 1
  }
  

  return(df.list)
}

combine.csv.2 <- function(file.list, file.text){
  files.to.get <- file.list[grepl(file.text, file.list)]
  
  df <- do.call(bind_rows,
          lapply(files.to.get,function(x){ 
            data <- read.csv(x, header = FALSE, colClasses = 'character')
            data$filename <- x
            return(data)
            })
          )
  
  return(df)
}

# Get the list of data frames
scraped.data <- combine.csv.2(files.output, 'scraped_data')


head(scraped.data)


unique(scraped.data$V1)

scraped.data[scraped.data$V1 == 'CORREA',]

unique(scraped.data$filename)

scraped.data[scraped.data$V1 == "HN JUN 2016: 526112, HN JUL 2016: 394584, HN AGO 2016: 426664, HN SEP 2016: 375336."
            ,]

