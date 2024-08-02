from flask import Flask, render_template
from flask_cors import CORS
from routes import handle_sql_query, verify, update_data, export_data

app = Flask(__name__)
CORS(app)

# NLP to SQL Button
@app.route('/query', methods=['POST'])
def query():
    return handle_sql_query()

# Correct Query Button
@app.route('/verify_query', methods=['POST'])
def verify_query():
    return verify()

# Update Data Button
@app.route('/update_data', methods=['POST'])
def update():
    return update_data()

# Export Data Button
@app.route('/export_data', methods=['POST'])
def export():
    return export_data()

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run()