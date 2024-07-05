import streamlit as st
import requests
import time
import pandas as pd
import numpy as np
import plotly.express as px
from playwright.sync_api import sync_playwright
from PIL import Image
import io
from io import BytesIO
import subprocess
import sys
import math
import base64

# Function to search for places
def search_places(api_key, query, location):
    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    places = []
    next_page_token = None

    while True:
        params = {
            'query': f'{query} in {location}',
            'key': api_key
        }
        if next_page_token:
            params['pagetoken'] = next_page_token

        response = requests.get(base_url, params=params)
        result = response.json()

        if 'results' in result:
            for place in result['results']:
                place_data = {
                    'place_id': place.get('place_id', 'N/A'),
                    'name': place.get('name', 'N/A'),
                    'rating': place.get('rating', 'N/A'),
                    'user_ratings_total': place.get('user_ratings_total', 0),
                    'address': place.get('formatted_address', 'N/A'),
                    'photo_reference': place.get('photos', [{}])[0].get('photo_reference')
                }
                places.append(place_data)
                # st.write(f"Place: {place_data['name']}, Place ID: {place_data['place_id']}, Photo Reference: {'Available' if place_data['photo_reference'] else 'Not available'}")

        if 'next_page_token' in result:
            next_page_token = result['next_page_token']
            time.sleep(2)
        else:
            break

    return places

    
def get_place_details(api_key, place_id):
    base_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        'place_id': place_id,
        'fields': 'name,rating,user_ratings_total,formatted_address,formatted_phone_number,website,price_level,opening_hours,reviews',
        'key': api_key
    }

    response = requests.get(base_url, params=params)
    result = response.json()

    return result.get('result', {})

