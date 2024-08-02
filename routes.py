import pandas as pd
import numpy as np
from config import *
from scipy.spatial.distance import cdist
import os, re, json, cx_Oracle, csv, sys
from flask import request, send_file
from utils import client, parse_table_info, find_tables, find_columns, create_column_schema, create_embedding, update_db_data, export_excel, read_verify_df


# Attempt to change storage path for PyInstaller deployment method

# def get_resource_path(relative_path):
#     try:
#         base_path = sys._MEIPASS
#     except AttributeError:
#         base_path = os.path.dirname(__file__)
#     return os.path.join(base_path, relative_path)

# df = pd.read_csv(get_resource_path('data/embedding_csv.csv'))
# df['column_name_cleaned_embedding'] = df['column_name_cleaned_embedding_json'].apply(json.loads)
# df = df.drop(columns=['column_name_cleaned_embedding_json'])

# verify_df = pd.read_csv(get_resource_path('data/query_verification.csv'), encoding='utf-8')



# Oracle DB schema embeddings
df = pd.read_csv('data/embedding_csv.csv')
df['column_name_cleaned_embedding'] = df['column_name_cleaned_embedding_json'].apply(json.loads)
df = df.drop(columns=['column_name_cleaned_embedding_json'])

# Verified queries embeddings
verify_df = read_verify_df()


unique_table_names = df['Cleaned_Table_Name'].unique()

table_names_list = []
embeddings_list = []

for table_name in unique_table_names:
    embedding = create_embedding(table_name)
    table_names_list.append(table_name)
    embeddings_list.append(embedding)

df_embeddings = pd.DataFrame({
    'Unique_Table_Names': table_names_list,
    'Embeddings': embeddings_list
})

# Find solution to not use global variable
filtered_rows = []

def export_data():
    global filtered_rows
    csv_filename = export_excel(pd.DataFrame(filtered_rows))
    return send_file(csv_filename, as_attachment=True)

# Update to change button access 
# (pressing update data without letting it complete stops app from working since it resets oracle db schema)
def update_data():
    update_db_data()
    return {'message': 'Data updated successfully'}

# Cosine similarity search for retrieval of verified queries
# IMPLEMENT GENERATION OF RANDOM VERIFIED QUERIES AS BASE STORAGE
def retrieve_closest_queries(user_query, verify_df, top_n=3):
    user_query_cleaned = re.sub(r'[^a-z0-9_]', '', user_query).lower()
    user_query_embedding = create_embedding(user_query_cleaned)
    
    user_query_embedding = np.array(user_query_embedding).reshape(1, -1)
    
    embeddings_list = verify_df['user_query_embedding'].tolist()
    embeddings = np.array(embeddings_list)
    
    # print("user_query_embedding shape:", user_query_embedding.shape)
    # print("embeddings shape:", embeddings.shape)
    
    distances = cdist(user_query_embedding, embeddings, metric='cosine')[0]
    
    top_indices = np.argsort(distances)[:top_n]
    
    closest_queries = verify_df.iloc[top_indices]
    
    enhanced_context = "Here are some closely related queries to provide context:\n"
    for _, row in closest_queries.iterrows():
        enhanced_context += f"User Query: {row['user_query']}\nSQL Query: {row['sql_query']}\n\n"
    
    return enhanced_context


