# trackwise-search

trackwise-search is an NLP to SQL tool for the TrackWise Oracle SQL Database by converting natural language prompts to Oracle SQL queries which directly run on the TrackWise database. The extracted data can then be exported directly as an Excel file to local storage.

## Quickstart
1. Clone repo
   ```sh
    git clone https://github.com/mattlimsiaco/trackwise-search.git
   ```
2. Start virtual environment
   ```sh
   python -m venv venv
   ```
3. Activate virtual environment
   ```sh
   .\venv\Scripts\activate
   ```
4. Install dependencies
   ```sh
    pip install -r requirements.txt
   ```
5. Connect to repo
   ```sh
    git remote set-url origin https://github.com/mattlimsiaco/trackwise-search.git
   ```
6. Set Flask app
   ```sh
    $env:FLASK_APP = "app.py"
   ```
***IMPORTANT! Refer to #2 in "Important Notes and Future Implementations" before continuing!***
6. Run Flask app
   ```sh
    flask run
   ```

## Features
![Frontend](static/img/frontend.png)

1. **QUERY Tab**
   * Input a natural language prompt in the chatbox in the bottom to generate a query tailored to the TrackWise Oracle SQL database
   * Verify that the query is correct by checking the box. The user input, generated query, and their respective vector embeddings are then stored in the backend for future reference.
2. **DATA Tab**
   * Displays a preview of the data extracted after running the generated query on the TrackWise database.
   * Features an "Export Data" button to save the extracted data locally as an Excel file.
3. **Tooltips**
   * Provides general knowledge on usage and optimizing results (specificity of prompts).
4. **Update Data**
   * Functionality to update the table and column names to match current TrackWise format.


### Query Generation Functionality
![Functionality Pipeline](static/img/functionality.png)

1. **User Input:**
   * User input is read in and sent to the backend
2. **Similarity Search Through Verified Queries:**
   * User input is converted to a vector embedding via AzureOpenAIEmbeddings
   * K most similar queries are found from the verified query database
      * **NOTE:** Verified queries (user's query, generated sql query, user query embedding, sql query embedding) are currently stored as a jsonl file. This should instead be stored within a vector database for scalability and efficiency.
3. **Retrieval Of Most Similar Queries:**
   * K most similar queries are returned as **Enhanced Context**
4. **Extracting Most Relevant Tables and Columns, Adding to Model Context**
   * OpenAI determines "possible" k number of tables and columns from the user's input
   * The actual k number of table names are found from the TrackWise schema (which is an already established csv file that contains all the vector embeddings of the table names, respective column names, and respective data types) based on the "possible" table names given from OpenAI by cosine similarity search.
      * **NOTE:** As stated before, the storage of the TrackWise schema is not optimal as it is stored locally, instead it should be within an established vector database on the cloud, such as Azure.
   * After determining the actual table names, the "possible" columns go through the same process as the tables, this time limited to the scope of the tables.
   * The k number of most relevant table and column names are then fed into the OpenAI context. 
   * Retrieval Augmented Generation is implemented with the inclusion of the **Enhanced Context** in the model's context, which contains possible matches of previous queries.
      * **NOTE:** Feeding a decreased scope with just strings of most relevant table and column names into the context served a better approach than directly searching through the entire TrackWise schema for the correct table and column names as doing this previously with LangChain took around 50-60 seconds to find table and column names.
5. **Query Generation:**
   * With the base prompt, the user input, the relevant table and column names, and the enhanced context, the model finally generates an Oracle SQL query.


## Important Notes and Future Implementations
1. **METHOD FOR QUERY GENERATION:** The backend is currently being run through 2 iterations of OpenAI, 1st to extract potential table and column names, 2nd to finally generate the query. I have yet to discover a more efficient method of extracting potential table and column names, however, without the double implementation, I assume there will be a cut in half of the cost of upkeep with the usage of OpenAI's API. There may also be a decrease in runtime if parsing/extraction is done manually.
    **My original method:** Utilize LangChain to automatically run steps 4 and 5 in the "Query Generation" visualization. LangChain would directly connect to the TW Oracle SQL database and generate a query after finding the respective table names and column names. While this seems simple, it resulted in significantly long runtimes, averaging 50-60 seconds and lack of ability to tweak the efficiency.
2. **ENVIRONMENT VARIABLES:** Due to privacy policy, the .env file which contains all the environment variables cannot be pushed directly to GitHub. The most practical and foolproof method is to use this template to fill out the variable values then save it as ".env" in the root directory of the project folder:

    AZURE_OAI_TYPE = "azure"
    AZURE_OAI_VERSION = "2024-02-01"
    AZURE_OAI_ENDPOINT= "https://strykeranalyticsopenai.openai.azure.com/"
    AZURE_OAI_KEY= 
    AZURE_OAI_CHAT= "gpt-35-turbo"
    AZURE_OAI_EMBEDDING= "stryker_embedding_ai"

    ORACLE_DB = 
    ORACLE_HOST = 
    ORACLE_PORT = 
    ORACLE_USERNAME = 
    ORACLE_PASSWORD = 

The AZURE_OAI_KEY can be found in the Azure portal, under the OpenAI service. The best alternative is to store them as secrets within Azure and automate an access pattern to automatically generate a .env file.
3. **VECTOR DATABASE STORAGE:** Currently the vector embeddings for the TW Database schema and verified queries are stored as a csv and jsonl file, respectively. These should instead be stored as established vector databases (preferably within Azure) and utilized as index tables for cosine similarity search. While this may decrease the runtime of the app, it mitigates a lot of problems relating to local storage, scalability, and deployment.
4. **UPDATE DATA BUTTON:** The "Update Data" button is completely free use by anybody. This is a problem if the app is running on a web server, since pressing the button without letting it complete fully (which takes on average 10 minutes) results in an incomplete TW database schema since all table and column vector embeddings are cleared initially then filled according to the TW database metadata. This results in the app being non-functional if the user requests data that is not a part of the TW database schema. Some alternatives could be to implement admin access to this button, or simply remove the button entirely and update the metadata exclusively through the backend in the case that the TW database gets updated.


## DEPLOYMENT
***AZURE WEB APP DEPLOYMENT***
   1. Stryker firewall on the TW database. I 