def get_place_photo(api_key, photo_reference, max_width=1600):  # Meningkatkan max_width
    if not photo_reference:
        return None
    
    base_url = "https://maps.googleapis.com/maps/api/place/photo"
    params = {
        'maxwidth': max_width,
        'photoreference': photo_reference,
        'key': api_key
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        if response.headers.get('content-type', '').startswith('image'):
            # Menggunakan PIL untuk membuka dan mengoptimalkan gambar
            image = Image.open(BytesIO(response.content))
            
            # Mengoptimalkan gambar
            optimized_image = BytesIO()
            image.save(optimized_image, format='JPEG', quality=95, optimize=True)
            optimized_image.seek(0)
            
            return optimized_image.getvalue()
        else:
            st.warning(f"Received non-image response for photo reference: {photo_reference[:10]}...")
            return None
    
    except requests.RequestException as e:
        st.error(f"Error fetching photo: {str(e)}")
        return None
        
# Function to get place details
# def get_place_details(api_key, place_id):
#     base_url = "https://maps.googleapis.com/maps/api/place/details/json"
#     params = {
#         'place_id': place_id,
#         'fields': 'name,rating,user_ratings_total,formatted_address,formatted_phone_number,website,price_level,opening_hours,reviews',
#         'key': api_key
#     }

#     response = requests.get(base_url, params=params)
#     result = response.json()

#     return result.get('result', {})

def min_max_scale(series):
    return (series - series.min()) / (series.max() - series.min())

# Fungsi-fungsi untuk pembuatan poster
def create_star_svg(percentage):
    return f'''
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="star-{percentage}">
                <stop offset="{percentage}%" stop-color="#F2C94C" />
                <stop offset="{percentage}%" stop-color="#E0E0E0" />
            </linearGradient>
        </defs>
        <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"
              fill="url(#star-{percentage})" stroke="#F2C94C" stroke-width="1" />
    </svg>
    '''

def create_coffee_shops_poster(df, query, location, width=900, bg_color="#C1A87D"):
    shops_html = ""
    for index, row in df.iterrows():
        stars_html = ''.join([create_star_svg(max(0, min(100, (row['rating'] - i) * 100))) for i in range(5)])
        shops_html += f'''
        <div class="bg-gray-100 p-4 rounded-lg shadow-md mb-4">
            <div class="flex justify-between items-center">
                <span class="font-semibold text-lg text-gray-800">{row['rank']}. {row['name']}</span>
                <div class="flex items-center">
                    <div class="flex mr-2">{stars_html}</div>
                    <span class="font-medium text-lg text-gray-800">{row['rating']:.1f}</span>
                </div>
            </div>
            <div class="text-sm text-gray-600 mt-1">{row['user_ratings_total']:,} ratings</div>
        </div>
        '''

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            body {{ font-family: 'Inter', sans-serif; }}
        </style>
    </head>
    <body>
        <div class="poster-container bg-white" style="width: {width}px; height: {int(width * 1.4)}px;">
            <div class="flex flex-col items-center justify-center h-full">
                <div class="w-5/6 max-w-2xl">
                    <h1 class="text-3xl font-bold mb-6 text-gray-900 text-center">Top 10 {query} di {location}</h1>
                    <div class="space-y-4">
                        {shops_html}
                    </div>
                    <div class="mt-6 text-sm text-gray-500 text-center">Data based on user ratings and reviews</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

def create_modern_bar_chart_poster(df, query, location, width=900):
    shops_html = ""
    max_rating = df['rating'].max()
    for index, row in df.iterrows():
        bar_width = f"{(row['rating'] / max_rating) * 100}%"
        shops_html += f'''
        <div class="mb-4">
            <div class="flex justify-between items-center mb-1">
                <span class="font-medium text-sm text-gray-800">{row['rank']}. {row['name']}</span>
                <span class="text-sm text-gray-600">{row['rating']}</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2.5">
                <div class="bg-blue-600 h-2.5 rounded-full" style="width: {bar_width}"></div>
            </div>
            <div class="text-xs text-gray-500 mt-1">{row['user_ratings_total']:,} ratings</div>
        </div>
        '''

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
            body {{ font-family: 'Inter', sans-serif; }}
        </style>
    </head>
    <body>
        <div class="poster-container">
            <div class="bg-white p-8" style="width: {width}px;">
                <h1 class="text-3xl font-bold mb-6 text-gray-900">Top 10 {query} di {location}</h1>
                <div class="space-y-6">
                    {shops_html}
                </div>
                <div class="mt-6 text-xs text-gray-400">Data based on user ratings and reviews</div>
            </div>
        </div>
    </body>
    </html>
    '''

def create_colorful_card_poster(df, query, location, width=900):
    color_accents = ['red', 'blue', 'green', 'yellow', 'purple', 'pink', 'indigo', 'teal', 'orange', 'cyan']
    shops_html = ""
    for index, row in df.iterrows():
        accent = color_accents[index % len(color_accents)]
        shops_html += f'''
        <div class="bg-white rounded-lg shadow-md p-4 border-l-4 border-{accent}-500">
            <div class="flex justify-between items-center">
                <span class="font-semibold text-lg text-gray-800">{row['rank']}. {row['name']}</span>
                <span class="font-bold text-{accent}-600">{row['rating']}</span>
            </div>
            <div class="text-sm text-gray-600 mt-1">{row['user_ratings_total']:,} ratings</div>
        </div>
        '''

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
            body {{ font-family: 'Poppins', sans-serif; }}
        </style>
    </head>
    <body>
        <div class="poster-container">
            <div class="bg-gray-100 p-8" style="width: {width}px;">
                <h1 class="text-3xl font-bold mb-6 text-gray-900 text-center">Top 10 {query} di {location}</h1>
                <div class="grid grid-cols-2 gap-4">
                    {shops_html}
                </div>
                <div class="mt-6 text-xs text-gray-500 text-center">Data based on user ratings and reviews</div>
            </div>
        </div>
    </body>
    </html>
    '''

def create_minimalist_circle_poster(df, query, location, width=900):
    shops_html = ""
    for index, row in df.iterrows():
        circle_percentage = (row['rating'] / 5) * 100
        shops_html += f'''
        <div class="flex items-center mb-4">
            <div class="relative w-16 h-16 mr-4">
                <svg class="w-full h-full" viewBox="0 0 36 36">
                    <path d="M18 2.0845
                        a 15.9155 15.9155 0 0 1 0 31.831
                        a 15.9155 15.9155 0 0 1 0 -31.831"
                        fill="none" stroke="#eee" stroke-width="3" />
                    <path d="M18 2.0845
                        a 15.9155 15.9155 0 0 1 0 31.831
                        a 15.9155 15.9155 0 0 1 0 -31.831"
                        fill="none" stroke="#4CAF50" stroke-width="3"
                        stroke-dasharray="{circle_percentage}, 100" />
                    <text x="18" y="20.35" class="text-xl font-semibold" text-anchor="middle" fill="#333">{row['rating']}</text>
                </svg>
            </div>
            <div>
                <div class="font-medium text-gray-900">{row['rank']}. {row['name']}</div>
                <div class="text-sm text-gray-600">{row['user_ratings_total']:,} ratings</div>
            </div>
        </div>
        '''

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500&display=swap');
            body {{ font-family: 'Roboto', sans-serif; }}
        </style>
    </head>
    <body>
        <div class="poster-container">
            <div class="bg-white p-8" style="width: {width}px;">
                <h1 class="text-3xl font-light mb-8 text-gray-800 text-center">Top 10 {query} di {location}</h1>
                <div class="space-y-6">
                    {shops_html}
                </div>
                <div class="mt-8 text-xs text-gray-400 text-center">Data based on user ratings and reviews</div>
            </div>
        </div>
    </body>
    </html>
    '''

def create_infographic_icon_poster(df, query, location, width=900):
    shops_html = ""
    for index, row in df.iterrows():
        shops_html += f'''
        <div class="flex items-center mb-6">
            <div class="w-12 h-12 flex-shrink-0 mr-4 bg-yellow-400 rounded-full flex items-center justify-center">
                <span class="text-2xl font-bold text-white">{row['rank']}</span>
            </div>
            <div class="flex-grow">
                <div class="font-medium text-lg text-gray-900">{row['name']}</div>
                <div class="flex items-center mt-1">
                    <svg class="w-5 h-5 text-yellow-500 mr-1" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                    </svg>
                    <span class="text-sm font-semibold text-gray-700">{row['rating']}</span>
                    <span class="text-sm text-gray-500 ml-2">({row['user_ratings_total']:,} ratings)</span>
                </div>
            </div>
        </div>
        '''

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600;700&display=swap');
            body {{ font-family: 'Nunito', sans-serif; }}
        </style>
    </head>
    <body>
        <div class="poster-container">
            <div class="bg-gradient-to-br from-blue-50 to-purple-50 p-8" style="width: {width}px;">
                <h1 class="text-3xl font-bold mb-8 text-gray-800 text-center">Top 10 {query} di {location}</h1>
                <div class="space-y-4">
                    {shops_html}
                </div>
                <div class="mt-8 text-sm text-gray-500 text-center">Data based on user ratings and reviews</div>
            </div>
        </div>
    </body>
    </html>
    '''

def create_minimalist_text_poster(query, location, width=900):
    height = int(width * 1.4)  # Mempertahankan rasio portrait

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Roboto:ital,wght@0,400;1,300&display=swap');
            body {{ font-family: 'Roboto', sans-serif; }}
            .title {{ font-family: 'Playfair Display', serif; }}
        </style>
    </head>
    <body>
        <div class="poster-container bg-white" style="width: {width}px; height: {height}px;">
            <div class="flex flex-col justify-center h-full pl-12"> <!-- Adjusted padding for left alignment -->
                <div class="max-w-lg"> <!-- Limit max width for better layout control -->
                    <h1 class="title text-5xl font-bold mb-2 text-gray-900">{query} terbaik</h1>
                    <h2 class="title text-4xl font-bold mb-6 text-gray-800">di {location}</h2>
                    <p class="text-lg italic text-gray-600">Menurut Google Reviews</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

def create_retro_grid_poster(df, query, location, width=900):
    shops_html = ""
    for index, row in df.iterrows():
        shops_html += f'''
        <div class="bg-yellow-100 p-4 rounded-lg border-2 border-yellow-600">
            <div class="font-bold text-2xl text-yellow-800 mb-2">{row['rank']}</div>
            <div class="font-medium text-yellow-900 mb-1">{row['name']}</div>
            <div class="flex items-center justify-between">
                <span class="text-sm font-bold text-yellow-700">{row['rating']} ★</span>
                <span class="text-xs text-yellow-800">{row['user_ratings_total']:,} ratings</span>
            </div>
        </div>
        '''

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Abril+Fatface&family=DM+Sans:wght@400;500;700&display=swap');
            body {{ font-family: 'DM Sans', sans-serif; }}
            h1 {{ font-family: 'Abril Fatface', cursive; }}
        </style>
    </head>
    <body>
        <div class="poster-container">
            <div class="bg-yellow-50 p-8" style="width: {width}px;">
                <h1 class="text-4xl mb-8 text-yellow-900 text-center">Top 10 {query} di {location}</h1>
                <div class="grid grid-cols-2 gap-4">
                    {shops_html}
                </div>
                <div class="mt-8 text-sm text-yellow-800 text-center font-medium">Data based on user ratings and reviews</div>
            </div>
        </div>
    </body>
    </html>
    '''


# Fungsi untuk menginstal Chromium
def install_chromium():
    try:
        # st.write("Installing Chromium...")
        result = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                                capture_output=True, text=True, check=True)
        # st.write("Chromium installed successfully.")
        st.write(result.stdout)
    except subprocess.CalledProcessError as e:
        st.error("Failed to install Chromium.")
        st.error(e.stderr)
        raise
        
# Fungsi untuk generate poster
# def generate_poster(df, query, location, width=900, bg_color="#C1A87D"):
#     html_content = create_coffee_shops_poster(df, query, location, width, bg_color)
#     try:
#         with sync_playwright() as p:
#             browser = p.chromium.launch(chromium_sandbox=False)
#             page = browser.new_page()
#             page.set_content(html_content)
            
#             # Evaluasi tinggi konten
#             content_height = page.evaluate('''() => {
#                 const posterContainer = document.querySelector('.poster-container');
#                 return posterContainer.getBoundingClientRect().height;
#             }''')
            
#             # Set viewport ke ukuran konten yang tepat
#             page.set_viewport_size({"width": width, "height": math.ceil(content_height)})
            
#             # Ambil screenshot dari elemen poster-container saja
#             screenshot_bytes = page.locator('.poster-container').screenshot()
            
#             browser.close()
#         return screenshot_bytes
#     except Exception as e:
#         st.error(f"Error generating poster: {str(e)}")
#         return None

def generate_poster(df, query, location, design, width=900):
    if design == 'minimalist_text':
        html_content = create_minimalist_text_poster(query, location, width)
    elif design == 'original':
        html_content = create_coffee_shops_poster(df, query, location, width)
    elif design == 'modern':
        html_content = create_modern_bar_chart_poster(df, query, location, width)
    elif design == 'colorful':
        html_content = create_colorful_card_poster(df, query, location, width)
    elif design == 'minimalist':
        html_content = create_minimalist_circle_poster(df, query, location, width)
    elif design == 'infographic':
        html_content = create_infographic_icon_poster(df, query, location, width)
    elif design == 'retro':
        html_content = create_retro_grid_poster(df, query, location, width)
    else:
        raise ValueError("Invalid design choice")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(chromium_sandbox=False)
            page = browser.new_page()
            page.set_content(html_content)
            
            if design in ['original', 'minimalist_text']:
                # Use fixed height for these designs
                page.set_viewport_size({"width": width, "height": int(width * 1.4)})
            else:
                # For other designs, use the previous dynamic height calculation
                content_height = page.evaluate('''() => {
                    const posterContainer = document.querySelector('.poster-container');
                    return posterContainer.getBoundingClientRect().height;
                }''')
                page.set_viewport_size({"width": width, "height": int(content_height)})
            
            screenshot_bytes = page.locator('.poster-container').screenshot()
            browser.close()
        return screenshot_bytes
    except Exception as e:
        st.error(f"Error generating {design} poster: {str(e)}")
        return None

def create_individual_place_poster(place, photo_bytes, width=1200):
    height = int(width * 1.4)
    stars_html = ''.join([create_star_svg(max(0, min(100, (place['rating'] - i) * 100))) for i in range(5)])
    
    if photo_bytes:
        photo_html = f'''
        <div class="w-full pb-[100%] relative overflow-hidden">
            <img src="data:image/jpeg;base64,{base64.b64encode(photo_bytes).decode()}" 
                 class="absolute inset-0 w-full h-full object-cover" alt="{place["name"]}">
        </div>
        '''
    else:
        photo_html = '<div class="w-full pb-[100%] relative bg-gray-200 flex items-center justify-center"><span class="absolute text-gray-500">No Image Available</span></div>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Roboto:wght@300;400;700&display=swap');
            body {{ font-family: 'Roboto', sans-serif; }}
            .title {{ font-family: 'Playfair Display', serif; }}
        </style>
    </head>
    <body>
        <div class="poster-container bg-white flex items-center justify-center" style="width: {width}px; height: {height}px;">
            <div class="w-4/5 max-w-3xl bg-gray-100 rounded-lg overflow-hidden shadow-lg">
                {photo_html}
                <div class="p-6">
                    <h1 class="title text-3xl font-bold text-gray-900 mb-2 leading-tight">{place['name']}</h1>
                    <div class="flex items-center mb-2">
                        <div class="flex mr-2">{stars_html}</div>
                        <span class="text-xl font-semibold text-gray-700">({place['rating']})</span>
                    </div>
                    <p class="text-lg text-gray-600 mb-2">{place['user_ratings_total']} reviews</p>
                    <p class="text-md text-gray-700 leading-snug">{place['address']}</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    
def generate_individual_poster(place, photo_bytes, width=1200):
    html_content = create_individual_place_poster(place, photo_bytes, width)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(chromium_sandbox=False)
            page = browser.new_page()
            page.set_content(html_content)
            page.set_viewport_size({"width": width, "height": int(width * 1.4)})
            screenshot_bytes = page.locator('.poster-container').screenshot(type='jpeg', quality=100)
            browser.close()
        return screenshot_bytes
    except Exception as e:
        st.error(f"Error generating individual poster: {str(e)}")
        return None

# Main Streamlit app
def main():
    st.title("Google Places Search App")

    # Get API key from Streamlit secrets
    api_key = st.secrets["google_places_api_key"]

    # User inputs
    location = st.text_input("Enter location", "Tangerang Selatan")
    query = st.text_input("Enter place type", "Coffee Shop")

    if st.button("Search"):
        places = search_places(api_key, query, location)

        st.write(f"\nTotal places found: {len(places)}")

        data = []
        progress_bar = st.progress(0)
        for i, place in enumerate(places, 1):
            progress_bar.progress(i / len(places))
            place_id = place.get('place_id')
            if place_id != 'N/A':
                details = get_place_details(api_key, place_id)
            else:
                details = {}

            place_data = {
                'name': details.get('name', place.get('name', 'N/A')),
                'rating': details.get('rating', place.get('rating', np.nan)),
                'user_ratings_total': details.get('user_ratings_total', place.get('user_ratings_total', 0)),
                'address': details.get('formatted_address', place.get('address', 'N/A')),
                'phone': details.get('formatted_phone_number', 'N/A'),
                'website': details.get('website', 'N/A'),
                'price_level': details.get('price_level', 'N/A'),
                'open_now': details.get('opening_hours', {}).get('open_now', 'N/A'),
                'latitude': place.get('geometry', {}).get('location', {}).get('lat', 'N/A'),
                'longitude': place.get('geometry', {}).get('location', {}).get('lng', 'N/A'),
                'photo_reference': place.get('photo_reference')  # Pastikan ini ada
            }

            data.append(place_data)

        df = pd.DataFrame(data)
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
        df['user_ratings_total'] = pd.to_numeric(df['user_ratings_total'], errors='coerce')

        # Sorting and filtering
        df = df[df['rating'] > 4.2]
        df = df[df['user_ratings_total'] > 100]
        df = df.sort_values(by=['rating', 'user_ratings_total'], ascending=[False, False]).reset_index(drop=True)

        df_top10 = df.head(10)
        df_top10['rank'] = df_top10.index + 1

        # st.header("Top 10 Places:")
        # st.write("Checking df_top10 for photo references:")
        # for index, place in df_top10.iterrows():
        #     st.write(f"{place['name']}: {'Has photo_reference' if place['photo_reference'] else 'No photo_reference'}")
            # st.write(f"{place['name']}: {'Has photo_reference' if 'photo_reference' in place and place['photo_reference'] else 'No photo_reference'}")

        # Display top 10 places
        st.header("Top 10 Places:")
        # st.write("The top 10 places are selected based on criteria of having a rating above 4.2 and more than 100 reviews. This list is then sorted according to the Geometric Mean of rating value and number of reviews.")
        df_top10_renamed = df_top10.rename(columns={
                                'name': 'Nama Tempat',
                                'rating': 'Rating',
                                'user_ratings_total': 'Jumlah Ulasan',
                                'address': 'Alamat',
                                'price_level': 'Tingkat Harga'
                            })
        st.dataframe(df_top10_renamed, 
                     height=400, 
                     use_container_width=True)

        # # Create scatter plot
        # st.write("Scatter Plot: Number of Reviews vs Rating")
        # fig = px.scatter(df, x='user_ratings_total', y='rating', hover_name='name',
        #                  labels={'user_ratings_total': 'Number of Reviews', 'rating': 'Rating'},
        #                  title=f'Rating vs Number of Reviews for {query} in {location}')
        # fig.update_layout(height=600)
        # st.plotly_chart(fig, use_container_width=True)

        # Bagian untuk generate poster
        install_chromium()
        # try:
        #     install_chromium()  # Coba instal Chromium
        #     with st.spinner("Generating poster..."):
        #         screenshot_bytes = generate_poster(df_top10, query, location)
        #         if screenshot_bytes:
        #             image = Image.open(io.BytesIO(screenshot_bytes))
        #             st.image(image, caption="Generated Poster", use_column_width=True)
        #             st.download_button(
        #                 label="Download Poster",
        #                 data=screenshot_bytes,
        #                 file_name=f"top10_{query.lower()}_{location.lower().replace(' ', '_')}_poster.png",
        #                 mime="image/png"
        #             )
        #         else:
        #             st.error("Failed to generate poster.")
        # except Exception as e:
        #     st.error(f"An error occurred: {str(e)}")

        st.header("Generated Posters")
        
        designs = ['minimalist_text','original']
        
        for design in designs:
            # st.subheader(f"{design.capitalize()} Design")
            with st.spinner(f"Generating {design} poster..."):
                poster_bytes = generate_poster(df_top10, query, location, design)
                if poster_bytes:
                    image = Image.open(io.BytesIO(poster_bytes))
                    st.image(image, caption=f"{design.capitalize()} Poster", use_column_width=True)
                    # st.download_button(
                    #     label=f"Download {design.capitalize()} Poster",
                    #     data=poster_bytes,
                    #     file_name=f"top10_{query.lower()}_{location.lower().replace(' ', '_')}_{design}_poster.png",
                    #     mime="image/png"
                    # )
                else:
                    st.error(f"Failed to generate {design} poster.")

        # st.header("Individual Place Posters")
        for index, place in df_top10.iterrows():
            st.subheader(f"{index + 1}. {place['name']}")
            
            photo_reference = place.get('photo_reference')
            if photo_reference:
                # st.write(f"Attempting to fetch photo for {place['name']}...")
                photo_bytes = get_place_photo(api_key, place.get('photo_reference'), max_width=1600)
                # if photo_bytes:
                #     st.image(photo_bytes, caption=f"Photo of {place['name']}")
                # else:
                #     st.warning(f"Could not retrieve photo for {place['name']}")
            else:
                st.warning(f"No photo reference available for {place['name']}")
            
            # Generate dan tampilkan poster
            with st.spinner(f"Generating poster for {place['name']}..."):
                individual_poster_bytes = generate_individual_poster(place, photo_bytes if 'photo_bytes' in locals() else None)
                if individual_poster_bytes:
                    image = Image.open(io.BytesIO(individual_poster_bytes))
                    st.image(image, caption=f"{place['name']} Poster", use_column_width=True)
                    st.download_button(
                        label=f"Download {place['name']} Poster",
                        data=individual_poster_bytes,
                        file_name=f"{place['name'].lower().replace(' ', '_')}_poster.png",
                        mime="image/png",
                        key=f"download_button_{index}"  # Menambahkan kunci unik
                    )
                else:
                    st.error(f"Failed to generate poster for {place['name']}")

        
        # Download button for full data
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download full data as CSV",
            data=csv,
            file_name=f'{query.lower()}_{location.lower().replace(" ", "_")}_filtered.csv',
            mime='text/csv',
        )

if __name__ == "__main__":
    main()
