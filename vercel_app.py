from flask import Flask, send_from_directory
import subprocess
import os

app = Flask(__name__)

@app.route('/')
def home():
    # Start Streamlit in a subprocess
    streamlit_process = subprocess.Popen(['streamlit', 'run', 'app.py'])
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('./static', path)

if __name__ == '__main__':
    app.run() 