# Main function for nlp to sql
def handle_sql_query(df=df, df_embeddings=df_embeddings):
    connection = cx_Oracle.connect(
        user=ORACLE_USERNAME,
        password=ORACLE_PASSWORD,
        dsn=ORACLE_DSN
    )

    data = request.get_json()
    user_query = data['sql_query']

    # Retrieval of most similar queries that have been verified
    enhanced_context = retrieve_closest_queries(user_query, verify_df)

    # print(enhanced_context)

    # Can optimize context
    scope_context = f"""
        You are an expert in extracting table information from a user prompt. Once given a prompt, you are to respond with the table name that the user is hoping to query from in addition to stating that 1 table was used.
        Make sure you are prioritizing tables with "SV" instead of tables with "MV"
        If the query involves a join statement, make sure to list the tables and how many are used.

        Here is additional context from similar queries:
        {enhanced_context}

        For example:
        User Input: 
        "Can I get a list of Product Inquiries/MIRs where the PI CIC = “Medical - Belfast” and the eMIR approval record Timeliness Determined Late = “Yes”?  I would like to see PI opened in the past 2 years if possible."

        Your Response: 
        "Tables: Product Inquiries, MIR
        Amount of Tables: 2
        Columns: CIC, Timeliness Determined Late, Date Opened
        Amount of Columns: 3
    """

    scope = client.chat.completions.create(
        model=os.getenv("AZURE_OAI_CHAT"),
        messages=[
            {"role": "system", "content": scope_context},
            {"role": "user", "content": user_query}
        ]
    )

    # Extracting possible tables and respective columns from prompt
    tables = scope.choices[0].message.content.strip()
    tables1, amt_tables1, columns1, amt_columns1 = parse_table_info(tables)


    # Using extracted possible tables and columns to search for exact names from oracle db
    searched_tables = find_tables(tables1, amt_tables1, df, df_embeddings)
    pattern = '|'.join(searched_tables)
    df = df[df['Table_Name'].str.contains(pattern)].reset_index(drop=True)
    top_column_info = find_columns(columns1, amt_columns1, df)
    columns_schema = create_column_schema(top_column_info)

    # Can optimize context
    nlp2sql_context = f"""
        You are an expert in writing queries in Oracle SQL Syntax based on a user's request.
        Keep in mind that the column_name inside of the double quotation marks (") are the exact names of the columns. Do not deviate from the original name.

        Schema format:
        ("column_name1", datatype, table_name_of_column1)
        ("column_name2", datatype, table_name_of_column2)
        ("column_name3", datatype, table_name_of_column3)
        ("column_name4", datatype, table_name_of_column4)

        Here are some guidelines:

        1. **Verify Tables and Columns**: Before finalizing your query, ensure that the columns and tables match correctly. You must not query a column from a table without first confirming that the column belongs to that specific table.
        You can confirm this by checking if the table name is in the same parentheses as the column name. For example, "Timeliness Determined Late" column is from the "V_ARC_EMIR_SV_2" table, not the "V_ARC_EMIR_SV" table.

        2. **Verify Table Name**: Do not change the names of the columns that you are given, keep them exactly how they appear. Use the actual column names from the Oracle SQL Tables that I provided. For example, "Initial Reporter Country" should not be "Country of Initial Reporter"
        In addition encapsulate the original column names in double quotation marks and do not add unnecessary underscores as replacements for spaces. For example, "Date of Explant From" should not be "Date_of_Explant_From". You must not query from a column without first confirming
        that the column name is exactly the same as it was given in the schema. If it is not the same, use the closest name to the column you were to query from.

        3. **Handle Text Fields Appropriately**: If the user gives a text-based condition, adjust your query to incorporate "LOWER" or "LIKE". For example, if the user asks if the Correction Plan Summary contains "health" you should produce, 
        LOWER("Correction Plan Summary") = LIKE LOWER(%health%).

        4. **Ensure Correct Joins**: If your query involves a join, always use "ROOT_PARENT_ID" for joining tables. Only join tables with relevant columns. For example, do not join a table if there is no WHERE condition for a column from that table.

        5. **Select All Columns**: The select statement should include all columns with "SELECT *".

        6. **Include user**: All table names should begin with SYSADM, for example, SYSADM.V_ARC_PRODUCT_INQUIRY_SV

        7. **Use Proper Query Formatting**: Enclose your Oracle SQL queries within triple backticks (```). Do not enclose anything else in triple backticks except the Oracle SQL Query.

        Here are the Oracle SQL columns: {columns_schema}

        Example Prompts:
        User: I want the query that shows all the PFA Assessments where the fda reporting decision is 'To be reported'.
        Generated Query: 
        SELECT *
        FROM SYSADM.V_ARC_PFA_ASSESSMENT_SV
        WHERE LOWER("Reporting Decision - FDA") = ('To be reported');
    """

    response = client.chat.completions.create(
        model=os.getenv("AZURE_OAI_CHAT"),
        messages=[
            {"role": "system", "content": nlp2sql_context},
            {"role": "user", "content": user_query}
        ],
        temperature=0
    )

    sql_query = response.choices[0].message.content.strip()
    query_start_index = sql_query.find("```") + 3
    query_end_index = sql_query.rfind("```")

    # For some reason 'sql' is occasionally within triple quotes (''')
    sql_query = sql_query[query_start_index:query_end_index].strip().replace("sql","")

    sql_query_cleaned = sql_query.replace(";", "").replace("\n", " ").replace("\'", "'")
    cursor = connection.cursor()

    try:
        cursor.execute(sql_query_cleaned)
        
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

        # Find solution for global variable alternatives?
        global filtered_rows
        filtered_rows = [] 

        # Removing column names with ROWID to optimize runtime
        for row in rows:
            filtered_row = {}
            for idx, value in enumerate(row):
                column_name = columns[idx]
                if isinstance(value, cx_Oracle.LOB):
                    value = value.read()  
                if 'ROWID' not in column_name:
                    filtered_row[column_name] = value
            filtered_rows.append(filtered_row)
        
        return {'result': sql_query, 'data': filtered_rows}
    
    except Exception as e:
        return {"error": str(e)}
    
    finally:
        cursor.close()
        connection.close()


# Function to update with verified query
def verify(verify_df=verify_df):

    # Currently jsonl file is used to store verified queries but should change to established db
    verify_df_path = 'data/query_verification.jsonl'
    data = request.get_json()
    user_query = data.get('userQuery', '')
    sql_query_cleaned = data.get('sqlQuery', '')

    user_query_cleaned = re.sub(r'[^a-z0-9_]', '', user_query).lower()

    user_query_embedding = create_embedding(user_query_cleaned)
    sql_query_embedding = create_embedding(sql_query_cleaned)

    new_row = {
        'user_query': user_query,
        'sql_query': sql_query_cleaned,
        'user_query_embedding': user_query_embedding, 
        'sql_query_embedding': sql_query_embedding 
    }

    # Not adding duplicate queries to query verification storage
    if not verify_df[(verify_df['user_query'] == user_query) & (verify_df['sql_query'] == sql_query_cleaned)].empty:
        return {"message": "Duplicate entry found. No new data added."}

    # Eventually change to use established db instead of jsonl file
    with open(verify_df_path, 'a') as f:
        json.dump(new_row, f)
        f.write('\n')

    return {"message": "Query stored successfully"}