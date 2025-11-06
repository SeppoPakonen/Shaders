#!/usr/bin/env python3
"""
Webserver for hosting shader browsing website
"""

import os
import json
import re
from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
JSON_DIR = os.path.join(os.path.dirname(__file__), 'json')
TMP_DIR = os.path.join(os.path.dirname(__file__), 'tmp')
COMMON_DIR = os.path.join(os.path.dirname(__file__), 'common')

@app.route('/')
def frontpage():
    """Serve the frontpage"""
    shaders = load_all_shaders()
    return render_template('frontpage.html', shaders=shaders)

@app.route('/browse')
def browse():
    """Browse shaders with pagination and search"""
    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '').strip()
    per_page = 20
    
    shaders = load_all_shaders()
    
    # Filter based on search query
    if query:
        shaders = search_shaders(shaders, query)
    
    # Pagination
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_shaders = shaders[start_idx:end_idx]
    
    total_pages = (len(shaders) + per_page - 1) // per_page
    
    # Calculate pagination range
    start_page = max(1, page - 2)
    end_page = min(total_pages, page + 2)
    
    return render_template('browse.html', 
                           shaders=paginated_shaders, 
                           page=page, 
                           total_pages=total_pages, 
                           query=query,
                           start_page=start_page,
                           end_page=end_page)

@app.route('/shader/<shader_id>')
def shader_detail(shader_id):
    """View a specific shader"""
    shader_data = load_shader_by_id(shader_id)
    if not shader_data:
        abort(404)
    
    return render_template('shader.html', shader=shader_data)

@app.route('/api/shaders')
def api_shaders():
    """API endpoint to get shaders (for AJAX requests)"""
    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '').strip()
    per_page = 20
    
    shaders = load_all_shaders()
    
    if query:
        shaders = search_shaders(shaders, query)
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_shaders = shaders[start_idx:end_idx]
    
    return jsonify({
        'shaders': paginated_shaders,
        'total': len(shaders),
        'page': page,
        'has_next': end_idx < len(shaders),
        'has_prev': start_idx > 0
    })

@app.route('/api/search')
def api_search():
    """API endpoint for search functionality"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'shaders': [], 'total': 0})
    
    shaders = load_all_shaders()
    results = search_shaders(shaders, query)
    
    return jsonify({
        'shaders': results[:50],  # Limit results
        'total': len(results)
    })

@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files from various directories"""
    # Try to serve from different directories
    static_dirs = [TMP_DIR, COMMON_DIR]
    for static_dir in static_dirs:
        try:
            return send_from_directory(static_dir, path)
        except FileNotFoundError:
            continue
    abort(404)

def load_all_shaders():
    """Load all shaders from JSON files in the JSON directory"""
    shaders = []
    
    # Load from JSON directory
    if os.path.exists(JSON_DIR):
        for filename in os.listdir(JSON_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(JSON_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        shader_data = json.load(f)
                        # Extract ID from filename if not in the shader data
                        if 'info' in shader_data and 'id' in shader_data['info']:
                            shader_id = shader_data['info']['id']
                        else:
                            shader_id = os.path.splitext(filename)[0]
                        
                        shaders.append({
                            'id': shader_id,
                            'filename': filename,
                            'data': shader_data,
                            'info': shader_data.get('info', {})
                        })
                except Exception as e:
                    app.logger.error(f"Error loading shader from {filename}: {e}")
    
    # Sort shaders by name or ID
    shaders.sort(key=lambda x: x.get('data', {}).get('info', {}).get('name', x['id']).lower())
    
    return shaders

def load_shader_by_id(shader_id):
    """Load a specific shader by its ID"""
    if os.path.exists(JSON_DIR):
        # Look for the JSON file that matches the shader ID
        for filename in os.listdir(JSON_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(JSON_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        shader_data = json.load(f)
                        if 'info' in shader_data and 'id' in shader_data['info']:
                            if shader_data['info']['id'] == shader_id:
                                return {
                                    'id': shader_id,
                                    'filename': filename,
                                    'data': shader_data,
                                    'info': shader_data.get('info', {})
                                }
                except Exception as e:
                    app.logger.error(f"Error loading shader from {filename}: {e}")
    
    return None

def search_shaders(shaders, query):
    """Search for shaders by name, username, or description"""
    query = query.lower()
    results = []
    
    for shader in shaders:
        data = shader.get('data', {})
        info = data.get('info', {})
        
        # Search fields
        name = info.get('name', '').lower()
        username = info.get('username', '').lower()
        description = info.get('description', '').lower()
        
        if query in name or query in username or query in description:
            results.append(shader)
    
    return results

@app.route('/search')
def search_page():
    """Page for displaying search results"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    if query:
        shaders = load_all_shaders()
        results = search_shaders(shaders, query)
        
        # Pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_results = results[start_idx:end_idx]
        
        total_pages = (len(results) + per_page - 1) // per_page
        
        # Calculate pagination range
        start_page = max(1, page - 2)
        end_page = min(total_pages, page + 2)
        
        return render_template('search_results.html',
                               shaders=paginated_results,
                               page=page,
                               total_pages=total_pages,
                               query=query,
                               total_results=len(results),
                               start_page=start_page,
                               end_page=end_page)
    else:
        # Calculate pagination range for empty results
        start_page = max(1, page - 2)
        end_page = min(1, page + 2)
        
        return render_template('search_results.html',
                               shaders=[],
                               page=1,
                               total_pages=1,
                               query='',
                               total_results=0,
                               start_page=start_page,
                               end_page=end_page)

if __name__ == '__main__':
    # Create necessary directories if they don't exist
    os.makedirs(os.path.join(app.template_folder or '', 'templates'), exist_ok=True)
    
    app.run(host='0.0.0.0', port=8081, debug=True)