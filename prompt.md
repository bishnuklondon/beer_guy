I want to create an app which will connect pubs with the customers. which will regularly keep an updated data by fetching and storing details of all local pubs by UK districts using google API and the postcode inventory

Create a python project. 

Read the post code data for all regions in uk. The data is under data\POST_CODE_INVENTORY_ONSPD_FEB_2026\Data\multi_csv. 

Load this folder with pyarrow as a table. The first column pcd7 is the individual post code. the first 3 letters are the district post code. 

craeate a mcp server running in http. This mcp server should expose api to fetch and save the pubs data in delta tables by district post code. And will expose another api to retrieve the schema  of the tables and another api to read data from the table. The read should be done using pyarrow and duckdb. Also expose rest api along with mcp tool.

The pubs data should contain name, address, rating, district post code, district name , geo location, website link. 



Create another python project

This will regularly webscrape the pubs websites for keeping an updated data for their menu, and ongoing offers. This data should be saved in different tables. Extract the details for the beverage options in a seperate table.

Seperate the beers, wines and cocktails.



Create another project

This will be the UI, there should be a web ui, compatible with Mobile and desktop. Use react.js. provide a qucik way to start the server( choose the technology fits best ).

The UI will call REST endpoints to fetch the data.

There should be one UI which will allow users to filter the pubs data either by a dropdown selection of the districts or by getting the location details form the ip address. 

The customers can come this web page to check offers in their region. They will be able to serach for a speciffic beer or should compare the cheapest options for the beers. Same for the wines and cocktails. 



The UI should call the backend via rest api so, expose a dedicated rest api for this in the first project. and expose the same as mcp tools.



