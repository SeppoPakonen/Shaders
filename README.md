# Shadertoy Browser (15,067 shaders)

A comprehensive toolkit for browsing, searching, and viewing shaders from Shadertoy. This project allows you to run a local browser for Shadertoy shaders with extensive search capabilities.

## Overview

The Shadertoy Browser is a collection of tools for exploring the vast collection of Shadertoy shaders, featuring both a web interface and a powerful command-line search tool. It comes with thousands of pre-downloaded shaders ready to browse and search.

## Search Tool (Most Important Feature!)

The project includes a powerful command-line search tool (`search.py`) that enables sophisticated searching across all shader data:

### Basic Search Options
- `--tags <tag>`: Search by tags (e.g. `--tags game`)
- `--name <text>`: Search in shader names
- `--author <text>`: Search by author/username  
- `--description <text>`: Search in descriptions

### Resource Requirement Search
- `--buffer`: Find shaders requiring buffers
- `--cubemap`: Find shaders requiring cubemaps
- `--image`: Find shaders requiring images
- `--keyboard`: Find shaders requiring keyboard input
- `--texture`: Find shaders requiring textures
- `--video`: Find shaders requiring video input
- `--sound`: Find shaders requiring sound input
- `--library`: Find shaders requiring external libraries
- `--webcam`: Find shaders requiring webcam input
- And many more resource types...

### Advanced Options
- `--add-tags`: Add tag information from search_results to JSON files and analyze JSONs for resource dependencies
- `--reindex`: Rebuild shader index cache
- `--json-dir <dir>`: Specify directory with JSON shader files

### Examples:
```bash
# Find all games requiring buffers
python search.py --tags game --buffer

# Find all games with keyboard input
python search.py --tags game --keyboard

# Find shaders by specific author
python search.py --author iq

# Find shaders using textures
python search.py --texture --name "raymarching"
```

The search tool intelligently analyzes shader JSON files to detect resource requirements and combines this with the original requires data for comprehensive searching.

## Features

- Browse all shaders with pagination
- Search functionality for finding specific shaders
- Detailed shader views with code and metadata
- Responsive design that works on different screen sizes
- Local web interface - no internet required after setup
- Support for shader preview functionality

## File Structure

```
Shaders/
├── webserver.py          # Main Flask application
├── json/                 # Shader data files in JSON format
├── templates/            # HTML templates (base.html, browse.html, shader.html, etc.)
├── README.md             # This file
└── ...
```

## Prerequisites

- Python 3.6+
- Flask
- Other Python dependencies

## Installation

1. Clone the repository or download the source code
2. Install Python dependencies:
   ```bash
   pip install flask werkzeug
   ```

## Usage

1. Run the webserver:
   ```bash
   python webserver.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:8081
   ```

## Project Structure

- `webserver.py`: Main Flask application that serves the web interface
- `json/`: Contains hundreds of shader files in JSON format
- `templates/`: HTML templates for the web interface
  - `base.html`: Main layout template
  - `frontpage.html`: Front page of the application
  - `browse.html`: Browse all shaders page
  - `shader.html`: Individual shader detail page
  - `search_results.html`: Search results page
- `templates/styles.css`: CSS styling for the application

## Shader Data Format

Each shader is stored as a JSON file containing:
- Metadata (ID, name, username, description, date, etc.)
- Render pass information
- GLSL shader code
- Statistics (views, likes, etc.)

## Features

### Browse
View all available shaders in a grid layout with pagination.

### Search
Search for shaders by name, username, or description.

### Detailed View
View individual shaders with full code and metadata.

### Responsive Design
Works on various screen sizes and devices.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project does not specify a license in the provided files. Please check with the project maintainers for licensing information.

## Notes

- This project contains a large collection of shaders obtained from Shadertoy
- All shaders are stored locally in the `json/` directory
- The application runs locally and doesn't require continuous internet access after setup