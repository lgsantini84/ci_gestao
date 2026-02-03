#!/usr/bin/env python3
"""
Ponto de entrada para desenvolvimento.
"""

from app import create_app

app = create_app('development')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)