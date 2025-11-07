#!/usr/bin/env python3
"""
Search script for Shadertoy shaders based on various criteria.
Supports searching by tags, name, author, description, and finding shaders with requires_* files.
"""

import os
import json
import argparse
import glob
from pathlib import Path
import pickle
import time
from typing import Dict, List, Set

class ShaderSearcher:
    def __init__(self, json_dir='json', shader_dirs=None):
        self.json_dir = json_dir
        self.shader_dirs = shader_dirs or ['shaders_071121', 'shaders_270321']
        self.cache_file = os.path.join('.', 'tmp', 'shader_cache.dat')
        # Create tmp directory if it doesn't exist
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        
        self.requires_cache = {}  # Cache for requires_* file contents
        self.tag_cache = {}       # Cache for tag mappings
        self.shader_index = {}    # Cache for shader metadata

    def build_tag_mappings(self):
        """Build tag mappings from search_result files."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    if 'tag_cache' in cached_data:
                        self.tag_cache = cached_data['tag_cache']
                        return self.tag_cache
            except:
                pass  # Cache file is corrupted or invalid, rebuild

        tag_mappings = {}
        for shader_dir in self.shader_dirs:
            search_results_dir = os.path.join(shader_dir, 'search_results')
            if os.path.exists(search_results_dir):
                for tag_file in os.listdir(search_results_dir):
                    tag_name = tag_file
                    filepath = os.path.join(search_results_dir, tag_file)
                    if os.path.isfile(filepath):
                        try:
                            with open(filepath, 'r') as f:
                                ids = []
                                for line in f:
                                    line = line.strip()
                                    if line:
                                        ids.append(line)
                            tag_mappings[tag_name] = set(ids)
                        except Exception as e:
                            print(f"Warning: Could not read tag file {filepath}: {e}")

        # Cache the tag mappings
        try:
            # Load existing cache if it exists to update only tag_cache
            cache_data = {}
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
            
            cache_data['tag_cache'] = tag_mappings
            with open(self.cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
        except:
            print("Warning: Could not save tag cache file")

        self.tag_cache = tag_mappings
        return tag_mappings

    def add_requires_info_to_jsons(self):
        """Add requires information from search results and requires files to the JSON files."""
        # First, add tag information from search results
        tag_mappings = self.build_tag_mappings()
        tag_updated_count = 0
        
        for tag, shader_ids in tag_mappings.items():
            for shader_id in shader_ids:
                json_file_path = os.path.join(self.json_dir, f"{shader_id}.json")
                
                if os.path.exists(json_file_path):
                    try:
                        with open(json_file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Only modify if it's a proper data structure with 'info'
                        if isinstance(data, dict) and 'info' in data:
                            info = data['info']
                            if 'tags' not in info:
                                info['tags'] = []
                            
                            # Add tag if not already present
                            if tag not in info['tags']:
                                info['tags'].append(tag)
                                
                                # Write the updated data back to the file
                                with open(json_file_path, 'w', encoding='utf-8') as f:
                                    json.dump(data, f)
                                tag_updated_count += 1
                    except Exception as e:
                        print(f"Error updating {json_file_path} with tags: {e}")
        
        # Now, add requires information by parsing the JSON files for dependencies
        requires_updated_count = 0
        
        for filename in os.listdir(self.json_dir):
            if filename.endswith('.json'):
                shader_id = filename[:-5]  # Remove .json extension
                json_file_path = os.path.join(self.json_dir, filename)
                
                try:
                    with open(json_file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if isinstance(data, dict) and 'info' in data and 'renderpass' in data:
                        # Parse renderpass to identify what resources this shader requires
                        required_resources = set()
                        
                        for pass_info in data['renderpass']:                            
                            # Check inputs for resource types
                            inputs = pass_info.get('inputs', [])
                            for inp in inputs:
                                # Based on the C++ logic:
                                # - type "image" or "buffer" -> becomes "imagebuf"
                                # - type "sound" -> becomes "soundbuf"
                                # - type "common" -> becomes "library" 
                                # - type "cubemap" -> stays "cubemap"
                                # - other types get "buf" appended
                                
                                input_type = inp.get('type', '').lower()
                                sampler_info = inp.get('sampler', {})
                                
                                if input_type == 'image' or input_type == 'buffer':
                                    required_resources.add('imagebuf')
                                elif input_type == 'sound':
                                    required_resources.add('soundbuf')
                                elif input_type == 'common':
                                    required_resources.add('library')
                                elif input_type == 'cubemap':
                                    required_resources.add('cubemap')
                                elif input_type:
                                    # Other types get 'buf' appended (e.g., texture->texturebuf, video->videobuf)
                                    required_resources.add(input_type + 'buf')
                                
                                # Additionally, look at the filepath to see if there are other resources
                                filepath = inp.get('filepath', '')
                                if '/media/' in filepath or 'cubemap' in filepath.lower():
                                    required_resources.add('texture')
                            
                            # Also check the pass type itself
                            pass_type = pass_info.get('type', '').lower()
                            if pass_type == 'image' or pass_type == 'buffer':
                                required_resources.add('imagebuf')
                            elif pass_type == 'sound':
                                required_resources.add('soundbuf')
                            elif pass_type == 'common':
                                required_resources.add('library')
                            elif pass_type == 'cubemap':
                                required_resources.add('cubemap')
                            elif pass_type:
                                required_resources.add(pass_type + 'buf')
                        
                        # Update the JSON file with the required resources
                        info = data['info']
                        if 'requires' not in info:
                            info['requires'] = []
                        
                        original_count = len(info['requires'])
                        for req in required_resources:
                            if req not in info['requires']:
                                info['requires'].append(req)
                        
                        # Write back to file only if we added new requirements
                        if len(info['requires']) > original_count:
                            with open(json_file_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f)
                            requires_updated_count += 1
                                
                except Exception as e:
                    print(f"Error processing {json_file_path} for requires info: {e}")
        
        print(f"Updated {tag_updated_count} JSON files with tag information")
        print(f"Updated {requires_updated_count} JSON files with requires information")
        return tag_updated_count, requires_updated_count

    def load_requires_file(self, req_type):
        """Load shader IDs from a requires file."""
        if req_type in self.requires_cache:
            return self.requires_cache[req_type]

        requires_set = set()
        for shader_dir in self.shader_dirs:
            filepath = os.path.join(shader_dir, f'requires_{req_type}.txt')
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('---'):
                                # The line format is typically like "folder/shader_id"
                                # The shader_id part is what corresponds to the JSON filename (without .json extension)
                                if '/' in line:
                                    shader_id = line.split('/')[-1]
                                else:
                                    # If no slash, use the whole line
                                    shader_id = line
                                requires_set.add(shader_id)
                except Exception as e:
                    print(f"Warning: Could not read {filepath}: {e}")

        self.requires_cache[req_type] = requires_set
        return requires_set

    def load_all_json_metadata(self, force_rebuild=False):
        """Load metadata (id, name, username, description, tags) from all JSON files."""
        cache_data = {}
        if not force_rebuild and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                if 'shader_index' in cache_data:
                    return cache_data['shader_index']
            except:
                pass  # Cache file is corrupted or invalid, rebuild

        # Rebuild the cache
        shader_index = {}

        print("Building shader index... this may take a moment")
        json_files = glob.glob(os.path.join(self.json_dir, "*.json"))
        for i, filepath in enumerate(json_files):
            if i % 1000 == 0:
                print(f"Processed {i}/{len(json_files)} files...")

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Check if data is a dict (object) and has 'info' key
                if isinstance(data, dict) and 'info' in data:
                    info = data.get('info', {})
                    shader_id = info.get('id', os.path.basename(filepath).replace('.json', ''))

                    shader_index[shader_id] = {
                        'filepath': filepath,
                        'name': info.get('name', ''),
                        'username': info.get('username', ''),
                        'description': info.get('description', ''),
                        'tags': info.get('tags', []),
                    }
                else:
                    # Skip if data is not in expected format
                    continue
            except (json.JSONDecodeError, UnicodeDecodeError, FileNotFoundError):
                continue

        print(f"Index built with {len(shader_index)} shaders")

        # Save to cache
        cache_data['shader_index'] = shader_index
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
        except:
            print("Warning: Could not save cache file")

        return shader_index

    def search(self, tags=None, name=None, author=None, description=None,
               requires_buffer=False, requires_cubemap=False, requires_image=False,
               requires_imagebuf=False, requires_keyboard=False, requires_library=False,
               requires_mic=False, requires_music=False, requires_musicstream=False,
               requires_sound=False, requires_soundbuf=False, requires_texture=False,
               requires_video=False, requires_volume=False, requires_webcam=False, requires_common=False,
               force_rebuild=False):
        """Search shaders based on provided criteria."""
        self.shader_index = self.load_all_json_metadata(force_rebuild)
        if not force_rebuild:  # Only load tag mappings if not rebuilding the main shader index
            self.tag_cache = self.build_tag_mappings()
        results = []

        # Start with all shaders
        matching_shaders = set(self.shader_index.keys())

        # Apply text-based filters
        if tags:
            temp_set = set()
            tag_lower = tags.lower()
            for shader_id, data in self.shader_index.items():
                # Check both tags in JSON and tags in cache
                all_tags = data['tags'][:]
                # Check if shader appears in the tag cache
                for cached_tag, shader_ids in self.tag_cache.items():
                    if shader_id in shader_ids and cached_tag.lower().startswith(tag_lower):
                        # Add this tag to our all_tags if not already there
                        if cached_tag not in all_tags:
                            all_tags.append(cached_tag)
                
                if any(tag_lower in t.lower() for t in all_tags):
                    temp_set.add(shader_id)
            matching_shaders &= temp_set

        if name:
            temp_set = set()
            name_lower = name.lower()
            for shader_id, data in self.shader_index.items():
                if name_lower in data['name'].lower():
                    temp_set.add(shader_id)
            matching_shaders &= temp_set

        if author:
            temp_set = set()
            author_lower = author.lower()
            for shader_id, data in self.shader_index.items():
                if author_lower in data['username'].lower():
                    temp_set.add(shader_id)
            matching_shaders &= temp_set

        if description:
            temp_set = set()
            desc_lower = description.lower()
            for shader_id, data in self.shader_index.items():
                if desc_lower in data['description'].lower():
                    temp_set.add(shader_id)
            matching_shaders &= temp_set

        # Apply requires_* filters - first from original requires files, then from JSON info
        if requires_buffer or requires_cubemap or requires_image or requires_imagebuf or requires_keyboard \
           or requires_library or requires_mic or requires_music or requires_musicstream \
           or requires_sound or requires_soundbuf or requires_texture or requires_video \
           or requires_volume or requires_webcam or requires_common:
            temp_matching = set()
            for shader_id in matching_shaders:
                if shader_id in self.shader_index:
                    shader_info = self.shader_index[shader_id]
                    # Get the shader data from the actual file to check if it has 'requires' info
                    try:
                        with open(shader_info['filepath'], 'r', encoding='utf-8') as f:
                            shader_data = json.load(f)
                        if isinstance(shader_data, dict) and 'info' in shader_data:
                            req_list = shader_data['info'].get('requires', [])
                        else:
                            req_list = []
                    except Exception:
                        req_list = []
                    
                    conditions_met = []
                    any_requirement_checked = False
                    
                    if requires_buffer:
                        # Buffer requirement could be in original requires files or as 'imagebuf' in JSON (since buffer type becomes imagebuf)
                        in_orig = shader_id in self.load_requires_file('buffer')
                        has_req = 'imagebuf' in req_list  # Buffer type in inputs often becomes imagebuf
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                    
                    if requires_cubemap:
                        in_orig = shader_id in self.load_requires_file('cubemap')
                        has_req = 'cubemap' in req_list
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                    
                    if requires_image:
                        in_orig = shader_id in self.load_requires_file('image')
                        has_req = 'imagebuf' in req_list  # Image type in inputs often becomes imagebuf
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                        
                    if requires_imagebuf:
                        in_orig = shader_id in self.load_requires_file('imagebuf')
                        has_req = 'imagebuf' in req_list
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                        
                    if requires_keyboard:
                        in_orig = shader_id in self.load_requires_file('keyboard')
                        has_req = 'keyboardbuf' in req_list
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                        
                    if requires_library:
                        in_orig = shader_id in self.load_requires_file('library')
                        has_req = 'library' in req_list
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                        
                    if requires_mic:
                        in_orig = shader_id in self.load_requires_file('mic')
                        has_req = 'micbuf' in req_list
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                        
                    if requires_music:
                        in_orig = shader_id in self.load_requires_file('music')
                        has_req = 'musicbuf' in req_list
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                        
                    if requires_musicstream:
                        in_orig = shader_id in self.load_requires_file('musicstream')
                        has_req = 'musicstreambuf' in req_list
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                        
                    if requires_sound:
                        in_orig = shader_id in self.load_requires_file('sound')
                        has_req = 'soundbuf' in req_list
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                        
                    if requires_soundbuf:
                        in_orig = shader_id in self.load_requires_file('soundbuf')
                        has_req = 'soundbuf' in req_list
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                        
                    if requires_texture:
                        in_orig = shader_id in self.load_requires_file('texture')
                        has_req = 'texturebuf' in req_list
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                        
                    if requires_video:
                        in_orig = shader_id in self.load_requires_file('video')
                        has_req = 'videobuf' in req_list
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                        
                    if requires_volume:
                        in_orig = shader_id in self.load_requires_file('volume')
                        has_req = 'volumebuf' in req_list
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                        
                    if requires_webcam:
                        in_orig = shader_id in self.load_requires_file('webcam')
                        has_req = 'webcambuf' in req_list
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                        
                    if requires_common:
                        in_orig = shader_id in self.load_requires_file('common')  # Common becomes library
                        has_req = 'library' in req_list  # Common type becomes library
                        conditions_met.append(in_orig or has_req)
                        any_requirement_checked = True
                    
                    # Only add shader if all specified requirements are satisfied, OR no requirements were specified
                    if (any_requirement_checked and all(conditions_met)) or not any_requirement_checked:
                        temp_matching.add(shader_id)
            matching_shaders = temp_matching

        # Prepare results
        for shader_id in matching_shaders:
            data = self.shader_index[shader_id]
            results.append({
                'filepath': data['filepath'],
                'id': shader_id,
                'name': data['name'],
                'username': data['username'],
                'description': data['description'],
                'tags': data['tags']
            })

        return results

def main():
    parser = argparse.ArgumentParser(description='Search Shadertoy shaders')

    # Text-based search options
    parser.add_argument('--tags', type=str, help='Search by tags')
    parser.add_argument('--name', type=str, help='Search by name')
    parser.add_argument('--author', type=str, help='Search by author/username')
    parser.add_argument('--description', type=str, help='Search by description')

    # Requires-based search options
    parser.add_argument('--buffer', action='store_true', help='Shaders requiring buffers')
    parser.add_argument('--cubemap', action='store_true', help='Shaders requiring cubemaps')
    parser.add_argument('--image', action='store_true', help='Shaders requiring images')
    parser.add_argument('--imagebuf', action='store_true', help='Shaders requiring image buffers')
    parser.add_argument('--keyboard', action='store_true', help='Shaders requiring keyboard input')
    parser.add_argument('--library', action='store_true', help='Shaders requiring external libraries')
    parser.add_argument('--mic', action='store_true', help='Shaders requiring microphone input')
    parser.add_argument('--music', action='store_true', help='Shaders requiring music input')
    parser.add_argument('--musicstream', action='store_true', help='Shaders requiring music stream input')
    parser.add_argument('--sound', action='store_true', help='Shaders requiring sound input')
    parser.add_argument('--soundbuf', action='store_true', help='Shaders requiring sound buffers')
    parser.add_argument('--texture', action='store_true', help='Shaders requiring textures')
    parser.add_argument('--video', action='store_true', help='Shaders requiring video input')
    parser.add_argument('--volume', action='store_true', help='Shaders requiring volume textures')
    parser.add_argument('--webcam', action='store_true', help='Shaders requiring webcam input')
    parser.add_argument('--common', action='store_true', help='Shaders requiring common includes')

    # Additional options
    parser.add_argument('--reindex', action='store_true', help='Force rebuild of shader index cache')
    parser.add_argument('--add-tags', action='store_true', help='Add tags from search_results to JSON files')
    parser.add_argument('--json-dir', type=str, default='json', help='Directory containing JSON shader files')

    args = parser.parse_args()

    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_dir = os.path.join(script_dir, args.json_dir)

    shader_dirs = [
        os.path.join(script_dir, 'shaders_071121'),
        os.path.join(script_dir, 'shaders_270321')
    ]

    searcher = ShaderSearcher(json_dir, shader_dirs)
    
    # If --add-tags is specified, add tags and requires info to JSONs
    if args.add_tags:
        print("Adding tags and requires information from search_results and by analyzing JSONs...")
        searcher.add_requires_info_to_jsons()
        return

    # Check if any search criteria are provided
    has_criteria = any([
        args.tags, args.name, args.author, args.description,
        args.buffer, args.cubemap, args.image, args.imagebuf,
        args.keyboard, args.library, args.mic, args.music,
        args.musicstream, args.sound, args.soundbuf, args.texture,
        args.video, args.volume, args.webcam, args.common
    ])

    if has_criteria:
        results = searcher.search(
            tags=args.tags,
            name=args.name,
            author=args.author,
            description=args.description,
            requires_buffer=args.buffer,
            requires_cubemap=args.cubemap,
            requires_image=args.image,
            requires_imagebuf=args.imagebuf,
            requires_keyboard=args.keyboard,
            requires_library=args.library,
            requires_mic=args.mic,
            requires_music=args.music,
            requires_musicstream=args.musicstream,
            requires_sound=args.sound,
            requires_soundbuf=args.soundbuf,
            requires_texture=args.texture,
            requires_video=args.video,
            requires_volume=args.volume,
            requires_webcam=args.webcam,
            requires_common=args.common,
            force_rebuild=args.reindex
        )

        if results:
            print(f"Found {len(results)} matching shaders:")
            print("-" * 80)
            for result in results:
                print(f"ID: {result['id']}")
                print(f"Name: {result['name']}")
                print(f"Author: {result['username']}")
                print(f"Tags: {', '.join(result['tags']) if result['tags'] else 'None'}")
                print(f"Description: {result['description'][:100] + '...' if len(result['description']) > 100 else result['description']}")
                print(f"File: {result['filepath']}")
                print("-" * 80)
        else:
            print("No shaders found matching the criteria.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()