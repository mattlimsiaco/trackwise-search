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
6. Run Flask app
   ```sh
    flask run
   ```

## Functionality
### Query Generation
![Project Logo](static/img/functionality.png)

1. User input is read in and sent to the backend
2. * User input is converted to a vector embedding via AzureOpenAIEmbeddings
   * K most similar queries are found from the verified query database
      * **NOTE:** Verified queries (user's query, generated sql query, user query embedding, sql query embedding) are currently stored as a jsonl file. This should instead be stored within a vector database for scalability and efficiency.
3. K most similar queries are returned as **Enhanced Context**
4. * OpenAI determines "possible" k number of tables and columns from the user's input
   * The actual k number of table names are found from the TrackWise schema (which is an already established csv file that contains all the vector embeddings of the table names, respective column names, and respective data types) based on the "possible" table names given from OpenAI by cosine similarity search.
      * **NOTE:** As stated before, the storage of the TrackWise schema is not optimal as it is stored locally, instead it should be within an established vector database on the cloud, such as Azure.
   * After determining the actual table names, the "possible" columns go through the same process as the tables, this time limited to the scope of the tables.
   * The k number of most relevant table and column names are then fed into the OpenAI context. 
   * Retrieval Augmented Generation is implemented with the inclusion of the **Enhanced Context** in the model's context, which contains possible matches of previous queries.
5. With the base prompt of "You are an expert in writing queries in Oracle SQL Syntax based on a user's request.", the user input, the relevant table and column names, and the enhanced context, the model finally generates an Oracle SQL query.